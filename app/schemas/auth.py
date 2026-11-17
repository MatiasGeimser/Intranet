import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=50)

    @field_validator("new_password")
    @classmethod
    def validate_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("La contraseña debe incluir letras y números.")
        return value

class PasswordRecoveryRequest(BaseModel):
    email: str

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=50)
