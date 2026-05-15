from fastapi import APIRouter
from typing import Dict
from app.schemas.game import (
    SoundSettingsUpdate,
    SoundSettingsResponse,
    GameRulesResponse,
    RuleCategory
)
from app.core.response import ApiResponse, ApiResponseModel
from app.game.scoring import ScoreCalculator

router = APIRouter(tags=["首页"])

sound_enabled = True


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
async def get_sound_settings():
    return ApiResponse.success(
        data=SoundSettingsResponse(sound_enabled=sound_enabled),
        msg="获取成功"
    )


@router.put(
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
async def update_sound_settings(request: SoundSettingsUpdate):
    global sound_enabled
    sound_enabled = request.sound_enabled
    return ApiResponse.success(
        data=SoundSettingsResponse(sound_enabled=sound_enabled),
        msg="保存成功"
    )
