from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.seguridad import Usuario
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RegisterFirstAdminRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    usuario = auth_service.autenticar(db, body.nombre_usuario, body.contrasena)
    token, expires_in = auth_service.create_access_token(
        id_usuario=usuario.id_usuario,
        rol=usuario.rol.value if hasattr(usuario.rol, "value") else str(usuario.rol),
    )
    return TokenResponse(access_token=token, token_type="bearer", expires_in=expires_in)


@router.get("/me", response_model=CurrentUserResponse)
def me(current: Usuario = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current)


@router.post(
    "/register-first-admin",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_first_admin(
    body: RegisterFirstAdminRequest, db: Session = Depends(get_db)
) -> CurrentUserResponse:
    usuario = auth_service.bootstrap_first_admin(db, body)
    return CurrentUserResponse.model_validate(usuario)
