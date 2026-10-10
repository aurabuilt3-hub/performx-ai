"""PERFORMX Supabase Authentication & JWT Verification (Hardened).

Security & Privacy Guarantees:
- Cryptographic verification supporting both symmetric (HS256) and asymmetric (RS256/ES256) signing
- Strict prevention of JWT algorithm confusion attacks
- Rejection of unsigned tokens (alg="none")
- Audience, expiration, and optional issuer validation
- Derivation of authenticated user ID strictly from verified token claims (never request inputs)
- Sanitized error responses that never leak token contents, internal secrets, or stack traces
"""

from dataclasses import dataclass, field
import logging
import os
from typing import Any
import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

logger = logging.getLogger("performx.auth")

# Standard HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Strongly typed representation of an authenticated Supabase user."""
    user_id: str
    email: str | None = None
    role: str = "authenticated"
    token: str = ""
    claims: dict[str, Any] = field(default_factory=dict)


def verify_supabase_token(
    token: str,
    secret: str | None = None,
    public_key: str | None = None,
    expected_issuer: str | None = None,
    expected_audience: str = "authenticated",
) -> dict[str, Any]:
    """Cryptographically verify a Supabase-issued JWT and extract its validated claims.
    
    Security Controls:
    1. Algorithm Whitelisting:
       - If public key is provided: strictly restricts to asymmetric ["RS256", "ES256"]
       - If secret is provided: strictly restricts to symmetric ["HS256"]
       - Unsigned tokens (alg="none") are strictly rejected.
    2. Expiration Validation:
       - Requires 'exp' claim; rejects expired tokens with HTTP 401.
    3. Audience Validation:
       - Requires 'aud' claim matching expected audience (default: 'authenticated').
    4. Issuer Validation:
       - Validates 'iss' if SUPABASE_URL or expected_issuer is configured.
    5. Subject Validation:
       - Requires 'sub' claim to be a valid UUID.
    6. Information Disclosure Prevention:
       - Detailed error causes are logged internally; client responses receive safe, sanitized messages.
    """
    jwt_secret = secret or os.getenv("SUPABASE_JWT_SECRET")
    jwt_pubkey = public_key or os.getenv("SUPABASE_JWT_PUBLIC_KEY")

    if not jwt_secret and not jwt_pubkey:
        logger.error("Authentication failed: Neither SUPABASE_JWT_SECRET nor SUPABASE_JWT_PUBLIC_KEY is configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service configuration error",
        )

    # Determine verification key and strictly enforce allowed algorithms
    if jwt_pubkey:
        verify_key = jwt_pubkey
        allowed_algorithms = ["RS256", "ES256"]
    else:
        verify_key = jwt_secret
        allowed_algorithms = ["HS256"]

    # Determine expected issuer
    issuer = expected_issuer or os.getenv("SUPABASE_JWT_ISSUER")
    if not issuer:
        supa_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        if supa_url:
            issuer = f"{supa_url}/auth/v1"

    options = {
        "require": ["exp", "sub", "aud"],
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": True,
    }
    if issuer:
        options["verify_iss"] = True

    try:
        # Inspect unverified header to reject 'none' algorithm before parsing
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "").upper()
        if alg == "NONE" or alg not in allowed_algorithms:
            logger.warning("Rejected token with disallowed algorithm: %s", alg)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token algorithm",
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
            )

        payload = jwt.decode(
            token,
            verify_key,
            algorithms=allowed_algorithms,
            audience=expected_audience,
            issuer=issuer if issuer else None,
            options=options,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""},
        )
    except jwt.InvalidTokenError as err:
        logger.warning("Token verification failed: %s", type(err).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Unexpected error during token decoding: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    # Validate sub is a valid UUID
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token subject must be a valid UUID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser:
    """FastAPI dependency requiring a cryptographically verified Supabase access token."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_token = credentials.credentials
    claims = verify_supabase_token(raw_token)
    return AuthenticatedUser(
        user_id=str(claims["sub"]),
        email=claims.get("email"),
        role=claims.get("role", "authenticated"),
        token=raw_token,
        claims=claims,
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser | None:
    """FastAPI dependency permitting optional authentication."""
    if credentials is None or not credentials.credentials:
        return None

    try:
        raw_token = credentials.credentials
        claims = verify_supabase_token(raw_token)
        return AuthenticatedUser(
            user_id=str(claims["sub"]),
            email=claims.get("email"),
            role=claims.get("role", "authenticated"),
            token=raw_token,
            claims=claims,
        )
    except HTTPException:
        return None
