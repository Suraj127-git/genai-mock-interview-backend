"""
User schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ...,
        min_length=6,
        max_length=72,
        description="Password must be between 6-72 characters (bcrypt limit)"
    )


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    current_password: Optional[str] = Field(None, alias="currentPassword")
    new_password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=72,
        alias="newPassword",
        description="Password must be between 6-72 characters (bcrypt limit)"
    )

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, user):
        """Convert ORM model to response schema."""
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    user: UserResponse
    token: str
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response."""
    access_token: str
    refresh_token: Optional[str] = None
