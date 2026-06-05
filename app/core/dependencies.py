from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户（通过 Token 验证）"""
    payload = verify_token(token)
    nickname = payload.get("sub")
    user_id = payload.get("user_id")
    
    if not nickname or not user_id:
        raise HTTPException(status_code=401, detail="令牌信息不完整")
    
    user = db.query(User).filter(User.id == user_id, User.nickname == nickname).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    if user.is_deleted:
        raise HTTPException(status_code=401, detail="用户已被删除")
    
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """获取当前登录用户（可选，没有 Token 时返回 None）"""
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        nickname = payload.get("sub")
        user_id = payload.get("user_id")
        
        if not nickname or not user_id:
            return None
        
        user = db.query(User).filter(User.id == user_id, User.nickname == nickname).first()
        if user and not user.is_deleted:
            return user
        return None
    except:
        return None
