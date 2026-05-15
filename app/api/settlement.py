from fastapi import APIRouter
from typing import List
from app.schemas.game import (
    SettlementResponse,
    SettlementPlayer,
    RematchRequest,
    RematchResponse,
    BackToHomeRequest,
    GameMode,
    GameStatus,
    GameStateResponse,
    GamePlayer
)
from app.game.game_manager import GameManager
from app.core.response import ApiResponse, ApiResponseModel

router = APIRouter(tags=["结算"])


@router.get(
    "/{game_id}",
    summary="获取结算信息",
    description="获取游戏结算信息",
    responses={
        200: {
            "model": ApiResponseModel[SettlementResponse],
            "description": "成功响应"
        }
    }
)
async def get_settlement(game_id: str):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    
    if game_dict["status"] != "finished":
        game_data.close()
        return ApiResponse.error(msg="游戏未结束", code=409)
    
    players_with_rank = []
    sorted_players = sorted(game_dict["players"], key=lambda p: -p["total_score"])
    
    for rank, player in enumerate(sorted_players, 1):
        players_with_rank.append(SettlementPlayer(
            player_id=player["player_id"],
            name=player["name"],
            final_score=player["total_score"],
            rank=rank,
            is_winner=(rank == 1),
            scores=player["scores"]
        ))
    
    game_data.close()
    
    return ApiResponse.success(
        data=SettlementResponse(
            game_id=game_dict["game_id"],
            finished_at=game_dict["finished_at"] or "",
            players=players_with_rank
        ),
        msg="获取成功"
    )


@router.post(
    "/{game_id}/rematch",
    summary="再来一局",
    description="开始新一局游戏",
    responses={
        200: {
            "model": ApiResponseModel[RematchResponse],
            "description": "成功响应"
        }
    }
)
async def rematch(game_id: str, request: RematchRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    player_names = [p["name"] for p in game_dict["players"]]
    game_mode = game_dict["game_mode"]
    game_data.close()
    
    new_game_data = GameManager.create_game(game_mode, player_names)
    GameManager.start_game(new_game_data)
    new_game_dict = new_game_data.to_dict()
    new_game_data.close()
    
    return ApiResponse.success(
        data=RematchResponse(
            new_game_id=new_game_dict["game_id"],
            game_state=GameStateResponse(
                game_id=new_game_dict["game_id"],
                game_mode=GameMode(new_game_dict["game_mode"]),
                current_player=new_game_dict["current_player"],
                players=[GamePlayer(**p) for p in new_game_dict["players"]],
                dice=new_game_dict["dice"],
                dice_locked=new_game_dict["dice_locked"],
                rolls_left=new_game_dict["rolls_left"],
                status=GameStatus(new_game_dict["status"]),
                created_at=new_game_dict["created_at"],
                finished_at=new_game_dict["finished_at"]
            )
        ),
        msg="新游戏已创建"
    )


@router.post(
    "/{game_id}/back",
    summary="返回首页",
    description="返回模式选择首页",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def back_to_home(game_id: str, request: BackToHomeRequest):
    GameManager.remove_game(game_id)
    return ApiResponse.success(msg="已返回首页")
