from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int
    avatar: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(User):
    hashed_password: str
