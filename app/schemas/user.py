from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegister(BaseModel):
    """用户注册请求模型"""
    nickname: str = Field(..., description="用户昵称（用于登录）")
    phone: str = Field(..., description="手机号码")
    password: str = Field(..., description="密码")


class UserLogin(BaseModel):
    """用户登录请求模型"""
    account: str = Field(..., description="用户昵称或手机号码")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: int
    nickname: Optional[str] = None
    phone: Optional[str] = None
    points: int
    total_games: int
    total_wins: int
    highest_score: int
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """登录/注册成功响应模型"""
    access_token: str
    token_type: str
    user: UserResponse


class UserBase(BaseModel):
    username: str
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
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