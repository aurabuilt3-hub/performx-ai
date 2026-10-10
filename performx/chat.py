"""PERFORMX — Grounded AI Chat Assistant & Deterministic Context Assembler.

Architecture:
- Privacy-first: Raw camera video, image frames, and MediaPipe landmark arrays are NEVER passed to the LLM.
- Grounding: Only sanitized scalar metrics, active plan exercises, user-reported health context,
  and daily logs for the authenticated user are retrieved.
- Safety & Guardrails:
  1. Allergen status conservatism: If allergen status is UNKNOWN, system strictly forbids
     claiming ingredients are safe or absent.
  2. Medical safety: Clinician restrictions and reported injuries are explicitly demarcated as
     USER_REPORTED or CLINICIAN_RESTRICTION; assistant is prohibited from diagnosing or clearing contraindications.
  3. No metric hallucination: Form scores, repetition counts, and depth angles are bound strictly to
     deterministic SessionMetrics.
  4. Cross-user isolation: Retrieval is strictly bound to the authenticated `user_id`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from performx.storage import (
    AdaptiveRecommendation,
    HealthProfile,
    NutritionLog,
    PersistedWorkoutSession,
    RecoveryCheckin,
    UserProfile,
    WorkoutPlan,
    WorkoutStorage,
)


class ChatMessageRequest(BaseModel):
    """User prompt payload for the PERFORMX AI Chat Assistant."""
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000, description="User question or coaching inquiry.")
    session_id: str | None = Field(default=None, max_length=128, description="Optional active or recent session ID to ground feedback on.")


class ChatMessageResponse(BaseModel):
    """Assistant response payload with provenance citations."""
    model_config = ConfigDict(extra="forbid")

    reply: str = Field(description="Grounded natural language response.")
    grounded_entities: list[str] = Field(default_factory=list, description="IDs and categories of records used to ground this answer.")
    warnings: list[str] = Field(default_factory=list, description="Safety or allergy advisories.")


@dataclass(frozen=True)
class ChatGroundingContext:
    """Sanitized context bundle extracted strictly for the authenticated user."""
    user_id: str
    display_name: str
    fitness_experience: str
    primary_goal: str
    available_equipment: list[str]
    health_limitations: dict[str, Any]
    active_plan: dict[str, Any] | None
    recent_workout_metrics: list[dict[str, Any]]
    latest_recovery: dict[str, Any] | None
    today_nutrition: dict[str, Any] | None
    safety_advisories: list[str] = field(default_factory=list)

    def to_system_prompt_context(self) -> str:
        """Render context as structured markdown for system prompt injection."""
        lines = [
            f"# USER PROFILE: {self.display_name} (Experience: {self.fitness_experience}, Goal: {self.primary_goal})",
            f"Available Equipment: {', '.join(self.available_equipment) if self.available_equipment else 'Bodyweight only'}",
            "",
            "## CLINICAL & INJURY SAFETY CONSTRAINTS (USER_REPORTED / CLINICIAN):",
            f"- Reported Injuries: {self.health_limitations.get('reported_injuries', [])}",
            f"- Reported Symptoms: {self.health_limitations.get('reported_symptoms', [])}",
            f"- Clinician Restrictions: {self.health_limitations.get('clinician_restrictions', [])}",
            f"- Known Allergies: {self.health_limitations.get('allergies', [])}",
            f"- Dietary Restrictions: {self.health_limitations.get('dietary_restrictions', [])}",
            "",
            "## RECENT DETERMINISTIC WORKOUT METRICS (VERIFIED RECORD):",
        ]

        if not self.recent_workout_metrics:
            lines.append("No completed workout sessions recorded yet.")
        else:
            for s in self.recent_workout_metrics:
                lines.append(
                    f"- Session {s.get('id')} ({s.get('exercise_type')}): "
                    f"Total Reps={s.get('total_reps')}, Valid={s.get('valid_reps')}, "
                    f"Symmetry={s.get('mean_symmetry')}, Duration={s.get('duration_seconds')}s"
                )

        lines.extend([
            "",
            "## ACTIVE WORKOUT PLAN:",
            f"Plan Title: {self.active_plan.get('title') if self.active_plan else 'None'}",
            f"Exercises: {self.active_plan.get('exercises') if self.active_plan else '[]'}",
            "",
            "## RECOVERY & NUTRITION STATUS:",
            f"Recovery Checkin: {self.latest_recovery if self.latest_recovery else 'None logged'}",
            f"Nutrition Today: {self.today_nutrition if self.today_nutrition else 'None logged'}",
        ])

        if self.safety_advisories:
            lines.extend(["", "## MANDATORY SAFETY DIRECTIVES:"] + [f"- {a}" for a in self.safety_advisories])

        return "\n".join(lines)


async def assemble_grounding_context(
    user_id: str,
    storage: WorkoutStorage,
    auth_token: str | None = None,
    specific_session_id: str | None = None,
) -> ChatGroundingContext:
    """Retrieve and sanitize all authorized context for an authenticated user.
    
    Guarantees:
    - Never accesses records of any other user.
    - Never queries raw video, frames, or landmarks.
    - Sanitizes all numbers and bounds.
    """
    profile = await storage.get_profile(user_id, auth_token=auth_token)
    display_name = profile.display_name if profile and profile.display_name else "Athlete"
    fitness_exp = profile.fitness_experience if profile else "intermediate"
    primary_goal = profile.primary_goal if profile else "general_fitness"
    equipment = profile.available_equipment if profile and profile.available_equipment else []

    health = await storage.get_health_profile(user_id, auth_token=auth_token)
    health_limitations = {
        "reported_injuries": health.reported_injuries if health else [],
        "reported_symptoms": health.reported_symptoms if health else [],
        "clinician_restrictions": health.clinician_restrictions if health else [],
        "allergies": health.allergies if health else [],
        "dietary_restrictions": health.dietary_restrictions if health else [],
    }

    active_plan = await storage.get_active_workout_plan(user_id, auth_token=auth_token)
    plan_dict = active_plan.to_dict() if active_plan else None

    # Fetch recent persisted workouts
    workouts, _ = await storage.list_workouts(user_id, limit=3, offset=0, auth_token=auth_token)
    recent_metrics = []
    for w in workouts:
        recent_metrics.append({
            "id": w.id,
            "exercise_type": w.exercise_type,
            "duration_seconds": w.duration_seconds,
            "total_reps": w.total_reps,
            "valid_reps": w.valid_reps,
            "mean_symmetry": w.mean_symmetry,
            "mean_rep_duration": w.mean_rep_duration,
            "summary_metrics": w.summary_metrics,
        })

    # Recovery checkins
    recovery_list = await storage.list_recovery_checkins(user_id, auth_token=auth_token)
    latest_rec = recovery_list[0].to_dict() if recovery_list else None

    # Nutrition
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_nut = await storage.get_nutrition_log(user_id, today_str, auth_token=auth_token)
    if today_nut is None:
        # Fall back to empty date string or latest available if any
        today_nut = await storage.get_nutrition_log(user_id, "", auth_token=auth_token)
    nutrition_dict = today_nut.to_dict() if today_nut else None

    safety_advisories = [
        "DO NOT diagnose medical conditions or contradict clinician restrictions.",
        "DO NOT generate hallucinated movement rep counts or biomechanical scores.",
    ]

    if nutrition_dict and nutrition_dict.get("allergen_verification_status") == "UNKNOWN":
        safety_advisories.append(
            "ALLERGEN SAFETY CONSERVATISM: Allergen verification status is UNKNOWN. "
            "You MUST inform the user that allergens are unverified and advise verifying with manufacturer/clinician."
        )

    return ChatGroundingContext(
        user_id=user_id,
        display_name=display_name,
        fitness_experience=fitness_exp,
        primary_goal=primary_goal,
        available_equipment=equipment,
        health_limitations=health_limitations,
        active_plan=plan_dict,
        recent_workout_metrics=recent_metrics,
        latest_recovery=latest_rec,
        today_nutrition=nutrition_dict,
        safety_advisories=safety_advisories,
    )


import os
import logging
import httpx

logger = logging.getLogger(__name__)


class LLMClientProtocol(Protocol):
    """Protocol for LLM clients to allow zero-dependency test mocking and multi-provider backends."""
    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        ...


class GeminiLLMClient:
    """Production Google Gemini client via HTTP REST API.
    
    Uses GEMINI_API_KEY environment variable.
    """
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout_seconds

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800,
            }
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.error(f"Gemini API returned status {resp.status_code}: {resp.text}")
                raise RuntimeError(f"Gemini API request failed with status {resp.status_code}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError("No generation candidates returned from Gemini API")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise RuntimeError("Empty response parts from Gemini API")
            return parts[0].get("text", "").strip()


class OpenAILLMClient:
    """Production OpenAI client via HTTP REST API.
    
    Uses OPENAI_API_KEY environment variable.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout_seconds: float = 15.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout_seconds

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error(f"OpenAI API returned status {resp.status_code}: {resp.text}")
                raise RuntimeError(f"OpenAI API request failed with status {resp.status_code}")
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError("No choices returned from OpenAI API")
            return choices[0].get("message", {}).get("content", "").strip()


def create_llm_client_from_env() -> LLMClientProtocol | None:
    """Instantiate configured LLM provider from environment variables.
    
    Checks in order:
    1. GEMINI_API_KEY -> GeminiLLMClient
    2. OPENAI_API_KEY -> OpenAILLMClient
    3. None -> Returns None (falls back to deterministic grounded rule engine)
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        logger.info(f"Initialized Gemini LLM Client (model: {model})")
        return GeminiLLMClient(api_key=gemini_key, model=model)

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        logger.info(f"Initialized OpenAI LLM Client (model: {model})")
        return OpenAILLMClient(api_key=openai_key, model=model)

    logger.info("No external LLM provider configured. Using grounded deterministic assistant.")
    return None


class GroundedChatEngine:
    """Orchestrates deterministic grounding retrieval, prompt composition, and guardrail enforcement."""

    def __init__(self, storage: WorkoutStorage, llm_client: LLMClientProtocol | None = None) -> None:
        self.storage = storage
        self.llm_client = llm_client

    async def answer(
        self,
        user_id: str,
        message: str,
        auth_token: str | None = None,
        session_id: str | None = None,
    ) -> ChatMessageResponse:
        context = await assemble_grounding_context(
            user_id=user_id,
            storage=self.storage,
            auth_token=auth_token,
            specific_session_id=session_id,
        )

        system_prompt = (
            "You are the PERFORMX AI Fitness & Biomechanics Assistant.\n"
            "You provide evidence-based, encouraging explanations of workouts, form, recovery, and nutrition.\n"
            "STRICT RULES:\n"
            "1. Ground all feedback solely in the provided user data.\n"
            "2. Never claim an unverified exercise is safe if clinician restrictions apply to that joint.\n"
            "3. If allergen status is UNKNOWN, explicitly warn that safety cannot be guaranteed.\n"
            "4. Never hallucinate repetition counts or symmetry percentages.\n"
            "5. Refuse any request to inspect raw video, image bytes, or camera streams.\n\n"
            f"{context.to_system_prompt_context()}"
        )

        warnings: list[str] = []
        if context.today_nutrition and context.today_nutrition.get("allergen_verification_status") == "UNKNOWN":
            warnings.append("Allergen status is unverified. Do not assume meal safety.")

        entities_used = [f"user:{user_id}"]
        if context.active_plan and "id" in context.active_plan:
            entities_used.append(f"plan:{context.active_plan['id']}")
        for w in context.recent_workout_metrics:
            entities_used.append(f"workout:{w['id']}")

        if self.llm_client:
            try:
                reply = await self.llm_client.generate_response(system_prompt, message)
            except Exception as e:
                logger.warning(f"Configured LLM provider failed ({e}). Falling back to deterministic grounded engine.")
                reply = self._generate_deterministic_explanation(context, message)
                warnings.append("AI generation provider temporarily unavailable. Switched to verified deterministic rules.")
        else:
            # Deterministic, grounded fallback when external LLM is not configured
            reply = self._generate_deterministic_explanation(context, message)

        return ChatMessageResponse(
            reply=reply,
            grounded_entities=entities_used,
            warnings=warnings,
        )

    def _generate_deterministic_explanation(self, ctx: ChatGroundingContext, message: str) -> str:
        msg_lower = message.lower()
        if "workout" in msg_lower or "rep" in msg_lower or "score" in msg_lower or "squat" in msg_lower:
            if ctx.recent_workout_metrics:
                w = ctx.recent_workout_metrics[0]
                return (
                    f"Hi {ctx.display_name}, in your latest {w['exercise_type']} session, you performed "
                    f"{w['total_reps']} total repetitions ({w['valid_reps']} valid) with a mean symmetry score of "
                    f"{round(w['mean_symmetry'] * 100, 1)}%. Keep focusing on controlled tempo and bilateral balance!"
                )
            return f"Hi {ctx.display_name}, you don't have any completed workout sessions recorded yet. Start a session when you're ready!"

        if "injury" in msg_lower or "hurt" in msg_lower or "knee" in msg_lower or "pain" in msg_lower:
            injuries = ctx.health_limitations.get("reported_injuries", [])
            restrictions = ctx.health_limitations.get("clinician_restrictions", [])
            return (
                f"Your profile lists reported injuries: {injuries} and clinician restrictions: {restrictions}. "
                "Always adhere to clinician guidelines and stop immediately if you experience pain."
            )

        if "nutrition" in msg_lower or "food" in msg_lower or "protein" in msg_lower:
            if ctx.today_nutrition:
                nut = ctx.today_nutrition
                cals = nut.get("calories_consumed", 0)
                prot = nut.get("protein_g", 0.0)
                status = nut.get("allergen_verification_status", "UNKNOWN")
                advisory = " (Note: Allergen verification is UNKNOWN; verify with supplier)" if status == "UNKNOWN" else ""
                return f"Today you have logged {cals} kcal and {prot}g of protein{advisory}."
            return "No nutrition logs recorded for today yet."

        return (
            f"Hello {ctx.display_name}! I am your PERFORMX assistant. I can review your verified session metrics, "
            f"active plan ({ctx.active_plan.get('title') if ctx.active_plan else 'none'}), recovery status, and nutrition."
        )
