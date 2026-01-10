from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .datastore.interface import DatastoreInterface
from .services.auth_service import AuthService
from .services.user_service import UserService

# Global datastore instance (set during app startup)
_datastore: Optional[DatastoreInterface] = None

# Security scheme
security = HTTPBearer()


def set_datastore(datastore: DatastoreInterface) -> None:
    """Set the global datastore instance."""
    global _datastore
    _datastore = datastore


def get_datastore() -> DatastoreInterface:
    """Get the global datastore instance."""
    if _datastore is None:
        raise RuntimeError("Datastore not initialized")
    return _datastore


def get_auth_service(
    datastore: DatastoreInterface = Depends(get_datastore),
) -> AuthService:
    """Get auth service instance."""
    return AuthService(datastore)


def get_user_service(
    datastore: DatastoreInterface = Depends(get_datastore),
) -> UserService:
    """Get user service instance."""
    return UserService(datastore)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """Validate token and return current user ID."""
    token = credentials.credentials
    user_id = await auth_service.validate_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id
