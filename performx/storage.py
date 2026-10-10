"""PERFORMX Data Persistence Layer (Hardened).

Provides data contracts and repository interfaces for:
- User Profiles
- Validated Workout Session Summaries

Security & Privacy Guarantees:
- Strict user-scoped isolation enforced at both application and PostgREST RLS layers
- Idempotency on repeated saves
- Forwarding of user Bearer token to PostgREST for true database-level RLS evaluation
- Strict schema allowlisting and finite number enforcement (rejects NaN/Inf/oversized payloads)
- Zero storage of raw frames, images, or landmark coordinate histories
- Dual backend support: Supabase PostgREST (production) and InMemory (testing/mocking)
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
import math
import os
from typing import Any
import uuid

import httpx

from performx.contracts import SessionSummary

logger = logging.getLogger("performx.storage")


class StorageError(Exception):
    """Base exception for storage and database operations."""
    pass


class StorageConflictError(StorageError):
    """Raised when an entity conflict or violation occurs."""
    pass


@dataclass(frozen=True)
class UserProfile:
    """User profile record linked to an authenticated user ID."""
    id: str
    display_name: str | None
    created_at: str
    updated_at: str
    units: str = "metric"
    fitness_experience: str = "intermediate"
    primary_goal: str = "general_fitness"
    secondary_goal: str | None = None
    available_equipment: list[str] = field(default_factory=lambda: ["bodyweight"])
    preferred_training_days: list[int] = field(default_factory=lambda: [1, 3, 5])
    preferred_session_duration: int = 45
    dietary_preferences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["user_id"] = self.id
        return data


@dataclass(frozen=True)
class HealthProfile:
    """User health profile, reported symptoms, injuries and clinician restrictions."""
    user_id: str
    height_cm: float | None = None
    weight_kg: float | None = None
    body_fat_percentage: float | None = None
    resting_heart_rate: int | None = None
    reported_injuries: list[dict[str, Any]] = field(default_factory=list)
    reported_symptoms: list[str] = field(default_factory=list)
    clinician_restrictions: list[str] = field(default_factory=list)
    clinician_approved_plan: str | None = None
    allergies: list[str] = field(default_factory=list)
    dietary_restrictions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    data_provenance: str = "USER_REPORTED"
    last_assessed_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkoutPlan:
    """User workout plan containing validated exercises, sets, and parameters."""
    id: str
    user_id: str
    title: str
    description: str = ""
    is_active: bool = True
    version: int = 1
    exercises: list[dict[str, Any]] = field(default_factory=list)
    equipment_constraints: list[str] = field(default_factory=list)
    target_experience: str = "intermediate"
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdaptiveRecommendation:
    """Adaptive coaching recommendation with audit lifecycle tracking."""
    id: str
    user_id: str
    recommendation_type: str
    rationale: str
    status: str = "proposed"  # proposed, accepted, edited, dismissed, applied
    source_session_id: str | None = None
    applied_changes: dict[str, Any] = field(default_factory=dict)
    decision_timestamp: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryCheckin:
    """User recovery and symptom check-in record."""
    id: str
    user_id: str
    affected_area: str
    discomfort_score: int  # 0-10
    symptoms: str = ""
    exercise_adherence_score: float = 1.0
    notes: str = ""
    recorded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NutritionLog:
    """Daily nutrition and hydration record with explicit allergen verification."""
    id: str
    user_id: str
    log_date: str
    calories_consumed: int = 0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    water_ml: int = 0
    meals: list[dict[str, Any]] = field(default_factory=list)
    allergen_verification_status: str = "UNKNOWN"  # VERIFIED_PRESENT, VERIFIED_ABSENT, UNKNOWN
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MedicalDocumentMetadata:
    """Metadata reference for securely stored medical documents."""
    id: str
    user_id: str
    storage_path: str
    file_name: str
    file_size_bytes: int
    mime_type: str
    document_category: str = "general"
    description: str = ""
    status: str = "confirmed"  # pending_upload, confirmed, deleted
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrivacyConsent:
    """User privacy preferences and explicit feature consents."""
    user_id: str
    camera_processing_consent: bool = False
    document_processing_consent: bool = False
    data_analytics_consent: bool = False
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PersistedWorkoutSession:
    """Validated, immutable record of a completed workout session in storage."""
    id: str
    user_id: str
    exercise_type: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_frames_processed: int
    total_reps: int
    valid_reps: int
    mean_symmetry: float
    mean_rep_duration: float
    summary_metrics: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)



def sanitize_summary_metrics(summary: SessionSummary) -> dict[str, Any]:
    """Extract approved scalar summary metrics with strict allowlisting and finite numeric checks.
    
    Guarantees:
    - Never retains vision data, raw landmark arrays, frame histories, or nested dicts
    - Rejects or clips non-finite numbers (NaN, Infinity)
    - Limits string insight lengths and counts to prevent memory ballooning
    """
    if not summary.metrics:
        return {}

    raw_metrics = summary.metrics.to_dict()
    sanitized: dict[str, Any] = {}

    # 1. Non-negative integer counters
    int_fields = [
        "total_completed_reps", "accepted_reps", "rejected_reps",
        "incomplete_attempts", "aborted_attempts",
    ]
    for key in int_fields:
        val = raw_metrics.get(key)
        if isinstance(val, int) and val >= 0:
            sanitized[key] = val
        elif val is not None:
            raise ValueError(f"Metric field '{key}' must be a non-negative integer, got {val}")

    # 2. Finite non-negative floats
    float_fields = [
        "mean_duration", "min_duration", "max_duration", "duration_range",
        "mean_descent_duration", "mean_bottom_dwell", "mean_ascent_duration",
        "mean_min_knee_angle", "knee_angle_range",
    ]
    for key in float_fields:
        val = raw_metrics.get(key)
        if val is not None:
            if not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0.0:
                raise ValueError(f"Metric field '{key}' must be a finite non-negative number, got {val}")
            sanitized[key] = round(float(val), 3)

    # 3. Normalized score floats [0.0, 1.0]
    score_fields = ["mean_rep_symmetry", "mean_tracking_confidence"]
    for key in score_fields:
        val = raw_metrics.get(key)
        if val is not None:
            if not isinstance(val, (int, float)) or not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"Metric field '{key}' must be in [0.0, 1.0], got {val}")
            sanitized[key] = round(float(val), 4)

    # 4. Explainable insight strings (strictly bounded)
    insights = raw_metrics.get("explainable_insights")
    if isinstance(insights, list):
        clean_insights: list[str] = []
        for item in insights[:50]:  # Cap at 50 insights
            if isinstance(item, str):
                cleaned = item.strip()[:300]  # Cap at 300 characters
                if cleaned:
                    clean_insights.append(cleaned)
        sanitized["explainable_insights"] = clean_insights
    else:
        sanitized["explainable_insights"] = []

    return sanitized


class WorkoutStorage(ABC):
    """Abstract repository for PERFORMX user data and session persistence."""

    @abstractmethod
    async def get_profile(self, user_id: str, auth_token: str | None = None) -> UserProfile | None:
        """Retrieve a user's profile by ID."""
        pass

    @abstractmethod
    async def upsert_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        units: str = "metric",
        fitness_experience: str = "intermediate",
        primary_goal: str = "general_fitness",
        secondary_goal: str | None = None,
        available_equipment: list[str] | None = None,
        preferred_training_days: list[int] | None = None,
        preferred_session_duration: int = 45,
        dietary_preferences: list[str] | None = None,
        auth_token: str | None = None,
    ) -> UserProfile:
        """Create or update a user's full profile and preferences."""
        pass

    @abstractmethod
    async def get_health_profile(self, user_id: str, auth_token: str | None = None) -> HealthProfile | None:
        """Retrieve a user's health profile and medical annotations."""
        pass

    @abstractmethod
    async def upsert_health_profile(self, user_id: str, data: dict[str, Any], auth_token: str | None = None) -> HealthProfile:
        """Update or create a user's health profile."""
        pass

    @abstractmethod
    async def get_active_workout_plan(self, user_id: str, auth_token: str | None = None) -> WorkoutPlan | None:
        """Retrieve current active workout plan."""
        pass

    @abstractmethod
    async def save_workout_plan(self, user_id: str, plan_data: dict[str, Any], auth_token: str | None = None) -> WorkoutPlan:
        """Create or update a user's workout plan."""
        pass

    @abstractmethod
    async def list_recommendations(self, user_id: str, auth_token: str | None = None) -> list[AdaptiveRecommendation]:
        """List adaptive coaching recommendations for a user."""
        pass

    @abstractmethod
    async def create_recommendation(self, user_id: str, rec_data: dict[str, Any], auth_token: str | None = None) -> AdaptiveRecommendation:
        """Create a new adaptive recommendation."""
        pass

    @abstractmethod
    async def update_recommendation_status(self, user_id: str, rec_id: str, status: str, auth_token: str | None = None) -> AdaptiveRecommendation | None:
        """Update recommendation decision status (accepted, dismissed, applied)."""
        pass

    @abstractmethod
    async def log_recovery_checkin(self, user_id: str, checkin_data: dict[str, Any], auth_token: str | None = None) -> RecoveryCheckin:
        """Record an injury symptom or recovery check-in."""
        pass

    @abstractmethod
    async def list_recovery_checkins(self, user_id: str, auth_token: str | None = None) -> list[RecoveryCheckin]:
        """Retrieve recovery history for a user."""
        pass

    @abstractmethod
    async def get_nutrition_log(self, user_id: str, log_date: str, auth_token: str | None = None) -> NutritionLog | None:
        """Retrieve nutrition and hydration log for a specific date."""
        pass

    @abstractmethod
    async def upsert_nutrition_log(self, user_id: str, log_data: dict[str, Any], auth_token: str | None = None) -> NutritionLog:
        """Record or update a daily nutrition log."""
        pass

    @abstractmethod
    async def save_medical_document(self, user_id: str, doc_data: dict[str, Any], auth_token: str | None = None) -> MedicalDocumentMetadata:
        """Store medical document metadata."""
        pass

    @abstractmethod
    async def list_medical_documents(self, user_id: str, auth_token: str | None = None) -> list[MedicalDocumentMetadata]:
        """List confirmed medical documents for a user."""
        pass

    @abstractmethod
    async def get_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> MedicalDocumentMetadata | None:
        """Retrieve a specific medical document metadata record owned by user_id."""
        pass

    @abstractmethod
    async def delete_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> bool:
        """Delete a medical document metadata record."""
        pass

    @abstractmethod
    async def get_privacy_consent(self, user_id: str, auth_token: str | None = None) -> PrivacyConsent | None:
        """Retrieve privacy and consent flags."""
        pass

    @abstractmethod
    async def update_privacy_consent(self, user_id: str, consents: dict[str, Any], auth_token: str | None = None) -> PrivacyConsent:
        """Update user privacy and consent flags."""
        pass

    @abstractmethod
    async def export_all_user_data(self, user_id: str, auth_token: str | None = None) -> dict[str, Any]:
        """Export all user data for GDPR/CCPA data export."""
        pass

    @abstractmethod
    async def delete_all_user_data(self, user_id: str, auth_token: str | None = None) -> bool:
        """Permanently delete all user records (account deletion)."""
        pass

    @abstractmethod
    async def save_workout(
        self,
        user_id: str,
        summary: SessionSummary,
        exercise_type: str = "squat",
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession:
        """Persist a completed workout summary with idempotency."""
        pass

    @abstractmethod
    async def list_workouts(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        auth_token: str | None = None,
    ) -> tuple[list[PersistedWorkoutSession], int]:
        """List a user's saved workout summaries with pagination."""
        pass

    @abstractmethod
    async def get_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession | None:
        """Retrieve a specific workout session owned by user_id."""
        pass

    @abstractmethod
    async def delete_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> bool:
        """Delete a specific workout session owned by user_id."""
        pass


class InMemoryWorkoutStorage(WorkoutStorage):
    """Thread-safe in-memory repository for unit testing and offline execution."""

    def __init__(self):
        self._profiles: dict[str, UserProfile] = {}
        self._health_profiles: dict[str, HealthProfile] = {}
        self._workout_plans: dict[str, list[WorkoutPlan]] = {}
        self._recommendations: dict[str, list[AdaptiveRecommendation]] = {}
        self._recovery_checkins: dict[str, list[RecoveryCheckin]] = {}
        # Key: (user_id, log_date) -> NutritionLog
        self._nutrition_logs: dict[tuple[str, str], NutritionLog] = {}
        self._medical_docs: dict[str, MedicalDocumentMetadata] = {}
        self._consents: dict[str, PrivacyConsent] = {}
        # Map: workout_id -> PersistedWorkoutSession
        self._workouts: dict[str, PersistedWorkoutSession] = {}

    async def get_profile(self, user_id: str, auth_token: str | None = None) -> UserProfile | None:
        return self._profiles.get(user_id)

    async def upsert_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        units: str = "metric",
        fitness_experience: str = "intermediate",
        primary_goal: str = "general_fitness",
        secondary_goal: str | None = None,
        available_equipment: list[str] | None = None,
        preferred_training_days: list[int] | None = None,
        preferred_session_duration: int = 45,
        dietary_preferences: list[str] | None = None,
        auth_token: str | None = None,
    ) -> UserProfile:
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = self._profiles.get(user_id)
        created_at = existing.created_at if existing else now_iso
        profile = UserProfile(
            id=user_id,
            display_name=display_name.strip() if display_name else (existing.display_name if existing else None),
            created_at=created_at,
            updated_at=now_iso,
            units=units,
            fitness_experience=fitness_experience,
            primary_goal=primary_goal,
            secondary_goal=secondary_goal,
            available_equipment=available_equipment if available_equipment is not None else (existing.available_equipment if existing else ["bodyweight"]),
            preferred_training_days=preferred_training_days if preferred_training_days is not None else (existing.preferred_training_days if existing else [1, 3, 5]),
            preferred_session_duration=preferred_session_duration,
            dietary_preferences=dietary_preferences if dietary_preferences is not None else (existing.dietary_preferences if existing else []),
        )
        self._profiles[user_id] = profile
        return profile

    async def get_health_profile(self, user_id: str, auth_token: str | None = None) -> HealthProfile | None:
        return self._health_profiles.get(user_id)

    async def upsert_health_profile(self, user_id: str, data: dict[str, Any], auth_token: str | None = None) -> HealthProfile:
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = self._health_profiles.get(user_id)
        hp = HealthProfile(
            user_id=user_id,
            height_cm=data.get("height_cm", existing.height_cm if existing else None),
            weight_kg=data.get("weight_kg", existing.weight_kg if existing else None),
            body_fat_percentage=data.get("body_fat_percentage", existing.body_fat_percentage if existing else None),
            resting_heart_rate=data.get("resting_heart_rate", existing.resting_heart_rate if existing else None),
            reported_injuries=data.get("reported_injuries", existing.reported_injuries if existing else []),
            reported_symptoms=data.get("reported_symptoms", existing.reported_symptoms if existing else []),
            clinician_restrictions=data.get("clinician_restrictions", existing.clinician_restrictions if existing else []),
            clinician_approved_plan=data.get("clinician_approved_plan", existing.clinician_approved_plan if existing else None),
            allergies=data.get("allergies", existing.allergies if existing else []),
            dietary_restrictions=data.get("dietary_restrictions", existing.dietary_restrictions if existing else []),
            medications=data.get("medications", existing.medications if existing else []),
            data_provenance=data.get("data_provenance", "USER_REPORTED"),
            last_assessed_at=now_iso,
            updated_at=now_iso,
        )
        self._health_profiles[user_id] = hp
        return hp

    async def get_active_workout_plan(self, user_id: str, auth_token: str | None = None) -> WorkoutPlan | None:
        plans = self._workout_plans.get(user_id, [])
        for p in plans:
            if p.is_active:
                return p
        return plans[0] if plans else None

    async def save_workout_plan(self, user_id: str, plan_data: dict[str, Any], auth_token: str | None = None) -> WorkoutPlan:
        now_iso = datetime.now(timezone.utc).isoformat()
        plan_id = plan_data.get("id") or str(uuid.uuid4())
        plan = WorkoutPlan(
            id=plan_id,
            user_id=user_id,
            title=plan_data.get("title", "My Custom Plan"),
            description=plan_data.get("description", ""),
            is_active=plan_data.get("is_active", True),
            version=plan_data.get("version", 1),
            exercises=plan_data.get("exercises", []),
            equipment_constraints=plan_data.get("equipment_constraints", []),
            target_experience=plan_data.get("target_experience", "intermediate"),
            created_at=now_iso,
            updated_at=now_iso,
        )
        if user_id not in self._workout_plans:
            self._workout_plans[user_id] = []
        if plan.is_active:
            # deactivate older active plans
            self._workout_plans[user_id] = [
                WorkoutPlan(
                    id=p.id, user_id=p.user_id, title=p.title, description=p.description,
                    is_active=False, version=p.version, exercises=p.exercises,
                    equipment_constraints=p.equipment_constraints, target_experience=p.target_experience,
                    created_at=p.created_at, updated_at=p.updated_at
                ) if p.id != plan.id else plan
                for p in self._workout_plans[user_id]
            ]
        # Append or update
        found = False
        for idx, p in enumerate(self._workout_plans[user_id]):
            if p.id == plan.id:
                self._workout_plans[user_id][idx] = plan
                found = True
                break
        if not found:
            self._workout_plans[user_id].append(plan)
        return plan

    async def list_recommendations(self, user_id: str, auth_token: str | None = None) -> list[AdaptiveRecommendation]:
        return self._recommendations.get(user_id, [])

    async def create_recommendation(self, user_id: str, rec_data: dict[str, Any], auth_token: str | None = None) -> AdaptiveRecommendation:
        now_iso = datetime.now(timezone.utc).isoformat()
        rec_id = str(uuid.uuid4())
        rec = AdaptiveRecommendation(
            id=rec_id,
            user_id=user_id,
            recommendation_type=rec_data.get("recommendation_type", "load_adjustment"),
            rationale=rec_data.get("rationale", ""),
            status=rec_data.get("status", "proposed"),
            source_session_id=rec_data.get("source_session_id"),
            applied_changes=rec_data.get("applied_changes", {}),
            created_at=now_iso,
        )
        if user_id not in self._recommendations:
            self._recommendations[user_id] = []
        self._recommendations[user_id].append(rec)
        return rec

    async def update_recommendation_status(self, user_id: str, rec_id: str, status: str, auth_token: str | None = None) -> AdaptiveRecommendation | None:
        now_iso = datetime.now(timezone.utc).isoformat()
        user_recs = self._recommendations.get(user_id, [])
        for idx, r in enumerate(user_recs):
            if r.id == rec_id:
                updated = AdaptiveRecommendation(
                    id=r.id,
                    user_id=r.user_id,
                    recommendation_type=r.recommendation_type,
                    rationale=r.rationale,
                    status=status,
                    source_session_id=r.source_session_id,
                    applied_changes=r.applied_changes,
                    decision_timestamp=now_iso,
                    created_at=r.created_at,
                )
                user_recs[idx] = updated
                return updated
        return None

    async def log_recovery_checkin(self, user_id: str, checkin_data: dict[str, Any], auth_token: str | None = None) -> RecoveryCheckin:
        now_iso = datetime.now(timezone.utc).isoformat()
        chk = RecoveryCheckin(
            id=str(uuid.uuid4()),
            user_id=user_id,
            affected_area=checkin_data.get("affected_area", "general"),
            discomfort_score=int(checkin_data.get("discomfort_score", 0)),
            symptoms=checkin_data.get("symptoms", ""),
            exercise_adherence_score=float(checkin_data.get("exercise_adherence_score", 1.0)),
            notes=checkin_data.get("notes", ""),
            recorded_at=now_iso,
        )
        if user_id not in self._recovery_checkins:
            self._recovery_checkins[user_id] = []
        self._recovery_checkins[user_id].insert(0, chk)
        return chk

    async def list_recovery_checkins(self, user_id: str, auth_token: str | None = None) -> list[RecoveryCheckin]:
        return self._recovery_checkins.get(user_id, [])

    async def get_nutrition_log(self, user_id: str, log_date: str, auth_token: str | None = None) -> NutritionLog | None:
        return self._nutrition_logs.get((user_id, log_date))

    async def upsert_nutrition_log(self, user_id: str, log_data: dict[str, Any], auth_token: str | None = None) -> NutritionLog:
        now_iso = datetime.now(timezone.utc).isoformat()
        log_date = log_data.get("log_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        key = (user_id, log_date)
        existing = self._nutrition_logs.get(key)
        log_id = existing.id if existing else str(uuid.uuid4())
        nlog = NutritionLog(
            id=log_id,
            user_id=user_id,
            log_date=log_date,
            calories_consumed=int(log_data.get("calories_consumed", 0)),
            protein_g=float(log_data.get("protein_g", 0.0)),
            carbs_g=float(log_data.get("carbs_g", 0.0)),
            fat_g=float(log_data.get("fat_g", 0.0)),
            water_ml=int(log_data.get("water_ml", 0)),
            meals=log_data.get("meals", []),
            allergen_verification_status=log_data.get("allergen_verification_status", "UNKNOWN"),
            updated_at=now_iso,
        )
        self._nutrition_logs[key] = nlog
        return nlog

    async def save_medical_document(self, user_id: str, doc_data: dict[str, Any], auth_token: str | None = None) -> MedicalDocumentMetadata:
        now_iso = datetime.now(timezone.utc).isoformat()
        doc_id = str(uuid.uuid4())
        doc = MedicalDocumentMetadata(
            id=doc_id,
            user_id=user_id,
            storage_path=doc_data.get("storage_path", f"user_{user_id}/{doc_id}"),
            file_name=doc_data.get("file_name", "document.pdf"),
            file_size_bytes=int(doc_data.get("file_size_bytes", 0)),
            mime_type=doc_data.get("mime_type", "application/pdf"),
            document_category=doc_data.get("document_category", "general"),
            description=doc_data.get("description", ""),
            status="confirmed",
            created_at=now_iso,
        )
        self._medical_docs[doc_id] = doc
        return doc

    async def list_medical_documents(self, user_id: str, auth_token: str | None = None) -> list[MedicalDocumentMetadata]:
        return [d for d in self._medical_docs.values() if d.user_id == user_id and d.status != "deleted"]

    async def get_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> MedicalDocumentMetadata | None:
        doc = self._medical_docs.get(doc_id)
        if doc and doc.user_id == user_id and doc.status != "deleted":
            return doc
        return None

    async def delete_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> bool:
        doc = self._medical_docs.get(doc_id)
        if doc and doc.user_id == user_id:
            del self._medical_docs[doc_id]
            return True
        return False

    async def get_privacy_consent(self, user_id: str, auth_token: str | None = None) -> PrivacyConsent | None:
        return self._consents.get(user_id)

    async def update_privacy_consent(self, user_id: str, consents: dict[str, Any], auth_token: str | None = None) -> PrivacyConsent:
        now_iso = datetime.now(timezone.utc).isoformat()
        pc = PrivacyConsent(
            user_id=user_id,
            camera_processing_consent=bool(consents.get("camera_processing_consent", False)),
            document_processing_consent=bool(consents.get("document_processing_consent", False)),
            data_analytics_consent=bool(consents.get("data_analytics_consent", False)),
            updated_at=now_iso,
        )
        self._consents[user_id] = pc
        return pc

    async def export_all_user_data(self, user_id: str, auth_token: str | None = None) -> dict[str, Any]:
        """GDPR/CCPA comprehensive user archive."""
        profile = await self.get_profile(user_id)
        health = await self.get_health_profile(user_id)
        workouts, _ = await self.list_workouts(user_id, limit=1000)
        plans = self._workout_plans.get(user_id, [])
        recs = await self.list_recommendations(user_id)
        recovery = await self.list_recovery_checkins(user_id)
        nutrition = [n.to_dict() for (uid, _), n in self._nutrition_logs.items() if uid == user_id]
        docs = await self.list_medical_documents(user_id)
        consent = await self.get_privacy_consent(user_id)

        return {
            "user_id": user_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "profile": profile.to_dict() if profile else None,
            "health_profile": health.to_dict() if health else None,
            "workout_history": [w.to_dict() for w in workouts],
            "workout_plans": [p.to_dict() for p in plans],
            "adaptive_recommendations": [r.to_dict() for r in recs],
            "recovery_checkins": [rc.to_dict() for rc in recovery],
            "nutrition_logs": nutrition,
            "medical_documents_metadata": [d.to_dict() for d in docs],
            "privacy_consents": consent.to_dict() if consent else None,
        }

    async def delete_all_user_data(self, user_id: str, auth_token: str | None = None) -> bool:
        """Purge all user-scoped data permanently."""
        self._profiles.pop(user_id, None)
        self._health_profiles.pop(user_id, None)
        self._workout_plans.pop(user_id, None)
        self._recommendations.pop(user_id, None)
        self._recovery_checkins.pop(user_id, None)
        self._consents.pop(user_id, None)

        to_del_nut = [k for k in self._nutrition_logs if k[0] == user_id]
        for k in to_del_nut:
            del self._nutrition_logs[k]

        to_del_doc = [k for k, d in self._medical_docs.items() if d.user_id == user_id]
        for k in to_del_doc:
            del self._medical_docs[k]

        to_del_wo = [k for k, w in self._workouts.items() if w.user_id == user_id]
        for k in to_del_wo:
            del self._workouts[k]

        return True


    async def save_workout(
        self,
        user_id: str,
        summary: SessionSummary,
        exercise_type: str = "squat",
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession:
        workout_id = summary.session_id

        # Idempotency check: if already saved for this user, return existing
        if workout_id in self._workouts:
            existing = self._workouts[workout_id]
            if existing.user_id == user_id:
                return existing
            raise StorageConflictError(f"Workout ID '{workout_id}' is owned by another user")

        # Finite timestamp checks
        if not math.isfinite(summary.start_time) or not math.isfinite(summary.end_time):
            raise ValueError("Workout summary start_time and end_time must be finite numbers")

        try:
            start_iso = datetime.fromtimestamp(summary.start_time, tz=timezone.utc).isoformat()
            end_iso = datetime.fromtimestamp(summary.end_time, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            now_dt = datetime.now(timezone.utc)
            start_iso = now_dt.isoformat()
            end_iso = now_dt.isoformat()

        now_iso = datetime.now(timezone.utc).isoformat()
        duration = max(0.0, summary.end_time - summary.start_time)
        metrics = sanitize_summary_metrics(summary)

        record = PersistedWorkoutSession(
            id=workout_id,
            user_id=user_id,
            exercise_type=exercise_type,
            start_time=start_iso,
            end_time=end_iso,
            duration_seconds=duration,
            total_frames_processed=summary.total_frames_processed,
            total_reps=summary.total_reps,
            valid_reps=summary.valid_reps,
            mean_symmetry=summary.mean_symmetry,
            mean_rep_duration=summary.mean_rep_duration,
            summary_metrics=metrics,
            created_at=now_iso,
        )
        self._workouts[workout_id] = record
        return record

    async def list_workouts(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        auth_token: str | None = None,
    ) -> tuple[list[PersistedWorkoutSession], int]:
        user_records = [
            w for w in self._workouts.values()
            if w.user_id == user_id
        ]
        # Sort newest first
        user_records.sort(key=lambda x: x.created_at, reverse=True)
        total_count = len(user_records)
        paged = user_records[offset: offset + limit]
        return paged, total_count

    async def get_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession | None:
        record = self._workouts.get(workout_id)
        if record and record.user_id == user_id:
            return record
        return None

    async def delete_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> bool:
        record = self._workouts.get(workout_id)
        if record and record.user_id == user_id:
            del self._workouts[workout_id]
            return True
        return False


class SupabaseWorkoutStorage(WorkoutStorage):
    """Production repository interacting with Supabase PostgREST endpoints."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
    ):
        self.url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = supabase_key or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
        if not self.url or not self.key:
            raise StorageError("SupabaseWorkoutStorage requires SUPABASE_URL and SUPABASE_KEY to be configured.")

    def _headers(self, user_token: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self.key,
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
        return headers

    async def get_profile(self, user_id: str, auth_token: str | None = None) -> UserProfile | None:
        endpoint = f"{self.url}/rest/v1/profiles?id=eq.{user_id}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                logger.error("Supabase get_profile failed: HTTP %s", res.status_code)
                raise StorageError("Failed to fetch user profile")
            data = res.json()
            if not data:
                return None
            item = data[0]
            return UserProfile(
                id=item["id"],
                display_name=item.get("display_name"),
                created_at=item["created_at"],
                updated_at=item["updated_at"],
            )

    async def upsert_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        units: str = "metric",
        fitness_experience: str = "intermediate",
        primary_goal: str = "general_fitness",
        secondary_goal: str | None = None,
        available_equipment: list[str] | None = None,
        preferred_training_days: list[int] | None = None,
        preferred_session_duration: int = 45,
        dietary_preferences: list[str] | None = None,
        auth_token: str | None = None,
    ) -> UserProfile:
        endpoint = f"{self.url}/rest/v1/profiles"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload: dict[str, Any] = {
            "id": user_id,
            "updated_at": now_iso,
            "units": units,
            "fitness_experience": fitness_experience,
            "primary_goal": primary_goal,
            "secondary_goal": secondary_goal,
            "available_equipment": available_equipment if available_equipment is not None else ["bodyweight"],
            "preferred_training_days": preferred_training_days if preferred_training_days is not None else [1, 3, 5],
            "preferred_session_duration": preferred_session_duration,
            "dietary_preferences": dietary_preferences if dietary_preferences is not None else [],
        }
        if display_name is not None:
            payload["display_name"] = display_name.strip()

        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error("Supabase upsert_profile failed: HTTP %s", res.status_code)
                raise StorageError("Failed to update user profile")
            data = res.json()
            item = data[0] if isinstance(data, list) and data else payload
            return UserProfile(
                id=item["id"],
                display_name=item.get("display_name"),
                created_at=item.get("created_at", now_iso),
                updated_at=item.get("updated_at", now_iso),
                units=item.get("units", "metric"),
                fitness_experience=item.get("fitness_experience", "intermediate"),
                primary_goal=item.get("primary_goal", "general_fitness"),
                secondary_goal=item.get("secondary_goal"),
                available_equipment=item.get("available_equipment", ["bodyweight"]),
                preferred_training_days=item.get("preferred_training_days", [1, 3, 5]),
                preferred_session_duration=item.get("preferred_session_duration", 45),
                dietary_preferences=item.get("dietary_preferences", []),
            )

    async def get_health_profile(self, user_id: str, auth_token: str | None = None) -> HealthProfile | None:
        endpoint = f"{self.url}/rest/v1/health_profiles?user_id=eq.{user_id}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                logger.error("Supabase get_health_profile failed: HTTP %s", res.status_code)
                raise StorageError("Failed to fetch health profile")
            data = res.json()
            if not data:
                return None
            return HealthProfile(**data[0])

    async def upsert_health_profile(self, user_id: str, data: dict[str, Any], auth_token: str | None = None) -> HealthProfile:
        endpoint = f"{self.url}/rest/v1/health_profiles"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "user_id": user_id,
            "height_cm": data.get("height_cm"),
            "weight_kg": data.get("weight_kg"),
            "body_fat_percentage": data.get("body_fat_percentage"),
            "resting_heart_rate": data.get("resting_heart_rate"),
            "reported_injuries": data.get("reported_injuries", []),
            "reported_symptoms": data.get("reported_symptoms", []),
            "clinician_restrictions": data.get("clinician_restrictions", []),
            "clinician_approved_plan": data.get("clinician_approved_plan"),
            "allergies": data.get("allergies", []),
            "dietary_restrictions": data.get("dietary_restrictions", []),
            "medications": data.get("medications", []),
            "data_provenance": data.get("data_provenance", "USER_REPORTED"),
            "last_assessed_at": now_iso,
            "updated_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error("Supabase upsert_health_profile failed: HTTP %s", res.status_code)
                raise StorageError("Failed to update health profile")
            res_data = res.json()
            item = res_data[0] if isinstance(res_data, list) and res_data else payload
            return HealthProfile(**item)

    async def get_active_workout_plan(self, user_id: str, auth_token: str | None = None) -> WorkoutPlan | None:
        endpoint = f"{self.url}/rest/v1/workout_plans?user_id=eq.{user_id}&is_active=eq.true&order=created_at.desc&limit=1&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                logger.error("Supabase get_active_workout_plan failed: HTTP %s", res.status_code)
                raise StorageError("Failed to fetch workout plan")
            data = res.json()
            if not data:
                return None
            return WorkoutPlan(**data[0])

    async def save_workout_plan(self, user_id: str, plan_data: dict[str, Any], auth_token: str | None = None) -> WorkoutPlan:
        endpoint = f"{self.url}/rest/v1/workout_plans"
        now_iso = datetime.now(timezone.utc).isoformat()
        plan_id = plan_data.get("id") or str(uuid.uuid4())
        payload = {
            "id": plan_id,
            "user_id": user_id,
            "title": plan_data.get("title", "Custom Plan"),
            "description": plan_data.get("description", ""),
            "is_active": plan_data.get("is_active", True),
            "version": plan_data.get("version", 1),
            "exercises": plan_data.get("exercises", []),
            "equipment_constraints": plan_data.get("equipment_constraints", []),
            "target_experience": plan_data.get("target_experience", "intermediate"),
            "updated_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error("Supabase save_workout_plan failed: HTTP %s", res.status_code)
                raise StorageError("Failed to save workout plan")
            data = res.json()
            item = data[0] if isinstance(data, list) and data else payload
            return WorkoutPlan(**item)

    async def list_recommendations(self, user_id: str, auth_token: str | None = None) -> list[AdaptiveRecommendation]:
        endpoint = f"{self.url}/rest/v1/adaptive_recommendations?user_id=eq.{user_id}&order=created_at.desc&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to list recommendations")
            return [AdaptiveRecommendation(**item) for item in res.json()]

    async def create_recommendation(self, user_id: str, rec_data: dict[str, Any], auth_token: str | None = None) -> AdaptiveRecommendation:
        endpoint = f"{self.url}/rest/v1/adaptive_recommendations"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "recommendation_type": rec_data.get("recommendation_type", "load_adjustment"),
            "rationale": rec_data.get("rationale", ""),
            "status": rec_data.get("status", "proposed"),
            "source_session_id": rec_data.get("source_session_id"),
            "applied_changes": rec_data.get("applied_changes", {}),
            "created_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                raise StorageError("Failed to create recommendation")
            return AdaptiveRecommendation(**res.json()[0])

    async def update_recommendation_status(self, user_id: str, rec_id: str, status: str, auth_token: str | None = None) -> AdaptiveRecommendation | None:
        endpoint = f"{self.url}/rest/v1/adaptive_recommendations?id=eq.{rec_id}&user_id=eq.{user_id}"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {"status": status, "decision_timestamp": now_iso}
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient() as client:
            res = await client.patch(endpoint, json=payload, headers=headers)
            if res.status_code != 200:
                raise StorageError("Failed to update recommendation")
            data = res.json()
            return AdaptiveRecommendation(**data[0]) if data else None

    async def log_recovery_checkin(self, user_id: str, checkin_data: dict[str, Any], auth_token: str | None = None) -> RecoveryCheckin:
        endpoint = f"{self.url}/rest/v1/recovery_checkins"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "affected_area": checkin_data.get("affected_area", "general"),
            "discomfort_score": int(checkin_data.get("discomfort_score", 0)),
            "symptoms": checkin_data.get("symptoms", ""),
            "exercise_adherence_score": float(checkin_data.get("exercise_adherence_score", 1.0)),
            "notes": checkin_data.get("notes", ""),
            "recorded_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                raise StorageError("Failed to log recovery checkin")
            return RecoveryCheckin(**res.json()[0])

    async def list_recovery_checkins(self, user_id: str, auth_token: str | None = None) -> list[RecoveryCheckin]:
        endpoint = f"{self.url}/rest/v1/recovery_checkins?user_id=eq.{user_id}&order=recorded_at.desc&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to list recovery checkins")
            return [RecoveryCheckin(**item) for item in res.json()]

    async def get_nutrition_log(self, user_id: str, log_date: str, auth_token: str | None = None) -> NutritionLog | None:
        endpoint = f"{self.url}/rest/v1/nutrition_logs?user_id=eq.{user_id}&log_date=eq.{log_date}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to get nutrition log")
            data = res.json()
            return NutritionLog(**data[0]) if data else None

    async def upsert_nutrition_log(self, user_id: str, log_data: dict[str, Any], auth_token: str | None = None) -> NutritionLog:
        endpoint = f"{self.url}/rest/v1/nutrition_logs"
        now_iso = datetime.now(timezone.utc).isoformat()
        log_date = log_data.get("log_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        payload = {
            "user_id": user_id,
            "log_date": log_date,
            "calories_consumed": int(log_data.get("calories_consumed", 0)),
            "protein_g": float(log_data.get("protein_g", 0.0)),
            "carbs_g": float(log_data.get("carbs_g", 0.0)),
            "fat_g": float(log_data.get("fat_g", 0.0)),
            "water_ml": int(log_data.get("water_ml", 0)),
            "meals": log_data.get("meals", []),
            "allergen_verification_status": log_data.get("allergen_verification_status", "UNKNOWN"),
            "updated_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                raise StorageError("Failed to save nutrition log")
            return NutritionLog(**res.json()[0])

    async def save_medical_document(self, user_id: str, doc_data: dict[str, Any], auth_token: str | None = None) -> MedicalDocumentMetadata:
        endpoint = f"{self.url}/rest/v1/medical_documents"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "storage_path": doc_data.get("storage_path", ""),
            "file_name": doc_data.get("file_name", "document.pdf"),
            "file_size_bytes": int(doc_data.get("file_size_bytes", 0)),
            "mime_type": doc_data.get("mime_type", "application/pdf"),
            "document_category": doc_data.get("document_category", "general"),
            "description": doc_data.get("description", ""),
            "status": "confirmed",
            "created_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                raise StorageError("Failed to save medical document")
            return MedicalDocumentMetadata(**res.json()[0])

    async def list_medical_documents(self, user_id: str, auth_token: str | None = None) -> list[MedicalDocumentMetadata]:
        endpoint = f"{self.url}/rest/v1/medical_documents?user_id=eq.{user_id}&status=neq.deleted&order=created_at.desc&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to list medical documents")
            return [MedicalDocumentMetadata(**item) for item in res.json()]

    async def get_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> MedicalDocumentMetadata | None:
        endpoint = f"{self.url}/rest/v1/medical_documents?id=eq.{doc_id}&user_id=eq.{user_id}&status=neq.deleted&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to get medical document")
            data = res.json()
            return MedicalDocumentMetadata(**data[0]) if data else None

    async def delete_medical_document(self, user_id: str, doc_id: str, auth_token: str | None = None) -> bool:
        endpoint = f"{self.url}/rest/v1/medical_documents?id=eq.{doc_id}&user_id=eq.{user_id}"
        payload = {"status": "deleted"}
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation"
        async with httpx.AsyncClient() as client:
            res = await client.patch(endpoint, json=payload, headers=headers)
            return res.status_code == 200 and len(res.json()) > 0

    async def get_privacy_consent(self, user_id: str, auth_token: str | None = None) -> PrivacyConsent | None:
        endpoint = f"{self.url}/rest/v1/privacy_consents?user_id=eq.{user_id}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                raise StorageError("Failed to get privacy consent")
            data = res.json()
            return PrivacyConsent(**data[0]) if data else None

    async def update_privacy_consent(self, user_id: str, consents: dict[str, Any], auth_token: str | None = None) -> PrivacyConsent:
        endpoint = f"{self.url}/rest/v1/privacy_consents"
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "user_id": user_id,
            "camera_processing_consent": bool(consents.get("camera_processing_consent", False)),
            "document_processing_consent": bool(consents.get("document_processing_consent", False)),
            "data_analytics_consent": bool(consents.get("data_analytics_consent", False)),
            "updated_at": now_iso,
        }
        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                raise StorageError("Failed to update privacy consent")
            return PrivacyConsent(**res.json()[0])

    async def export_all_user_data(self, user_id: str, auth_token: str | None = None) -> dict[str, Any]:
        profile = await self.get_profile(user_id, auth_token)
        health = await self.get_health_profile(user_id, auth_token)
        workouts, _ = await self.list_workouts(user_id, limit=1000, auth_token=auth_token)
        plan = await self.get_active_workout_plan(user_id, auth_token)
        recs = await self.list_recommendations(user_id, auth_token)
        recovery = await self.list_recovery_checkins(user_id, auth_token)
        docs = await self.list_medical_documents(user_id, auth_token)
        consent = await self.get_privacy_consent(user_id, auth_token)

        return {
            "user_id": user_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "profile": profile.to_dict() if profile else None,
            "health_profile": health.to_dict() if health else None,
            "workout_history": [w.to_dict() for w in workouts],
            "active_workout_plan": plan.to_dict() if plan else None,
            "adaptive_recommendations": [r.to_dict() for r in recs],
            "recovery_checkins": [rc.to_dict() for rc in recovery],
            "medical_documents_metadata": [d.to_dict() for d in docs],
            "privacy_consents": consent.to_dict() if consent else None,
        }

    async def delete_all_user_data(self, user_id: str, auth_token: str | None = None) -> bool:
        # In Supabase with ON DELETE CASCADE from auth.users, deleting user cascades.
        # Alternatively delete rows directly:
        tables = [
            "workout_sessions", "workout_plans", "health_profiles",
            "adaptive_recommendations", "recovery_checkins", "nutrition_logs",
            "medical_documents", "privacy_consents", "profiles"
        ]
        headers = self._headers(auth_token)
        async with httpx.AsyncClient() as client:
            for tbl in tables:
                col = "id" if tbl == "profiles" else "user_id"
                await client.delete(f"{self.url}/rest/v1/{tbl}?{col}=eq.{user_id}", headers=headers)
        return True


    async def save_workout(
        self,
        user_id: str,
        summary: SessionSummary,
        exercise_type: str = "squat",
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession:
        endpoint = f"{self.url}/rest/v1/workout_sessions"

        if not math.isfinite(summary.start_time) or not math.isfinite(summary.end_time):
            raise ValueError("Workout summary start_time and end_time must be finite numbers")

        try:
            start_iso = datetime.fromtimestamp(summary.start_time, tz=timezone.utc).isoformat()
            end_iso = datetime.fromtimestamp(summary.end_time, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            now_dt = datetime.now(timezone.utc)
            start_iso = now_dt.isoformat()
            end_iso = now_dt.isoformat()

        now_iso = datetime.now(timezone.utc).isoformat()
        duration = max(0.0, summary.end_time - summary.start_time)
        metrics = sanitize_summary_metrics(summary)

        payload = {
            "id": summary.session_id,
            "user_id": user_id,
            "exercise_type": exercise_type,
            "start_time": start_iso,
            "end_time": end_iso,
            "duration_seconds": duration,
            "total_frames_processed": summary.total_frames_processed,
            "total_reps": summary.total_reps,
            "valid_reps": summary.valid_reps,
            "mean_symmetry": summary.mean_symmetry,
            "mean_rep_duration": summary.mean_rep_duration,
            "summary_metrics": metrics,
            "created_at": now_iso,
        }

        headers = self._headers(auth_token)
        headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        async with httpx.AsyncClient() as client:
            res = await client.post(endpoint, json=payload, headers=headers)
            if res.status_code not in (200, 201):
                logger.error("Supabase save_workout failed: HTTP %s", res.status_code)
                raise StorageError("Failed to persist workout session")
            data = res.json()
            item = data[0] if isinstance(data, list) and data else payload
            return PersistedWorkoutSession(**item)

    async def list_workouts(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        auth_token: str | None = None,
    ) -> tuple[list[PersistedWorkoutSession], int]:
        endpoint = (
            f"{self.url}/rest/v1/workout_sessions?"
            f"user_id=eq.{user_id}&order=created_at.desc&limit={limit}&offset={offset}&select=*"
        )
        headers = self._headers(auth_token)
        headers["Prefer"] = "count=exact"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=headers)
            if res.status_code != 200:
                logger.error("Supabase list_workouts failed: HTTP %s", res.status_code)
                raise StorageError("Failed to retrieve workout sessions")
            data = res.json()
            cr = res.headers.get("content-range", "")
            total_count = len(data)
            if "/" in cr:
                try:
                    total_count = int(cr.split("/")[-1])
                except ValueError:
                    pass
            records = [PersistedWorkoutSession(**item) for item in data]
            return records, total_count

    async def get_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> PersistedWorkoutSession | None:
        endpoint = f"{self.url}/rest/v1/workout_sessions?id=eq.{workout_id}&user_id=eq.{user_id}&select=*"
        async with httpx.AsyncClient() as client:
            res = await client.get(endpoint, headers=self._headers(auth_token))
            if res.status_code != 200:
                logger.error("Supabase get_workout failed: HTTP %s", res.status_code)
                raise StorageError("Failed to retrieve workout session")
            data = res.json()
            if not data:
                return None
            return PersistedWorkoutSession(**data[0])

    async def delete_workout(
        self,
        user_id: str,
        workout_id: str,
        auth_token: str | None = None,
    ) -> bool:
        endpoint = f"{self.url}/rest/v1/workout_sessions?id=eq.{workout_id}&user_id=eq.{user_id}"
        async with httpx.AsyncClient() as client:
            res = await client.delete(endpoint, headers=self._headers(auth_token))
            if res.status_code not in (200, 204):
                logger.error("Supabase delete_workout failed: HTTP %s", res.status_code)
                raise StorageError("Failed to delete workout session")
            data = res.json() if res.status_code == 200 else []
            return len(data) > 0 or res.status_code == 204


def create_storage(storage_backend: str | None = None) -> WorkoutStorage:
    """Factory creating the active persistence backend based on environment configuration.
    
    Guarantees:
    - Never silently falls back to in-memory persistence when 'supabase' is requested.
    - Explicitly validates backend mode; rejects unrecognized storage backends.
    - If PERFORMX_ENV=production, refuses 'memory' storage backend to prevent accidental ephemeral data loss.
    """
    backend = (storage_backend or os.getenv("PERFORMX_STORAGE_BACKEND", "memory")).lower().strip()
    env = os.getenv("PERFORMX_ENV", "development").lower().strip()

    if backend == "supabase":
        return SupabaseWorkoutStorage()
    elif backend == "memory":
        if env == "production":
            raise StorageError(
                "PERFORMX_STORAGE_BACKEND='memory' is strictly forbidden when PERFORMX_ENV='production'. "
                "Configure PERFORMX_STORAGE_BACKEND='supabase' with SUPABASE_URL and SUPABASE_KEY."
            )
        return InMemoryWorkoutStorage()
    else:
        raise StorageError(
            f"Unrecognized PERFORMX_STORAGE_BACKEND '{backend}'. Must be either 'supabase' or 'memory'."
        )

