from fastapi import APIRouter, Depends, Query
from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.schemas.game import (
    SoundSettingsUpdate,
    SoundSettingsResponse,
    GameRulesResponse,
    RuleCategory,
    PointsResponse,
    RulePopupSettingsUpdate,
    RulePopupSettingsResponse,
    RegisterRequest,
    RegisterResponse
)
from app.core.response import ApiResponse, ApiResponseModel
from app.db.session import get_db
from app.models.user import User
from app.models.user_setting import UserSetting

router = APIRouter(tags=["首页"])


@router.post(
    "/register",
    summary="用户注册",
    description="创建新用户账号，用于在线游戏",
    responses={
        200: {
            "model": ApiResponseModel[RegisterResponse],
            "description": "成功响应"
        }
    }
)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # 检查用户是否已存在
    existing_user = db.query(User).filter(User.client_id == request.client_id).first()
    if existing_user:
        return ApiResponse.error(msg="用户已存在", code=409)
    
    # 创建新用户
    new_user = User(
        client_id=request.client_id,
        nickname=request.nickname,
        user_type=1,  # 真实玩家
        points=100  # 初始积分
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 创建用户设置
    new_setting = UserSetting(
        user_id=new_user.id,
        sound_enabled=1,
        rule_popup_enabled=1
    )
    db.add(new_setting)
    db.commit()
    
    return ApiResponse.success(
        data=RegisterResponse(
            user_id=new_user.id,
            client_id=new_user.client_id,
            nickname=new_user.nickname,
            points=new_user.points
        ),
        msg="注册成功"
    )


def get_user_by_client_id(db: Session, client_id: str) -> Optional[User]:
    return db.query(User).filter(User.client_id == client_id).first()


def get_user_setting(db: Session, user_id: int) -> Optional[UserSetting]:
    return db.query(UserSetting).filter(UserSetting.user_id == user_id).first()


@router.get(
    "/rules",
    summary="获取游戏规则",
    description="获取快艇骰子游戏的完整规则说明",
    responses={
        200: {
            "model": ApiResponseModel[GameRulesResponse],
            "description": "成功响应"
        }
    }
)
async def get_game_rules():
    categories = [
        RuleCategory(name="ones", description="一点 - 计算所有1点的和"),
        RuleCategory(name="twos", description="两点 - 计算所有2点的和"),
        RuleCategory(name="threes", description="三点 - 计算所有3点的和"),
        RuleCategory(name="fours", description="四点 - 计算所有4点的和"),
        RuleCategory(name="fives", description="五点 - 计算所有5点的和"),
        RuleCategory(name="sixes", description="六点 - 计算所有6点的和"),
        RuleCategory(name="threeOfAKind", description="三个相同 - 计算所有骰子的和"),
        RuleCategory(name="fourOfAKind", description="四个相同 - 计算所有骰子的和"),
        RuleCategory(name="fullHouse", description="葫芦 - 三个相同加两个相同，得25分"),
        RuleCategory(name="smallStraight", description="小顺子 - 四个连续点数，得30分"),
        RuleCategory(name="largeStraight", description="大顺子 - 五个连续点数，得40分"),
        RuleCategory(name="yahtzee", description="快艇 - 五个相同，得50分"),
        RuleCategory(name="chance", description="机会 - 计算所有骰子的和")
    ]
    
    rules_text = """
快艇骰子游戏规则：

1. 每局游戏由多名玩家轮流进行
2. 每个玩家回合有3次掷骰子机会
3. 每次掷骰子后，可以选择锁定部分骰子
4. 第3次掷骰子后，必须选择一个计分项提交分数
5. 每个计分项只能使用一次
6. 所有玩家完成所有计分项后，游戏结束
7. 总分最高的玩家获胜

计分规则详见右侧列表。
    """.strip()
    
    return ApiResponse.success(
        data=GameRulesResponse(
            rules=rules_text,
            categories=categories
        ),
        msg="获取成功"
    )


@router.get(
    "/points",
    summary="获取玩家积分",
    description="获取当前玩家的积分",
    responses={
        200: {
            "model": ApiResponseModel[PointsResponse],
            "description": "成功响应"
        }
    }
)
async def get_points(client_id: str = Query(..., description="客户端ID"), db: Session = Depends(get_db)):
    user = get_user_by_client_id(db, client_id)
    if not user:
        return ApiResponse.error(msg="用户不存在", code=404)
    return ApiResponse.success(
        data=PointsResponse(points=user.points),
        msg="获取成功"
    )


@router.get(
    "/settings/sound",
    summary="获取音效设置",
    description="获取当前音效开关状态",
    responses={
        200: {
            "model": ApiResponseModel[SoundSettingsResponse],
            "description": "成功响应"
        }
    }
)
async def get_sound_settings(client_id: str = Query(..., description="客户端ID"), db: Session = Depends(get_db)):
    user = get_user_by_client_id(db, client_id)
    if not user:
        return ApiResponse.error(msg="用户不存在", code=404)
    setting = get_user_setting(db, user.id)
    if not setting:
        return ApiResponse.error(msg="用户设置不存在", code=404)
    return ApiResponse.success(
        data=SoundSettingsResponse(sound_enabled=setting.sound_enabled),
        msg="获取成功"
    )


@router.post(
    "/settings/sound",
    summary="保存音效设置",
    description="保存音效开关状态",
    responses={
        200: {
            "model": ApiResponseModel[SoundSettingsResponse],
            "description": "成功响应"
        }
    }
)
async def update_sound_settings(request: SoundSettingsUpdate, db: Session = Depends(get_db)):
    user = get_user_by_client_id(db, request.client_id)
    if not user:
        return ApiResponse.error(msg="用户不存在", code=404)
    setting = get_user_setting(db, user.id)
    if not setting:
        return ApiResponse.error(msg="用户设置不存在", code=404)
    setting.sound_enabled = request.sound_enabled
    db.commit()
    db.refresh(setting)
    return ApiResponse.success(
        data=SoundSettingsResponse(sound_enabled=setting.sound_enabled),
        msg="保存成功"
    )


@router.get(
    "/settings/rule_popup",
    summary="获取规则弹窗设置",
    description="获取当前规则弹窗开关状态",
    responses={
        200: {
            "model": ApiResponseModel[RulePopupSettingsResponse],
            "description": "成功响应"
        }
    }
)
async def get_rule_popup_settings(client_id: str = Query(..., description="客户端ID"), db: Session = Depends(get_db)):
    user = get_user_by_client_id(db, client_id)
    if not user:
        return ApiResponse.error(msg="用户不存在", code=404)
    setting = get_user_setting(db, user.id)
    if not setting:
        return ApiResponse.error(msg="用户设置不存在", code=404)
    return ApiResponse.success(
        data=RulePopupSettingsResponse(rule_popup_enabled=setting.rule_popup_enabled),
        msg="获取成功"
    )


@router.post(
    "/settings/rule_popup",
    summary="保存规则弹窗设置",
    description="保存规则弹窗开关状态",
    responses={
        200: {
            "model": ApiResponseModel[RulePopupSettingsResponse],
            "description": "成功响应"
        }
    }
)
async def update_rule_popup_settings(request: RulePopupSettingsUpdate, db: Session = Depends(get_db)):
    user = get_user_by_client_id(db, request.client_id)
    if not user:
        return ApiResponse.error(msg="用户不存在", code=404)
    setting = get_user_setting(db, user.id)
    if not setting:
        return ApiResponse.error(msg="用户设置不存在", code=404)
    setting.rule_popup_enabled = request.rule_popup_enabled
    db.commit()
    db.refresh(setting)
    return ApiResponse.success(
        data=RulePopupSettingsResponse(rule_popup_enabled=setting.rule_popup_enabled),
        msg="保存成功"
    )
