from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)

class PasswordRecoveryRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=50)
