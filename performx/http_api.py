"""PERFORMX Production HTTP REST API.

Provides a clean, typed, high-performance FastAPI interface for frontend clients:
- Direct landmark ingestion for browser-side MediaPipe (privacy-preserving, zero video upload)
- Server-side frame processing fallback (RAM-only, zero disk storage, 5MB limit)
- Session lifecycle management (create, status, summary, reset, delete)
- Standing-pose calibration endpoints
- Supabase Authentication & Profile Management
- Validated Workout Session Persistence (strict RLS & user isolation)
- Configurable CORS and structured error handling
"""

from contextlib import asynccontextmanager
from dataclasses import asdict
import math
import os
import time
from typing import Any
import uuid

import cv2
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from performx.api import BackendService
from performx.auth import AuthenticatedUser, get_current_user, get_optional_user
from performx.core import (
    ErrorCode,
    InvalidInputError,
    LandmarkIndex,
    LandmarkValidationError,
    PerformxError,
    SquatConfig,
)
from performx.contracts import (
    PoseLandmarksData,
    SessionMetrics,
    SessionSummary,
)
from performx.services import MovementAnalysisSession
from performx.storage import (
    StorageConflictError,
    StorageError,
    WorkoutStorage,
    create_storage,
)


MAX_FRAME_SIZE_BYTES = 5 * 1024 * 1024  # Strict 5 MB frame limit
HTTP_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


# ==========================================
# Pydantic Request & Response Models
# ==========================================


class SquatConfigRequest(BaseModel):
    """Optional biomechanical parameter overrides for a squat analysis session."""
    model_config = ConfigDict(extra="forbid")

    standing_knee_angle: float | None = Field(default=None, gt=0.0, le=180.0)
    descent_trigger_angle: float | None = Field(default=None, gt=0.0, le=180.0)
    bottom_target_angle: float | None = Field(default=None, gt=0.0, le=180.0)
    deep_squat_angle: float | None = Field(default=None, gt=0.0, le=180.0)
    min_bottom_dwell: float | None = Field(default=None, ge=0.0)
    max_bottom_dwell: float | None = Field(default=None, ge=0.0)
    min_rep_duration: float | None = Field(default=None, ge=0.0)
    max_torso_lean_deg: float | None = Field(default=None, ge=0.0)
    min_symmetry_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_visibility_conf: float | None = Field(default=None, ge=0.0, le=1.0)


class CreateSessionRequest(BaseModel):
    """Session creation request payload."""
    model_config = ConfigDict(extra="forbid")

    config: SquatConfigRequest | None = None


class LandmarkItem(BaseModel):
    """Normalized pose landmark coordinate from client-side vision."""
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


class AnalyzeLandmarksRequest(BaseModel):
    """Client-side landmark payload for privacy-preserving movement analysis."""
    model_config = ConfigDict(extra="forbid")

    timestamp: float = Field(ge=0.0)
    landmarks: list[LandmarkItem] | None = None
    world_landmarks: list[LandmarkItem] | None = None


from pydantic import BaseModel, ConfigDict, Field, field_validator


class UpdateProfileRequest(BaseModel):
    """User profile modification payload."""
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=100)
    units: str | None = Field(default="metric", pattern="^(metric|imperial)$")
    fitness_experience: str | None = Field(default="intermediate", pattern="^(beginner|intermediate|advanced|elite)$")
    primary_goal: str | None = Field(default="general_fitness", max_length=100)
    secondary_goal: str | None = Field(default=None, max_length=100)
    available_equipment: list[str] | None = Field(default=None, max_length=30)
    preferred_training_days: list[int] | None = Field(default=None, max_length=7)
    preferred_session_duration: int | None = Field(default=45, ge=5, le=180)
    dietary_preferences: list[str] | None = Field(default=None, max_length=30)


class UpdateHealthProfileRequest(BaseModel):
    """User health profile, injuries, and clinician restrictions payload."""
    model_config = ConfigDict(extra="forbid")

    height_cm: float | None = Field(default=None, ge=50.0, le=300.0)
    weight_kg: float | None = Field(default=None, ge=20.0, le=500.0)
    body_fat_percentage: float | None = Field(default=None, ge=2.0, le=70.0)
    resting_heart_rate: int | None = Field(default=None, ge=30, le=220)
    reported_injuries: list[dict[str, Any]] | None = Field(default_factory=list, max_length=20)
    reported_symptoms: list[str] | None = Field(default_factory=list, max_length=30)
    clinician_restrictions: list[str] | None = Field(default_factory=list, max_length=30)
    clinician_approved_plan: str | None = Field(default=None, max_length=500)
    allergies: list[str] | None = Field(default_factory=list, max_length=30)
    dietary_restrictions: list[str] | None = Field(default_factory=list, max_length=30)
    medications: list[str] | None = Field(default_factory=list, max_length=30)
    data_provenance: str = Field(default="USER_REPORTED", max_length=50)


class ExerciseItem(BaseModel):
    """Exercise prescription item."""
    model_config = ConfigDict(extra="forbid")

    exercise_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    target_sets: int = Field(ge=1, le=20)
    target_reps: int = Field(ge=1, le=100)
    target_load_kg: float | None = Field(default=None, ge=0.0)
    rest_seconds: int = Field(default=60, ge=0, le=600)
    scheduled_day: int | None = Field(default=None, ge=1, le=7)
    notes: str | None = Field(default="", max_length=300)


class WorkoutPlanRequest(BaseModel):
    """Workout plan creation and modification payload."""
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=500)
    is_active: bool = True
    version: int = Field(default=1, ge=1)
    exercises: list[ExerciseItem] = Field(default_factory=list, max_length=50)
    equipment_constraints: list[str] = Field(default_factory=list, max_length=20)
    target_experience: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced|elite)$")


class CreateRecommendationRequest(BaseModel):
    """Adaptive coaching recommendation creation payload."""
    model_config = ConfigDict(extra="forbid")

    recommendation_type: str = Field(min_length=1, max_length=64)
    rationale: str = Field(min_length=1, max_length=1000)
    status: str = Field(default="proposed", pattern="^(proposed|accepted|edited|dismissed|applied)$")
    source_session_id: str | None = Field(default=None, max_length=128)
    applied_changes: dict[str, Any] = Field(default_factory=dict)


class UpdateRecommendationStatusRequest(BaseModel):
    """Recommendation decision update."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern="^(accepted|edited|dismissed|applied)$")


class RecoveryCheckinRequest(BaseModel):
    """Injury symptom and recovery check-in payload."""
    model_config = ConfigDict(extra="forbid")

    affected_area: str = Field(min_length=1, max_length=100)
    discomfort_score: int = Field(ge=0, le=10)
    symptoms: str = Field(default="", max_length=500)
    exercise_adherence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=500)


class MealItem(BaseModel):
    """Meal log item."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    calories: int = Field(ge=0)
    protein_g: float = Field(default=0.0, ge=0.0)
    carbs_g: float = Field(default=0.0, ge=0.0)
    fat_g: float = Field(default=0.0, ge=0.0)
    ingredients: list[str] = Field(default_factory=list, max_length=30)
    allergens: list[str] = Field(default_factory=list, max_length=20)


class NutritionLogRequest(BaseModel):
    """Daily nutrition and hydration payload."""
    model_config = ConfigDict(extra="forbid")

    log_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    calories_consumed: int = Field(default=0, ge=0, le=20000)
    protein_g: float = Field(default=0.0, ge=0.0, le=1000.0)
    carbs_g: float = Field(default=0.0, ge=0.0, le=2000.0)
    fat_g: float = Field(default=0.0, ge=0.0, le=1000.0)
    water_ml: int = Field(default=0, ge=0, le=20000)
    meals: list[MealItem] = Field(default_factory=list, max_length=20)
    allergen_verification_status: str = Field(
        default="UNKNOWN",
        pattern="^(VERIFIED_PRESENT|VERIFIED_ABSENT|UNKNOWN)$"
    )


class PresignUploadRequest(BaseModel):
    """Medical document presigned upload request."""
    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0, le=15 * 1024 * 1024)  # 15MB limit
    mime_type: str = Field(pattern="^(application/pdf|image/png|image/jpeg)$")
    document_category: str = Field(default="general", max_length=64)
    description: str = Field(default="", max_length=500)


class ConfirmDocumentUploadRequest(BaseModel):
    """Confirm completed document upload."""
    model_config = ConfigDict(extra="forbid")

    storage_path: str = Field(min_length=1, max_length=500)
    file_name: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0, le=15 * 1024 * 1024)
    mime_type: str = Field(pattern="^(application/pdf|image/png|image/jpeg)$")
    document_category: str = Field(default="general", max_length=64)
    description: str = Field(default="", max_length=500)


class UpdatePrivacyConsentRequest(BaseModel):
    """User privacy preferences and explicit feature consents."""
    model_config = ConfigDict(extra="forbid")

    camera_processing_consent: bool = False
    document_processing_consent: bool = False
    data_analytics_consent: bool = False


class SummaryMetricsInput(BaseModel):
    """Validated scalar metrics payload matching SessionMetrics contract."""
    model_config = ConfigDict(extra="forbid")

    total_completed_reps: int = Field(ge=0)
    accepted_reps: int = Field(ge=0)
    rejected_reps: int = Field(ge=0)
    incomplete_attempts: int = Field(default=0, ge=0)
    aborted_attempts: int = Field(default=0, ge=0)
    mean_duration: float | None = Field(default=None, ge=0.0)
    min_duration: float | None = Field(default=None, ge=0.0)
    max_duration: float | None = Field(default=None, ge=0.0)
    duration_range: float | None = Field(default=None, ge=0.0)
    mean_descent_duration: float | None = Field(default=None, ge=0.0)
    mean_bottom_dwell: float | None = Field(default=None, ge=0.0)
    mean_ascent_duration: float | None = Field(default=None, ge=0.0)
    mean_min_knee_angle: float | None = Field(default=None, ge=0.0, le=180.0)
    knee_angle_range: float | None = Field(default=None, ge=0.0, le=180.0)
    mean_rep_symmetry: float | None = Field(default=None, ge=0.0, le=1.0)
    mean_tracking_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    explainable_insights: list[str] = Field(default_factory=list, max_length=50)

    @field_validator(
        "mean_duration", "min_duration", "max_duration", "duration_range",
        "mean_descent_duration", "mean_bottom_dwell", "mean_ascent_duration",
        "mean_min_knee_angle", "knee_angle_range", "mean_rep_symmetry",
        "mean_tracking_confidence"
    )
    @classmethod
    def validate_finite(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            raise ValueError("Value must be a finite number")
        return v


class SaveWorkoutSummaryPayload(BaseModel):
    """Validated direct summary payload for persistence."""
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=128)
    start_time: float = Field(ge=0.0)
    end_time: float = Field(ge=0.0)
    total_frames_processed: int = Field(ge=0)
    total_reps: int = Field(ge=0)
    valid_reps: int = Field(ge=0)
    mean_symmetry: float = Field(ge=0.0, le=1.0)
    mean_rep_duration: float = Field(ge=0.0)
    metrics: SummaryMetricsInput | None = None


    @field_validator("start_time", "end_time", "mean_symmetry", "mean_rep_duration")
    @classmethod
    def validate_finite_time(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Value must be a finite number")
        return v


class SaveWorkoutRequest(BaseModel):
    """Workout summary persistence payload."""
    model_config = ConfigDict(extra="forbid")

    session_id: str | None = None
    summary: SaveWorkoutSummaryPayload | None = None
    exercise_type: str = Field(default="squat", max_length=50)


# ==========================================
# Helpers
# ==========================================

def _convert_landmarks_payload(req: AnalyzeLandmarksRequest) -> PoseLandmarksData | None:
    """Validate and convert landmark request to PoseLandmarksData contract."""
    if req.landmarks is None or len(req.landmarks) == 0:
        return None

    if len(req.landmarks) != 33:
        raise HTTPException(
            status_code=HTTP_422,
            detail=f"landmarks must contain exactly 33 landmarks, got {len(req.landmarks)}",
        )

    coords = np.zeros((33, 4), dtype=np.float32)
    for idx, lm in enumerate(req.landmarks):
        if not (math.isfinite(lm.x) and math.isfinite(lm.y) and math.isfinite(lm.z) and math.isfinite(lm.visibility)):
            raise HTTPException(
                status_code=HTTP_422,
                detail=f"Non-finite coordinate encountered at landmark index {idx}",
            )
        coords[idx] = [lm.x, lm.y, lm.z, lm.visibility]

    world_coords = None
    if req.world_landmarks is not None:
        if len(req.world_landmarks) != 33:
            raise HTTPException(
                status_code=HTTP_422,
                detail=f"world_landmarks must contain exactly 33 landmarks, got {len(req.world_landmarks)}",
            )
        world_coords = np.zeros((33, 3), dtype=np.float32)
        for idx, wlm in enumerate(req.world_landmarks):
            if not (math.isfinite(wlm.x) and math.isfinite(wlm.y) and math.isfinite(wlm.z)):
                raise HTTPException(
                    status_code=HTTP_422,
                    detail=f"Non-finite world coordinate encountered at landmark index {idx}",
                )
            world_coords[idx] = [wlm.x, wlm.y, wlm.z]

    key_joints = [
        LandmarkIndex.LEFT_HIP, LandmarkIndex.RIGHT_HIP,
        LandmarkIndex.LEFT_KNEE, LandmarkIndex.RIGHT_KNEE,
        LandmarkIndex.LEFT_ANKLE, LandmarkIndex.RIGHT_ANKLE,
    ]
    mean_conf = float(np.mean(coords[key_joints, 3]))

    return PoseLandmarksData(
        coords=coords,
        world_coords=world_coords,
        mean_confidence=mean_conf,
        timestamp=req.timestamp,
    )


def _check_session_access(session: MovementAnalysisSession, current_user: AuthenticatedUser | None):
    """Enforce ownership on active in-memory analysis sessions."""
    if session.user_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required to access this user-bound session",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if session.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: this session is owned by another user",
            )


# ==========================================
# Application Factory
# ==========================================

def create_app(
    backend_service: BackendService | None = None,
    storage: WorkoutStorage | None = None,
) -> FastAPI:
    """Create and configure the FastAPI PERFORMX application."""
    service = backend_service if backend_service is not None else BackendService()
    storage_backend = storage if storage is not None else create_storage()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup phase
        yield
        # Shutdown phase: Clean up in-memory sessions and release MediaPipe vision resources
        service.close()

    app = FastAPI(
        title="PERFORMX Movement Analysis API",
        version="1.0.0",
        description=(
            "Privacy-preserving human movement analysis API inspired by fruit-fly sensorimotor intelligence. "
            "Processes in-memory kinematic landmarks or raw frames with zero disk persistence. "
            "Integrates Supabase authentication and user session persistence."
        ),
        lifespan=lifespan,
    )


    # CORS configuration
    cors_env = os.getenv("PERFORMX_CORS_ORIGINS", "")
    if cors_env.strip():
        allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]
    else:
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    # Prevent invalid Starlette combination: allow_origins=['*'] with allow_credentials=True
    has_wildcard = "*" in allowed_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=not has_wildcard,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Exception Handlers
    @app.exception_handler(PerformxError)
    async def handle_performx_error(_request: Request, exc: PerformxError):
        if exc.code == ErrorCode.SESSION_INACTIVE:
            status_code = status.HTTP_404_NOT_FOUND
        elif exc.code == ErrorCode.SESSION_LIMIT_EXCEEDED:
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        return JSONResponse(
            status_code=status_code,
            content={
                "code": exc.code.value,
                "message": exc.message,
                "timestamp": time.time(),
                "details": {},
            },
        )

    @app.exception_handler(LandmarkValidationError)
    async def handle_landmark_validation(_request: Request, exc: LandmarkValidationError):
        return JSONResponse(
            status_code=HTTP_422,
            content={
                "code": "INVALID_LANDMARK_DATA",
                "message": str(exc),
                "timestamp": time.time(),
                "details": {},
            },
        )

    @app.exception_handler(InvalidInputError)
    async def handle_invalid_input(_request: Request, exc: InvalidInputError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "code": "INVALID_INPUT",
                "message": str(exc),
                "timestamp": time.time(),
                "details": {},
            },
        )

    @app.exception_handler(StorageConflictError)
    async def handle_storage_conflict(_request: Request, exc: StorageConflictError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": "CONFLICT",
                "message": str(exc),
                "timestamp": time.time(),
                "details": {},
            },
        )

    @app.exception_handler(StorageError)
    async def handle_storage_error(_request: Request, exc: StorageError):
        # Prevent disclosure of database schemas or internal PostgREST details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "STORAGE_ERROR",
                "message": "Database storage operation failed. Please try again later.",
                "timestamp": time.time(),
                "details": {},
            },
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(_request: Request, exc: Exception):
        # Sanitize all unexpected errors to prevent stack trace leaks
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "timestamp": time.time(),
                "details": {},
            },
        )

    # ----------------------------------------------------
    # System Status & Capabilities
    # ----------------------------------------------------

    @app.get("/", tags=["System"])
    async def root():
        """Root health ping for PaaS load balancers."""
        return {"status": "healthy", "service": "PERFORMX Movement Analysis API", "version": "1.0.0"}

    @app.get("/health", tags=["System"])
    @app.get("/healthz", tags=["System"])
    async def get_health():
        """Retrieve operational health, active sessions count, and privacy guarantees."""
        return service.get_health()

    @app.get("/api/v1/capabilities", tags=["Capabilities"])

    async def get_capabilities():
        """Retrieve supported biomechanical features, exercises, and envelope limits."""
        return service.get_capabilities()

    # ----------------------------------------------------
    # User Profiles (Supabase Auth Required)
    # ----------------------------------------------------

    @app.get("/api/v1/me/profile", tags=["User Profiles"])
    @app.get("/api/v1/profile", tags=["User Profiles"])
    async def get_my_profile(user: AuthenticatedUser = Depends(get_current_user)):
        """Retrieve the authenticated user's profile and fitness preferences."""
        profile = await storage_backend.get_profile(user.user_id, auth_token=user.token)
        if profile is None:
            profile = await storage_backend.upsert_profile(user.user_id, "", auth_token=user.token)
        return profile.to_dict()

    @app.put("/api/v1/me/profile", tags=["User Profiles"])
    @app.put("/api/v1/profile", tags=["User Profiles"])
    @app.patch("/api/v1/profile", tags=["User Profiles"])
    async def update_my_profile(
        req: UpdateProfileRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Create or update the authenticated user's profile and preferences."""
        profile = await storage_backend.upsert_profile(
            user_id=user.user_id,
            display_name=req.display_name,
            units=req.units or "metric",
            fitness_experience=req.fitness_experience or "intermediate",
            primary_goal=req.primary_goal or "general_fitness",
            secondary_goal=req.secondary_goal,
            available_equipment=req.available_equipment,
            preferred_training_days=req.preferred_training_days,
            preferred_session_duration=req.preferred_session_duration or 45,
            dietary_preferences=req.dietary_preferences,
            auth_token=user.token,
        )
        return profile.to_dict()


    # ----------------------------------------------------
    # Session Lifecycle Management
    # ----------------------------------------------------

    @app.post("/api/v1/sessions", status_code=status.HTTP_201_CREATED, tags=["Sessions"])
    async def create_session(
        req: CreateSessionRequest | None = None,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Create a new isolated movement analysis session (optionally bound to authenticated user)."""
        config = SquatConfig()
        if req and req.config:
            cfg_dict = req.config.model_dump(exclude_none=True)
            try:
                config = SquatConfig(**cfg_dict)
            except ValueError as err:
                raise HTTPException(
                    status_code=HTTP_422,
                    detail=f"Invalid squat configuration: {err}",
                )

        bound_user_id = optional_user.user_id if optional_user else None
        session_id = service.create_session(config=config, user_id=bound_user_id)
        return {
            "session_id": session_id,
            "status": "active",
            "user_id": bound_user_id,
            "config": asdict(config),
        }

    @app.get("/api/v1/sessions/{session_id}", tags=["Sessions"])
    async def get_session_status(
        session_id: str,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Retrieve current runtime status and frame counters for an active session."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)

        return {
            "session_id": session.session_id,
            "is_active": session.is_active,
            "frames_processed": session.frames_processed,
            "total_reps": session.engine.repetition_count,
            "valid_reps": session.engine.valid_reps,
            "current_phase": session.engine.current_phase.value,
        }

    @app.get("/api/v1/sessions/{session_id}/summary", tags=["Sessions"])
    async def get_session_summary(
        session_id: str,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Retrieve aggregated biomechanical summary and metrics without terminating the session."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        summary = session.get_summary()
        return summary.to_dict()

    @app.post("/api/v1/sessions/{session_id}/reset", tags=["Sessions"])
    async def reset_session(
        session_id: str,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Reset movement counters, filters, and calibration within an active session."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        service.reset_session(session_id)
        return {"status": "session_reset", "session_id": session_id}

    @app.delete("/api/v1/sessions/{session_id}", tags=["Sessions"])
    async def terminate_session(
        session_id: str,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Terminate an active session and retrieve its final performance summary."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        summary = service.end_session(session_id)
        return summary.to_dict()

    # ----------------------------------------------------
    # Movement Analysis Endpoints
    # ----------------------------------------------------

    @app.post("/api/v1/sessions/{session_id}/analysis/landmarks", tags=["Analysis"])
    @app.post("/api/v1/sessions/{session_id}/landmarks", tags=["Analysis"])
    async def analyze_landmarks(
        session_id: str,
        payload: AnalyzeLandmarksRequest,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Analyze pre-extracted MediaPipe landmarks directly (privacy-first browser mode)."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        lm_data = _convert_landmarks_payload(payload)
        res = service.process_landmarks(session_id, lm_data, timestamp=payload.timestamp)
        return res.to_dict()

    @app.post("/api/v1/sessions/{session_id}/analysis/frame", tags=["Analysis"])
    async def analyze_frame(
        session_id: str,
        file: UploadFile = File(...),
        timestamp: float = Form(...),
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Analyze raw image frame fallback via server-side MediaPipe.
        
        Frame is held strictly in RAM, processed, and dereferenced. Never written to disk.
        """
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)

        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_FRAME_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Frame exceeds maximum permitted size of {MAX_FRAME_SIZE_BYTES // (1024 * 1024)} MB",
            )

        nparr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid or decodable image",
            )

        rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            res = service.process_frame(session_id, rgb_frame, timestamp=timestamp)
            return res.to_dict()
        finally:
            del raw_bytes
            del nparr
            del img
            del rgb_frame

    # ----------------------------------------------------
    # Calibration Endpoints
    # ----------------------------------------------------

    @app.post("/api/v1/sessions/{session_id}/calibration/landmarks", tags=["Calibration"])
    async def calibrate_landmarks(
        session_id: str,
        payload: AnalyzeLandmarksRequest,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Submit a standing calibration sample using pre-extracted landmarks."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        lm_data = _convert_landmarks_payload(payload)
        calib_res = service.calibrate_landmarks(session_id, lm_data)
        return calib_res.to_dict()

    @app.post("/api/v1/sessions/{session_id}/calibration/frame", tags=["Calibration"])
    async def calibrate_frame(
        session_id: str,
        file: UploadFile = File(...),
        timestamp: float = Form(...),
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Submit a standing calibration sample using an uploaded image frame."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)

        raw_bytes = await file.read()
        if len(raw_bytes) > MAX_FRAME_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Frame exceeds maximum permitted size of {MAX_FRAME_SIZE_BYTES // (1024 * 1024)} MB",
            )

        nparr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid or decodable image",
            )

        rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            calib_res = service.calibrate_frame(session_id, rgb_frame, timestamp=timestamp)
            return calib_res.to_dict()
        finally:
            del raw_bytes
            del nparr
            del img
            del rgb_frame

    @app.post("/api/v1/sessions/{session_id}/calibration/reset", tags=["Calibration"])
    async def reset_calibration(
        session_id: str,
        optional_user: AuthenticatedUser | None = Depends(get_optional_user),
    ):
        """Reset standing pose calibration within an active session."""
        session = service.get_session(session_id)
        if session is None or not session.is_active:
            raise PerformxError(ErrorCode.SESSION_INACTIVE, f"Session '{session_id}' not found or inactive")

        _check_session_access(session, optional_user)
        service.reset_calibration(session_id)
        return {"status": "calibration_reset", "session_id": session_id}

    # ----------------------------------------------------
    # Workout Persistence (Supabase Auth Required)
    # ----------------------------------------------------

    @app.post("/api/v1/workouts", status_code=status.HTTP_201_CREATED, tags=["Workouts"])
    async def save_workout(
        req: SaveWorkoutRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Persist a completed workout summary to the user's permanent history with RLS enforcement."""
        if req.session_id:
            # Look up active in-memory session
            session = service.get_session(req.session_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Active session '{req.session_id}' not found",
                )
            _check_session_access(session, user)
            summary = session.get_summary()
        elif req.summary:
            # Reconstruct validated SessionSummary contract
            m = req.summary.metrics
            metrics = None
            if m:
                metrics = SessionMetrics(
                    total_completed_reps=m.total_completed_reps,
                    accepted_reps=m.accepted_reps,
                    rejected_reps=m.rejected_reps,
                    incomplete_attempts=m.incomplete_attempts,
                    aborted_attempts=m.aborted_attempts,
                    mean_duration=m.mean_duration,
                    min_duration=m.min_duration,
                    max_duration=m.max_duration,
                    duration_range=m.duration_range,
                    mean_descent_duration=m.mean_descent_duration,
                    mean_bottom_dwell=m.mean_bottom_dwell,
                    mean_ascent_duration=m.mean_ascent_duration,
                    mean_min_knee_angle=m.mean_min_knee_angle,
                    knee_angle_range=m.knee_angle_range,
                    mean_rep_symmetry=m.mean_rep_symmetry,
                    mean_tracking_confidence=m.mean_tracking_confidence,
                    explainable_insights=m.explainable_insights,
                )
            summary = SessionSummary(
                session_id=req.summary.session_id,
                start_time=req.summary.start_time,
                end_time=req.summary.end_time,
                total_frames_processed=req.summary.total_frames_processed,
                total_reps=req.summary.total_reps,
                valid_reps=req.summary.valid_reps,
                mean_symmetry=req.summary.mean_symmetry,
                mean_rep_duration=req.summary.mean_rep_duration,
                config=SquatConfig(),
                metrics=metrics,
            )
        else:
            raise HTTPException(
                status_code=HTTP_422,
                detail="Request must provide either 'session_id' or 'summary'",
            )

        persisted = await storage_backend.save_workout(
            user_id=user.user_id,
            summary=summary,
            exercise_type=req.exercise_type,
            auth_token=user.token,
        )
        return persisted.to_dict()

    @app.get("/api/v1/workouts", tags=["Workouts"])
    async def list_workouts(
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """List the current user's saved workout summaries with pagination."""
        records, total_count = await storage_backend.list_workouts(
            user_id=user.user_id,
            limit=limit,
            offset=offset,
            auth_token=user.token,
        )
        return {
            "items": [r.to_dict() for r in records],
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/v1/workouts/{workout_id}", tags=["Workouts"])
    async def get_workout(
        workout_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Retrieve a specific saved workout session summary owned by the current user."""
        record = await storage_backend.get_workout(user_id=user.user_id, workout_id=workout_id, auth_token=user.token)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workout session '{workout_id}' not found",
            )
        return record.to_dict()

    @app.delete("/api/v1/workouts/{workout_id}", tags=["Workouts"])
    async def delete_workout(
        workout_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Delete a specific saved workout session summary owned by the current user."""
        success = await storage_backend.delete_workout(user_id=user.user_id, workout_id=workout_id, auth_token=user.token)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workout session '{workout_id}' not found",
            )
        return {"status": "deleted", "workout_id": workout_id}

    # ----------------------------------------------------
    # Health Profile & Medical Context
    # ----------------------------------------------------

    @app.get("/api/v1/health-profile", tags=["Health Profile"])
    async def get_health_profile(user: AuthenticatedUser = Depends(get_current_user)):
        """Retrieve the user-reported health profile, limitations, and clinician restrictions."""
        hp = await storage_backend.get_health_profile(user.user_id, auth_token=user.token)
        if hp is None:
            hp = await storage_backend.upsert_health_profile(user.user_id, {}, auth_token=user.token)
        return hp.to_dict()

    @app.put("/api/v1/health-profile", tags=["Health Profile"])
    @app.patch("/api/v1/health-profile", tags=["Health Profile"])
    async def update_health_profile(
        req: UpdateHealthProfileRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Update user-reported health profile and medical annotations."""
        hp = await storage_backend.upsert_health_profile(user.user_id, req.model_dump(exclude_none=True), auth_token=user.token)
        return hp.to_dict()

    # ----------------------------------------------------
    # Workout Plans & Personalization
    # ----------------------------------------------------

    @app.get("/api/v1/plans/active", tags=["Workout Plans"])
    @app.get("/api/v1/workout-plan", tags=["Workout Plans"])
    async def get_active_plan(user: AuthenticatedUser = Depends(get_current_user)):
        """Retrieve current active workout plan."""
        plan = await storage_backend.get_active_workout_plan(user.user_id, auth_token=user.token)
        if plan is None:
            # Default empty initial plan
            plan = await storage_backend.save_workout_plan(
                user.user_id,
                {"title": "Full Body Baseline", "description": "Adaptive beginner-friendly baseline plan", "exercises": []},
                auth_token=user.token,
            )
        return plan.to_dict()

    @app.post("/api/v1/plans", status_code=status.HTTP_201_CREATED, tags=["Workout Plans"])
    @app.put("/api/v1/plans", tags=["Workout Plans"])
    async def save_plan(
        req: WorkoutPlanRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Create or update a personalized workout plan."""
        plan = await storage_backend.save_workout_plan(user.user_id, req.model_dump(), auth_token=user.token)
        return plan.to_dict()

    # ----------------------------------------------------
    # Adaptive Coaching Recommendations
    # ----------------------------------------------------

    @app.get("/api/v1/recommendations", tags=["Coaching"])
    async def get_recommendations(user: AuthenticatedUser = Depends(get_current_user)):
        """List active and historical adaptive coaching recommendations."""
        recs = await storage_backend.list_recommendations(user.user_id, auth_token=user.token)
        return {"items": [r.to_dict() for r in recs], "total": len(recs)}

    @app.post("/api/v1/recommendations", status_code=status.HTTP_201_CREATED, tags=["Coaching"])
    async def create_recommendation(
        req: CreateRecommendationRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Create a new proposed adaptive recommendation."""
        rec = await storage_backend.create_recommendation(user.user_id, req.model_dump(), auth_token=user.token)
        return rec.to_dict()

    @app.patch("/api/v1/recommendations/{rec_id}", tags=["Coaching"])
    async def update_recommendation_status(
        rec_id: str,
        req: UpdateRecommendationStatusRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Record user decision on an adaptive recommendation (accepted, dismissed, applied)."""
        updated = await storage_backend.update_recommendation_status(user.user_id, rec_id, req.status, auth_token=user.token)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")
        return updated.to_dict()

    # ----------------------------------------------------
    # Recovery & Injury Check-ins
    # ----------------------------------------------------

    @app.get("/api/v1/recovery", tags=["Recovery"])
    async def get_recovery_history(user: AuthenticatedUser = Depends(get_current_user)):
        """Retrieve user recovery and symptom check-in history."""
        records = await storage_backend.list_recovery_checkins(user.user_id, auth_token=user.token)
        return {"items": [r.to_dict() for r in records], "total": len(records)}

    @app.post("/api/v1/recovery", status_code=status.HTTP_201_CREATED, tags=["Recovery"])
    async def log_recovery_checkin(
        req: RecoveryCheckinRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Log a new recovery check-in or symptom update."""
        rec = await storage_backend.log_recovery_checkin(user.user_id, req.model_dump(), auth_token=user.token)
        return rec.to_dict()

    # ----------------------------------------------------
    # Nutrition & Hydration
    # ----------------------------------------------------

    @app.get("/api/v1/nutrition/today", tags=["Nutrition"])
    @app.get("/api/v1/nutrition", tags=["Nutrition"])
    async def get_nutrition(
        date: str | None = None,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Retrieve nutrition and hydration log for today or a specific date."""
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        nlog = await storage_backend.get_nutrition_log(user.user_id, target_date, auth_token=user.token)
        if nlog is None:
            nlog = await storage_backend.upsert_nutrition_log(user.user_id, {"log_date": target_date}, auth_token=user.token)
        return nlog.to_dict()

    @app.post("/api/v1/nutrition/today", tags=["Nutrition"])
    @app.post("/api/v1/nutrition", tags=["Nutrition"])
    async def update_nutrition(
        req: NutritionLogRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Update daily nutrition and hydration log."""
        data = req.model_dump(exclude_none=True)
        if "meals" in data:
            data["meals"] = [m if isinstance(m, dict) else m.model_dump() for m in data["meals"]]
        nlog = await storage_backend.upsert_nutrition_log(user.user_id, data, auth_token=user.token)
        return nlog.to_dict()

    # ----------------------------------------------------
    # Medical Document Management
    # ----------------------------------------------------

    @app.post("/api/v1/documents/presign-upload", tags=["Medical Documents"])
    async def presign_document_upload(
        req: PresignUploadRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Authorize a secure medical document upload and return signed upload URL/path."""
        doc_id = str(uuid.uuid4())
        ext = req.file_name.rsplit(".", 1)[-1] if "." in req.file_name else "bin"
        storage_path = f"users/{user.user_id}/documents/{doc_id}.{ext}"

        # In production Supabase storage, signed upload URL can be generated.
        return {
            "document_id": doc_id,
            "storage_path": storage_path,
            "upload_url": f"/api/v1/documents/upload-content/{doc_id}",
            "expires_in_seconds": 3600,
            "file_size_limit_bytes": 15 * 1024 * 1024,
            "allowed_mime_types": ["application/pdf", "image/png", "image/jpeg"],
        }

    @app.post("/api/v1/documents/confirm", status_code=status.HTTP_201_CREATED, tags=["Medical Documents"])
    async def confirm_document_upload(
        req: ConfirmDocumentUploadRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Confirm uploaded medical document metadata in the private user catalog."""
        metadata = await storage_backend.save_medical_document(user.user_id, req.model_dump(), auth_token=user.token)
        return metadata.to_dict()

    @app.get("/api/v1/documents", tags=["Medical Documents"])
    async def list_documents(user: AuthenticatedUser = Depends(get_current_user)):
        """List active medical document metadata for the current user."""
        docs = await storage_backend.list_medical_documents(user.user_id, auth_token=user.token)
        return {"items": [d.to_dict() for d in docs], "total": len(docs)}

    @app.get("/api/v1/documents/{doc_id}", tags=["Medical Documents"])
    async def get_document(
        doc_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Retrieve a specific medical document record with authorized download path."""
        doc = await storage_backend.get_medical_document(user.user_id, doc_id, auth_token=user.token)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        data = doc.to_dict()
        data["download_url"] = f"/api/v1/documents/content/{doc.id}"
        return data

    @app.delete("/api/v1/documents/{doc_id}", tags=["Medical Documents"])
    async def delete_document(
        doc_id: str,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Permanently delete a medical document metadata record."""
        success = await storage_backend.delete_medical_document(user.user_id, doc_id, auth_token=user.token)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return {"status": "deleted", "document_id": doc_id}

    # ----------------------------------------------------
    # Consent & Privacy Preferences
    # ----------------------------------------------------

    @app.get("/api/v1/privacy/consent", tags=["Privacy"])
    async def get_privacy_consent(user: AuthenticatedUser = Depends(get_current_user)):
        """Retrieve user privacy preferences and processing consents."""
        pc = await storage_backend.get_privacy_consent(user.user_id, auth_token=user.token)
        if pc is None:
            pc = await storage_backend.update_privacy_consent(user.user_id, {}, auth_token=user.token)
        return pc.to_dict()

    @app.post("/api/v1/privacy/consent", tags=["Privacy"])
    async def update_privacy_consent(
        req: UpdatePrivacyConsentRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Update explicit user consents for camera and document processing."""
        pc = await storage_backend.update_privacy_consent(user.user_id, req.model_dump(), auth_token=user.token)
        return pc.to_dict()

    # ----------------------------------------------------
    # Data Export & Account Deletion
    # ----------------------------------------------------

    @app.post("/api/v1/account/data-export", tags=["Account"])
    async def export_data(user: AuthenticatedUser = Depends(get_current_user)):
        """Generate a complete machine-readable archive of all user data (GDPR/CCPA compliant)."""
        archive = await storage_backend.export_all_user_data(user.user_id, auth_token=user.token)
        return archive

    @app.delete("/api/v1/account", tags=["Account"])
    async def delete_account(user: AuthenticatedUser = Depends(get_current_user)):
        """Permanently delete all user profile, health, workout, and document data."""
        success = await storage_backend.delete_all_user_data(user.user_id, auth_token=user.token)
        return {"status": "account_purged", "user_id": user.user_id}

    # ----------------------------------------------------
    # Grounded AI Chat Assistant
    # ----------------------------------------------------

    from performx.chat import (
        ChatMessageRequest,
        ChatMessageResponse,
        GroundedChatEngine,
        create_llm_client_from_env,
    )

    llm_client = create_llm_client_from_env()
    chat_engine = GroundedChatEngine(storage=storage_backend, llm_client=llm_client)

    @app.post("/api/v1/chat/message", response_model=ChatMessageResponse, tags=["AI Assistant"])
    async def chat_with_assistant(
        req: ChatMessageRequest,
        user: AuthenticatedUser = Depends(get_current_user),
    ):
        """Send message to grounded PERFORMX assistant with strict user data isolation."""
        res = await chat_engine.answer(
            user_id=user.user_id,
            message=req.message,
            auth_token=user.token,
            session_id=req.session_id,
        )
        return res

    return app



# Default ASGI application instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    is_dev = os.getenv("PERFORMX_ENV", "development").lower().strip() == "development"

    uvicorn.run(
        "performx.http_api:app",
        host=host,
        port=port,
        reload=is_dev,
        log_level="info",
    )

