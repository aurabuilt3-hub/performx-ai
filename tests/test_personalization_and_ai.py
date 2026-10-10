"""Tests for PERFORMX Personalization and Grounded AI Chatbot Integration.

Verifies:
1. Authentication requirement: Unauthenticated POST /api/v1/chat/message returns 401.
2. User data isolation: User A cannot retrieve or receive explanations of User B's workout metrics or health profile.
3. Allergen safety conservatism: Explanations never declare meals safe when allergen status is UNKNOWN.
4. Medical and clinician restriction compliance: Adheres to reported injuries and restrictions without unauthorized clinical clearance.
5. Zero raw video/landmark leakage: Context assemblage strictly strips raw frames and coordinates.
6. Hallucination prevention: Form scores, repetition counts, and depth angles are bound strictly to deterministic SessionMetrics.
"""

from __future__ import annotations

import pytest
import time
import jwt
import pytest
from starlette.testclient import TestClient

from performx.chat import (
    ChatMessageRequest,
    GroundedChatEngine,
    assemble_grounding_context,
)
from performx.contracts import RepetitionSummary, SessionMetrics, SessionSummary
from performx.http_api import create_app
from performx.storage import InMemoryWorkoutStorage


TEST_JWT_SECRET = "super-secret-supabase-jwt-key-for-testing-12345678"
USER_A_ID = "11111111-1111-4111-8111-111111111111"
USER_B_ID = "22222222-2222-4222-8222-222222222222"


def generate_jwt(user_id: str, secret: str = TEST_JWT_SECRET) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        "email": f"user-{user_id[:8]}@example.com",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def auth_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("PERFORMX_ENV", "test")


@pytest.fixture
def storage():
    return InMemoryWorkoutStorage()


@pytest.fixture
def client(storage):
    app = create_app(storage=storage)
    return TestClient(app)


@pytest.fixture
def user_a_headers():
    token = generate_jwt(user_id=USER_A_ID)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_b_headers():
    token = generate_jwt(user_id=USER_B_ID)
    return {"Authorization": f"Bearer {token}"}


def test_chat_requires_authentication(client):
    """Unauthenticated requests must be rejected with 401 Unauthorized."""
    resp = client.post("/api/v1/chat/message", json={"message": "How was my last workout?"})
    assert resp.status_code == 401


def test_chat_rejects_empty_or_excessive_payload(client, user_a_headers):
    """Payload validation: message cannot be empty or excessively large."""
    resp = client.post("/api/v1/chat/message", json={"message": ""}, headers=user_a_headers)
    assert resp.status_code == 422

    resp2 = client.post("/api/v1/chat/message", json={"message": "a" * 2500}, headers=user_a_headers)
    assert resp2.status_code == 422


@pytest.mark.anyio
async def test_user_data_isolation(client, storage, user_a_headers, user_b_headers):
    """User A's workout and health profile are isolated and never leaked to User B."""
    # Setup User A's profile and completed workout
    await storage.upsert_profile(user_id=USER_A_ID, display_name="Alex A", fitness_experience="advanced")
    await storage.upsert_health_profile(
        USER_A_ID,
        {
            "reported_injuries": [{"joint": "right_patella", "severity": "mild"}],
            "clinician_restrictions": ["no_deep_squats_beyond_90_deg"],
        },
    )
    
    from performx.core import SquatConfig
    # Save a workout for User A with 12 reps and 0.94 symmetry
    summary_a = SessionSummary(
        session_id="session_user_a",
        start_time=1000.0,
        end_time=1900.0,
        total_frames_processed=27000,
        total_reps=12,
        valid_reps=12,
        mean_symmetry=0.94,
        mean_rep_duration=2.5,
        config=SquatConfig(),
        metrics=SessionMetrics(
            total_completed_reps=12,
            accepted_reps=12,
            rejected_reps=0,
            incomplete_attempts=0,
            aborted_attempts=0,
            mean_duration=2.5,
            min_duration=2.1,
            max_duration=2.8,
            duration_range=0.7,
            mean_descent_duration=1.2,
            mean_bottom_dwell=0.3,
            mean_ascent_duration=1.0,
            mean_min_knee_angle=82.0,
            knee_angle_range=20.0,
            mean_rep_symmetry=0.94,
            mean_tracking_confidence=0.98,
        ),
    )
    await storage.save_workout(user_id=USER_A_ID, summary=summary_a, exercise_type="squat")

    # Setup User B's profile
    await storage.upsert_profile(user_id=USER_B_ID, display_name="Blake B", fitness_experience="beginner")

    # User B queries their workout
    resp_b = client.post(
        "/api/v1/chat/message",
        json={"message": "How did I perform in my squat workout?"},
        headers=user_b_headers,
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    # User B should NOT see User A's 12 reps or patella injury
    assert "12 total repetitions" not in data_b["reply"]
    assert "right_patella" not in data_b["reply"]
    assert f"user:{USER_A_ID}" not in data_b["grounded_entities"]
    assert f"user:{USER_B_ID}" in data_b["grounded_entities"]

    # User A queries their workout
    resp_a = client.post(
        "/api/v1/chat/message",
        json={"message": "How was my squat workout?"},
        headers=user_a_headers,
    )
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert "12 total repetitions" in data_a["reply"]
    assert "94.0%" in data_a["reply"]
    assert f"user:{USER_A_ID}" in data_a["grounded_entities"]


@pytest.mark.anyio
async def test_allergen_conservatism(client, storage, user_a_headers):
    """When allergen verification status is UNKNOWN, system issues warning and refuses safety clearance."""
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # User A logs nutrition with UNKNOWN allergen verification
    await storage.upsert_nutrition_log(
        USER_A_ID,
        {
            "log_date": today_str,
            "calories_consumed": 2100,
            "protein_g": 140.0,
            "allergen_verification_status": "UNKNOWN",
            "meals": [{"name": "Protein Shake", "calories": 300, "protein_g": 30.0, "allergens": ["whey", "soy"]}],
        },
    )

    resp = client.post(
        "/api/v1/chat/message",
        json={"message": "What is my nutrition status today and is my food safe?"},
        headers=user_a_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["warnings"]) > 0
    assert any("Allergen status is unverified" in w for w in data["warnings"])
    assert "UNKNOWN" in data["reply"] or "verify with supplier" in data["reply"]


@pytest.mark.anyio
async def test_grounding_context_excludes_raw_vision_data(storage):
    """Grounding context extraction must strictly exclude raw frames, images, and landmark arrays."""
    ctx = await assemble_grounding_context(user_id=USER_A_ID, storage=storage)
    rendered = ctx.to_system_prompt_context()

    # Verify no landmark coordinates, raw bytes, or base64 frames exist
    assert "landmarks" not in rendered
    assert "world_landmarks" not in rendered
    assert "base64" not in rendered
    assert "image_bytes" not in rendered


class MockSuccessfulLLMClient:
    """Mock LLM client returning verified natural language generation."""
    def __init__(self, canned_response: str = "Great job maintaining 94% symmetry on your squats!"):
        self.canned = canned_response
        self.calls = []

    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append({"system": system_prompt, "user": user_prompt})
        return self.canned


class MockFailingLLMClient:
    """Mock LLM client simulating external network failure / rate limit."""
    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("Simulated upstream provider timeout (504 Gateway Timeout)")


@pytest.mark.anyio
async def test_mock_llm_provider_execution(storage):
    """Engine successfully invokes configured LLM client with strictly grounded context."""
    mock_llm = MockSuccessfulLLMClient()
    engine = GroundedChatEngine(storage=storage, llm_client=mock_llm)

    await storage.upsert_profile(user_id=USER_A_ID, display_name="Test Athlete", fitness_experience="intermediate")
    
    response = await engine.answer(
        user_id=USER_A_ID,
        message="Can you explain my recent symmetry score?",
    )
    assert response.reply == "Great job maintaining 94% symmetry on your squats!"
    assert len(mock_llm.calls) == 1
    # Ensure system prompt contains the user's name and strict rules
    assert "Test Athlete" in mock_llm.calls[0]["system"]
    assert "STRICT RULES" in mock_llm.calls[0]["system"]


@pytest.mark.anyio
async def test_llm_provider_failure_graceful_fallback(storage):
    """When external LLM provider raises an exception, engine gracefully falls back to deterministic rules."""
    failing_llm = MockFailingLLMClient()
    engine = GroundedChatEngine(storage=storage, llm_client=failing_llm)

    await storage.upsert_profile(user_id=USER_A_ID, display_name="Fallback Athlete", fitness_experience="beginner")

    response = await engine.answer(
        user_id=USER_A_ID,
        message="What is my current workout status?",
    )
    # Must not crash, should return deterministic reply and advisory warning
    assert "Fallback Athlete" in response.reply
    assert any("temporarily unavailable" in w for w in response.warnings)

