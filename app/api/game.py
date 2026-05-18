from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
from app.schemas.game import (
    GameMode,
    GameStatus,
    DiceRollRequest,
    DiceResetRequest,
    DiceToggleRequest,
    ScoreSubmitRequest,
    QuitGameRequest,
    GameStateResponse,
    GamePlayer,
    DiceRollResponse,
    DiceToggleResponse,
    ScoreSubmitResponse
)
from app.game.game_manager import GameManager
from app.websocket.manager import manager
from app.core.response import ApiResponse, ApiResponseModel

router = APIRouter(tags=["游戏"])


@router.get(
    "/{game_id}",
    summary="获取游戏状态",
    description="获取指定游戏的当前状态",
    responses={
        200: {
            "model": ApiResponseModel[GameStateResponse],
            "description": "成功响应"
        }
    }
)
async def get_game_state(game_id: str):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    game_dict = game_data.to_dict()
    game_data.close()
    
    return ApiResponse.success(
        data=GameStateResponse(
            game_id=game_dict["game_id"],
            game_mode=GameMode(game_dict["game_mode"]),
            current_player=game_dict["current_player"],
            players=[GamePlayer(**p) for p in game_dict["players"]],
            dice=game_dict["dice"],
            dice_locked=game_dict["dice_locked"],
            rolls_left=game_dict["rolls_left"],
            status=GameStatus(game_dict["status"]),
            created_at=game_dict["created_at"],
            finished_at=game_dict["finished_at"]
        ),
        msg="获取成功"
    )


@router.post(
    "/{game_id}/roll",
    summary="掷骰子",
    description="掷骰子，支持锁定指定骰子",
    responses={
        200: {
            "model": ApiResponseModel[DiceRollResponse],
            "description": "成功响应"
        }
    }
)
async def roll_dice(game_id: str, request: DiceRollRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    try:
        user_id = int(request.player_id)
        dice = GameManager.roll_dice(game_data, user_id, request.locked_dice)
        game_dict = game_data.to_dict()
        game_data.close()
        
        return ApiResponse.success(
            data=DiceRollResponse(
                dice=dice,
                dice_locked=game_dict["dice_locked"],
                rolls_left=game_dict["rolls_left"]
            ),
            msg="掷骰子成功"
        )
    except Exception as e:
        game_data.close()
        return ApiResponse.error(msg=str(e), code=400)


@router.post(
    "/{game_id}/dice/reset",
    summary="重置骰子",
    description="重置所有骰子（解锁）",
    responses={
        200: {
            "model": ApiResponseModel[DiceRollResponse],
            "description": "成功响应"
        }
    }
)
async def reset_dice(game_id: str, request: DiceResetRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    game_data.close()
    
    return ApiResponse.success(
        data=DiceRollResponse(
            dice=game_dict["dice"],
            dice_locked=game_dict["dice_locked"],
            rolls_left=game_dict["rolls_left"]
        ),
        msg="骰子已重置"
    )


@router.post(
    "/{game_id}/dice/toggle",
    summary="切换骰子锁定状态",
    description="切换指定骰子的锁定状态",
    responses={
        200: {
            "model": ApiResponseModel[DiceToggleResponse],
            "description": "成功响应"
        }
    }
)
async def toggle_dice_lock(game_id: str, request: DiceToggleRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    dice_locked = game_dict["dice_locked"]
    if 0 <= request.dice_index < 5:
        dice_locked[request.dice_index] = not dice_locked[request.dice_index]
    game_data.close()
    
    return ApiResponse.success(
        data=DiceToggleResponse(dice_locked=dice_locked),
        msg="切换成功"
    )


@router.post(
    "/{game_id}/score",
    summary="提交分数",
    description="将当前骰子组合的分数提交到指定计分项",
    responses={
        200: {
            "model": ApiResponseModel[ScoreSubmitResponse],
            "description": "成功响应"
        }
    }
)
async def submit_score(game_id: str, request: ScoreSubmitRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    try:
        user_id = int(request.player_id)
        score = GameManager.submit_score(game_data, user_id, request.category)
        game_dict = game_data.to_dict()
        
        next_player = game_dict["current_player"] if game_dict["status"] != "finished" else None
        
        game_data.close()
        
        return ApiResponse.success(
            data=ScoreSubmitResponse(
                category=request.category,
                score=score,
                game_state=GameStateResponse(
                    game_id=game_dict["game_id"],
                    game_mode=GameMode(game_dict["game_mode"]),
                    current_player=game_dict["current_player"],
                    players=[GamePlayer(**p) for p in game_dict["players"]],
                    dice=game_dict["dice"],
                    dice_locked=game_dict["dice_locked"],
                    rolls_left=game_dict["rolls_left"],
                    status=GameStatus(game_dict["status"]),
                    created_at=game_dict["created_at"],
                    finished_at=game_dict["finished_at"]
                ),
                next_player=next_player,
                is_game_finished=(game_dict["status"] == "finished")
            ),
            msg="分数提交成功"
        )
    except Exception as e:
        game_data.close()
        return ApiResponse.error(msg=str(e), code=400)


@router.post(
    "/{game_id}/quit",
    summary="退出游戏",
    description="中途退出游戏",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def quit_game(game_id: str, request: QuitGameRequest):
    GameManager.remove_game(game_id)
    return ApiResponse.success(msg="已退出游戏")


@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    await manager.connect(game_id, player_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(game_id, {"player_id": player_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(game_id, player_id, websocket)
