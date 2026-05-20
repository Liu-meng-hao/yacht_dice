from datetime import datetime, timedelta
from typing import Optional
import re
import html
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def escape_html(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return html.escape(text)


def validate_nickname(nickname: str) -> tuple[bool, str]:
    if not nickname or len(nickname.strip()) == 0:
        return False, "昵称不能为空"
    
    if len(nickname) > 50:
        return False, "昵称长度不能超过50个字符"
    
    if re.search(r'[<>\"\'&]', nickname):
        return False, "昵称包含非法字符"
    
    if re.search(r'(<script|javascript:|on\w+=)', nickname, re.IGNORECASE):
        return False, "昵称包含危险内容"
    
    return True, nickname.strip()


def sanitize_nickname(nickname: Optional[str]) -> Optional[str]:
    if nickname is None:
        return None
    
    nickname = nickname.strip()
    nickname = html.escape(nickname)
    nickname = re.sub(r'[^\w\s\u4e00-\u9fff_-]', '', nickname)
    
    if len(nickname) > 50:
        nickname = nickname[:50]
    
    return nickname if nickname else None
