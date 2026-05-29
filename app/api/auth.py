from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import get_password_hash, verify_password, create_access_token, validate_password
from app.core.config import settings
from datetime import timedelta

router = APIRouter()


@router.post("/register", response_model=TokenResponse, summary="用户注册")
def register(
    user: UserRegister,
    db: Session = Depends(get_db)
):
    """
    用户注册接口
    
    - **nickname**: 用户昵称（唯一，用于登录）
    - **password**: 密码
    """
    # 检查昵称是否已存在
    existing_user = db.query(User).filter(User.nickname == user.nickname).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="昵称已被使用")
    
    # 检查客户端ID是否已存在
    existing_client = db.query(User).filter(User.client_id == user.nickname).first()
    if existing_client:
        raise HTTPException(status_code=400, detail="该昵称已关联其他账号")
    
    # 验证密码强度
    password_valid, password_msg = validate_password(user.password)
    if not password_valid:
        raise HTTPException(status_code=400, detail=password_msg)
    
    # 创建新用户
    hashed_password = get_password_hash(user.password)
    new_user = User(
        client_id=user.nickname,
        nickname=user.nickname,
        password=hashed_password,
        user_type=1,
        points=1580  # 默认初始积分
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.nickname, "user_id": new_user.id},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=new_user.id,
            nickname=new_user.nickname,
            points=new_user.points,
            total_games=new_user.total_games,
            total_wins=new_user.total_wins,
            highest_score=new_user.highest_score
        )
    )


@router.post("/login", response_model=TokenResponse, summary="用户登录")
def login(
    user: UserLogin,
    db: Session = Depends(get_db)
):
    """
    用户登录接口
    
    - **nickname**: 用户昵称
    - **password**: 密码
    """
    # 查找用户
    db_user = db.query(User).filter(User.nickname == user.nickname).first()
    
    if not db_user:
        raise HTTPException(status_code=400, detail="昵称或密码错误")
    
    if not db_user.password:
        raise HTTPException(status_code=400, detail="该账号未设置密码，请联系管理员")
    
    # 验证密码
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="昵称或密码错误")
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user.nickname, "user_id": db_user.id},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=db_user.id,
            nickname=db_user.nickname,
            points=db_user.points,
            total_games=db_user.total_games,
            total_wins=db_user.total_wins,
            highest_score=db_user.highest_score
        )
    )