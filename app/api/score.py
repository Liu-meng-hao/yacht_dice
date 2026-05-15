from fastapi import APIRouter
from typing import Dict, List
from app.schemas.game import (
    PossibleScoresResponse,
    ScoreHistoryRequest,
    ScoreHistoryResponse,
    LeaderboardResponse,
    LeaderboardItem
)
from app.game.game_manager import GameManager
from app.game.scoring import ScoreCalculator
from app.core.response import ApiResponse, ApiResponseModel

router = APIRouter(tags=["计分"])


@router.get(
    "/possible/{game_id}",
    summary="获取可能得分",
    description="计算当前骰子在所有计分项的可能得分",
    responses={
        200: {
            "model": ApiResponseModel[PossibleScoresResponse],
            "description": "成功响应"
        }
    }
)
async def get_possible_scores(game_id: str):
    game = GameManager.get_game(game_id)
    if not game:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    dice = game.dice_manager.get_dice()
    possible_scores: Dict[str, int] = {}
    
    for category in ScoreCalculator.CATEGORIES:
        try:
            possible_scores[category] = ScoreCalculator.calculate_score(dice, category)
        except:
            possible_scores[category] = None
    
    return ApiResponse.success(
        data=PossibleScoresResponse(possible_scores=possible_scores),
        msg="获取成功"
    )


@router.get(
    "/history",
    summary="获取历史记录",
    description="获取当前玩家的历史游戏记录",
    responses={
        200: {
            "model": ApiResponseModel[ScoreHistoryResponse],
            "description": "成功响应"
        }
    }
)
async def get_score_history(request: ScoreHistoryRequest):
    return ApiResponse.success(
        data=ScoreHistoryResponse(history=[]),
        msg="获取成功（功能开发中")


@router.get(
    "/leaderboard",
    summary="获取排行榜",
    description="获取排行榜",
    responses={
        200: {
            "model": ApiResponseModel[LeaderboardResponse],
            "description": "成功响应"
        }
    }
)
async def get_leaderboard():
    return ApiResponse.success(
        data=LeaderboardResponse(leaderboard=[]),
        msg="获取成功（功能开发中）"
    )
