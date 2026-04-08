"""
Authentication routes for user registration and login.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from zyx_ai.database.session import get_db
from zyx_ai.core.security import create_access_token, verify_password, get_password_hash
from zyx_ai.core.config import settings
from zyx_ai.database.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    username: str,
    email: str,
    password: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Register a new user account."""
    # Check if user exists
    # TODO: Query database for existing user
    
    # Create new user
    hashed_password = get_password_hash(password)
    
    # TODO: Save user to database
    
    return {
        "message": "User registered successfully",
        "username": username,
        "email": email
    }


@router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Login and get JWT access token."""
    # TODO: Verify user credentials from database
    
    # For now, return a mock token
    access_token = create_access_token(
        data={"sub": form_data.username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiration_hours * 3600
    }


@router.post("/refresh")
async def refresh_token(current_user: Annotated[str, Depends(oauth2_scheme)]):
    """Refresh JWT access token."""
    new_token = create_access_token(data={"sub": current_user})
    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
