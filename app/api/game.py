from fastapi import APIRouter, Depends
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
from app.core.dependencies import get_current_user_optional
from app.models.user import User
from fastapi import HTTPException

router = APIRouter(tags=["游戏"])


@router.post(
    "/create",
    summary="创建游戏",
    description="创建新游戏，支持三种模式：\n"
                "- local（本地单人）：必须登录用户\n"
                "- ai（人机对战）：游客可用client_id玩（不记录积分），登录用户也可玩（记录积分）\n"
                "- online（在线联机）：必须登录，通过房间接口创建",
    responses={
        200: {
            "model": ApiResponseModel[CreateGameResponse],
            "description": "成功响应"
        }
    }
)
async def create_game(request: CreateGameRequest, user: Optional[User] = Depends(get_current_user_optional)):
    try:
        # LOCAL模式：必须是登录用户，必须传 player_name
        if request.game_mode == GameMode.LOCAL:
            if not user:
                raise HTTPException(status_code=401, detail="本地模式需要登录")

            if not request.player_name:
                raise HTTPException(status_code=400, detail="本地模式需要提供 player_name")

            result = GameManager.create_game(
                game_mode=request.game_mode.value,
                player_name=request.player_name
            )

            return ApiResponse.success(
                data=CreateGameResponse(
                    game_id=result["game_id"],
                    player_id=result["player_id"],
                    user_type=result["user_type"],
                    has_points=result["has_points"],
                    current_points=result["current_points"]
                ),
                msg="游戏创建成功"
            )

        # AI模式：游客和登录用户都可以玩
        elif request.game_mode == GameMode.AI:
            # 判断是游客还是登录用户
            if user:
                # 登录用户：必须传 player_name，记录积分
                if not request.player_name:
                    raise HTTPException(status_code=400, detail="AI模式（登录用户）需要提供 player_name")

                result = GameManager.create_game(
                    game_mode=request.game_mode.value,
                    player_name=request.player_name,
                    ai_difficulty=request.ai_difficulty
                )
            else:
                # 游客：后端自动生成 client_id，不记录积分
                # player_name 可选，不传则使用默认名称
                result = GameManager.create_game(
                    game_mode=request.game_mode.value,
                    player_name=request.player_name,
                    ai_difficulty=request.ai_difficulty
                )
            
            return ApiResponse.success(
                data=CreateGameResponse(
                    game_id=result["game_id"],
                    player_id=result["player_id"],
                    user_type=result["user_type"],
                    has_points=result["has_points"],
                    current_points=result["current_points"]
                ),
                msg="游戏创建成功"
            )
        
        # ONLINE 模式：必须登录，且需要通过房间接口创建
        elif request.game_mode == GameMode.ONLINE:
            raise HTTPException(status_code=400, detail="在线模式请通过房间接口创建")
        
        else:
            raise HTTPException(status_code=400, detail="不支持的游戏模式")
    
    except HTTPException:
        raise
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
async def get_game_state(game_id: str, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        game_data.close()
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
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
async def roll_dice(game_id: str, request: DiceRollRequest, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        game_data.close()
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
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
async def reset_dice(game_id: str, request: DiceResetRequest, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)

    game_dict = game_data.to_dict()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        game_data.close()
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
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
async def toggle_dice_lock(game_id: str, request: DiceToggleRequest, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)

    game_dict = game_data.to_dict()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        game_data.close()
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
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
async def submit_score(game_id: str, request: ScoreSubmitRequest, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        game_data.close()
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"submit_score called with game_id={game_id}, player_id={request.player_id}, category={request.category}")
        
        current_player = game_data.get_current_player()
        logger.info(f"Current player: {current_player.user_id if current_player else None}")
        logger.info(f"Is your turn: {str(current_player.user_id) == request.player_id if current_player else False}")
        
        result = GameManager.submit_score(game_data, request.player_id, request.category)
        logger.info(f"submit_score result: {result}")
        
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
        error_msg = str(e)
        logger.error(f"submit_score exception: {error_msg}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return ApiResponse.error(msg=error_msg, code=400)


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
async def quit_game(game_id: str, request: QuitGameRequest, user: Optional[User] = Depends(get_current_user_optional)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    game_data.close()
    
    # ONLINE 模式必须登录
    if game_dict["game_mode"] == GameMode.ONLINE.value and not user:
        return ApiResponse.error(msg="在线模式需要登录", code=401)
    
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
