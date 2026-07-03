from fastapi import APIRouter, Depends, HTTPException

from models.schemas import AuthRequest, AuthResponse
from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: AuthRequest) -> AuthResponse:
    try:
        user = register_user(request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return AuthResponse(
        access_token=create_access_token(user["id"], user["email"]),
        email=user["email"],
    )


@router.post("/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    user = authenticate_user(request.email, request.password)
    # Same message for wrong email vs wrong password — don't leak which accounts exist
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return AuthResponse(
        access_token=create_access_token(user["id"], user["email"]),
        email=user["email"],
    )


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return {"id": user["id"], "email": user["email"]}
