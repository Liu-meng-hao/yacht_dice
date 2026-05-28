from fastapi import APIRouter
from typing import Optional
import re
from datetime import datetime
from app.schemas.game import (
    GameMode,
    GameStatus,
    CreateGameRequest,
    CreateGameResponse,
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
from app.core.response import ApiResponse, ApiResponseModel
from app.websocket.manager import manager

router = APIRouter(tags=["游戏"])


@router.post(
    "/create",
    summary="创建游戏",
    description="创建新游戏，支持本地多人、人机对战模式",
    responses={
        200: {
            "model": ApiResponseModel[CreateGameResponse],
            "description": "成功响应"
        }
    }
)
async def create_game(request: CreateGameRequest):
    game_data = None
    try:
        # 将玩家名称列表转换为字典列表
        players = [{"player_name": name} for name in request.player_names]
        game_data = GameManager.create_game(request.game_mode.value, players)
        game_dict = game_data.to_dict()
        game_data.close()
        
        return ApiResponse.success(
            data=CreateGameResponse(
                game_id=game_dict["game_id"],
                player_id=game_dict["players"][0]["player_id"]
            ),
            msg="游戏创建成功"
        )
    except Exception as e:
        error_msg = str(e)
        if "validation error" in error_msg.lower():
            match = re.search(r'Field required|Input should be|validation error for (\w+)', error_msg)
            if match:
                if "Field required" in error_msg:
                    field_match = re.search(r'Field required: (\w+)', error_msg)
                    field = field_match.group(1) if field_match else "未知字段"
                    error_msg = f"缺少必填字段: {field}"
                elif "Input should be" in error_msg:
                    field_match = re.search(r' (\w+)\s*$', error_msg.split('\n')[0])
                    field = field_match.group(1) if field_match else "字段"
                    error_msg = f"字段 {field} 类型错误或值为空"
                else:
                    model_match = re.search(r'validation error for (\w+)', error_msg)
                    model = model_match.group(1) if model_match else ""
                    error_msg = f"数据验证失败: {model}"
        if game_data:
            game_data.close()
        return ApiResponse.error(msg=error_msg, code=400)


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
        locked_indices = [i for i, locked in enumerate(request.locked_dice) if locked]
        dice = GameManager.roll_dice(game_data, request.player_id, locked_indices)
        game_dict = game_data.to_dict()
        game_data.close()

        broadcast_msg = {
            "type": "game_action",
            "action": "roll",
            "player_id": request.player_id,
            "dice": dice,
            "dice_locked": game_dict["dice_locked"],
            "rolls_left": game_dict["rolls_left"],
            "current_player": game_dict["current_player"],
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(game_id, broadcast_msg)

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

    broadcast_msg = {
        "type": "game_action",
        "action": "dice_reset",
        "player_id": request.player_id,
        "dice": game_dict["dice"],
        "dice_locked": game_dict["dice_locked"],
        "rolls_left": game_dict["rolls_left"],
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(game_id, broadcast_msg)

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

    broadcast_msg = {
        "type": "game_action",
        "action": "dice_toggle",
        "player_id": request.player_id,
        "dice_index": request.dice_index,
        "dice_locked": dice_locked,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(game_id, broadcast_msg)

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
        result = GameManager.submit_score(game_data, request.player_id, request.category)
        game_dict = game_data.to_dict()

        next_player = game_dict["current_player"] if game_dict["status"] != "finished" else None

        broadcast_msg = {
            "type": "game_action",
            "action": "score_submit",
            "player_id": request.player_id,
            "category": request.category,
            "score": result["score"],
            "total_score": result["total_score"],
            "game_state": {
                "game_id": game_dict["game_id"],
                "game_mode": game_dict["game_mode"],
                "current_player": game_dict["current_player"],
                "players": game_dict["players"],
                "dice": game_dict["dice"],
                "dice_locked": game_dict["dice_locked"],
                "rolls_left": game_dict["rolls_left"],
                "status": game_dict["status"]
            },
            "next_player": next_player,
            "is_game_finished": (game_dict["status"] == "finished"),
            "timestamp": datetime.now().isoformat()
        }
        await manager.broadcast(game_id, broadcast_msg)

        game_data.close()

        return ApiResponse.success(
            data=ScoreSubmitResponse(
                category=request.category,
                score=result["score"],
                upper_score=result["upper_score"],
                lower_score=result["lower_score"],
                bonus_score=result["bonus_score"],
                total_score=result["total_score"],
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
    broadcast_msg = {
        "type": "system",
        "action": "player_quit",
        "player_id": request.player_id,
        "game_id": game_id,
        "timestamp": datetime.now().isoformat()
    }
    await manager.broadcast(game_id, broadcast_msg)

    GameManager.remove_game(game_id)
    return ApiResponse.success(msg="已退出游戏")
