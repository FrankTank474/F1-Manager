from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .games import router as games_router
from .gameplay import router as gameplay_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(games_router)
api_router.include_router(gameplay_router)
