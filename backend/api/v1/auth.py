from fastapi import APIRouter, Depends, HTTPException, status, Request

from ...models.auth import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse, MessageResponse
from ...models.user import UserCreate, User
from ...services.auth_service import AuthService
from ...dependencies import get_auth_service, get_current_user_id
from ...middleware.rate_limit import rate_limiter

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user account."""
    try:
        user = await auth_service.register_user(user_data)
        return {
            "message": "Registration successful. Please log in.",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return tokens."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}"

    # Check rate limit
    if not await rate_limiter.is_allowed(rate_key):
        reset_time = rate_limiter.get_reset_time(rate_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {reset_time} seconds.",
        )

    result = await auth_service.authenticate(credentials.email, credentials.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Reset rate limit on successful login
    await rate_limiter.reset(rate_key)

    return result


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    data: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token."""
    result = await auth_service.refresh_access_token(data.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    return result


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
    request: Request = None,
):
    """Logout and invalidate current token."""
    # Get token from header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        await auth_service.logout(token)

    return MessageResponse(message="Successfully logged out")
