from typing import Optional
from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from pydantic.class_validators import validator
from pydantic import (
    BaseModel,
    Field
)


class BaseUser(BaseModel):
    email: str = Field(...)
    username: str = Field(...)


class User(BaseUser):
    password: str = Field(...)

    @validator('username')
    def validate_username(cls, v):
        if v is '':
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Username field is required"
            )
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is '':
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Email field is required"
            )
        return v

    @validator('password')
    def validate_password(cls, v):
        if v is '':
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Password field is required"
            )
        return v


class LoginUser(BaseModel):
    email: str
    password: str


class UpdateUser(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

class OutUser(BaseModel):
    id: str = Field(...)
    username: str = Field(...)
    email: str = Field(...)