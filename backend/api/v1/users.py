from fastapi import APIRouter, Depends, HTTPException, status

from ...models.user import User, UserUpdate, PasswordChange
from ...models.auth import MessageResponse
from ...services.user_service import UserService
from ...dependencies import get_user_service, get_current_user_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """Get current user's profile."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch("/me", response_model=User)
async def update_current_user(
    update: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """Update current user's profile."""
    try:
        user = await user_service.update_user(user_id, update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/me/change-password", response_model=MessageResponse)
async def change_password(
    password_change: PasswordChange,
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """Change current user's password."""
    try:
        success = await user_service.change_password(user_id, password_change)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return MessageResponse(message="Password changed successfully. Please log in again.")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/me", response_model=MessageResponse)
async def delete_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """Delete current user's account."""
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return MessageResponse(message="Account deleted successfully")
