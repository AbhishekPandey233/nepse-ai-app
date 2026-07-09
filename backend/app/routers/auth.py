"""POST /api/register, POST /api/login."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.db import get_database
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User

router = APIRouter()


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/api/register", response_model=TokenResponse)
async def register(payload: AuthRequest):
    users = get_database()["users"]

    if await users.find_one({"email": payload.email}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    await users.insert_one(user.model_dump())

    token = create_access_token({"sub": user.email})
    return TokenResponse(access_token=token)


@router.post("/api/login", response_model=TokenResponse)
async def login(payload: AuthRequest):
    users = get_database()["users"]
    user = await users.find_one({"email": payload.email})

    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user["email"]})
    return TokenResponse(access_token=token)
