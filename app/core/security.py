from datetime import datetime, timedelta
from typing import Optional
import re
import html
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException
from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对密码进行哈希处理"""
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


def validate_password(password: str) -> tuple[bool, str]:
    if not password or len(password.strip()) == 0:
        return False, "密码不能为空"
    
    if len(password) < 8:
        return False, "密码长度不能少于8个字符"
    
    if len(password) > 128:
        return False, "密码长度不能超过128个字符"
    
    if re.search(r'[<>\"\'&;]', password):
        return False, "密码包含非法字符"
    
    if re.search(r'(<script|javascript:|on\w+=)', password, re.IGNORECASE):
        return False, "密码包含危险内容"
    
    weak_patterns = [
        r'^(\d{8,})$',
        r'^(abcdef|qwerty|123456|password|admin|root|123qwe)(.*)$',
        r'^(\w)\1{5,}$'
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password.lower()):
            return False, "密码过于简单，请使用更复杂的密码"
    
    if not re.search(r'[a-zA-Z]', password):
        return False, "密码必须包含至少一个字母"
    
    if not re.search(r'[0-9]', password):
        return False, "密码必须包含至少一个数字"
    
    return True, password.strip()


def verify_token(token: str) -> dict:
    """验证 Token 并返回 payload"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的令牌")
