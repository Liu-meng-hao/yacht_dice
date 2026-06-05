from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket.manager import manager
from app.game.game_manager import GameManager
from app.models.online_room import OnlineRoom
from app.models.room_player import RoomPlayer
from app.db.session import get_db
from sqlalchemy.orm import Session
import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ValidationError
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["实时通信"])


class MessageType(str, Enum):
    """消息类型枚举"""
    CHAT = "chat"
    GAME_ACTION = "game_action"
    SYSTEM = "system"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    GAME_STATE = "game_state"


class GameMessage(BaseModel):
    """消息结构验证模型"""
    type: MessageType
    content: dict = {}
    timestamp: str = None


async def validate_player(game_id: str, player_id: str) -> bool:
    """验证玩家是否属于指定游戏
    
    由于当前项目没有用户登录注册系统，此验证仅检查玩家是否在游戏中
    
    Args:
        game_id: 游戏ID
        player_id: 玩家ID
    
    Returns:
        bool: 玩家是否有效
    """
    # 检查游戏是否存在
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return False
    
    # 检查玩家是否在游戏中
    game_dict = game_data.to_dict()
    game_data.close()
    
    for player in game_dict["players"]:
        if player["player_id"] == player_id:
            return True
    
    return False


@router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    """WebSocket 游戏实时通信端点
    用于多人游戏状态实时同步
    
    Args:
        game_id: 游戏房间ID
        player_id: 玩家ID
    """
    # 验证玩家是否属于该游戏（可选功能，根据需要启用）
    # if not await validate_player(game_id, player_id):
    #     await websocket.close(code=1008)  # 策略性关闭
    #     return
    
    # 尝试连接
    success = await manager.connect(game_id, player_id, websocket)
    if not success:
        return
    
    try:
        # 连接成功后立即发送游戏状态快照
        game_data = GameManager.get_game(game_id)
        if game_data:
            game_dict = game_data.to_dict()
            game_data.close()
            
            # 发送游戏状态
            await websocket.send_text(json.dumps({
                "type": "game_state",
                "game_state": game_dict,
                "timestamp": datetime.now().isoformat()
            }))
            
            # 检查是否需要恢复AI回合
            from app.game.ai_controller import AIGameController
            from app.game.ai_task_manager import ai_task_manager
            
            if game_dict["status"] == "playing":
                current_player_data = next((p for p in game_dict["players"] if p["player_id"] == game_dict["current_player"]), None)
                if current_player_data and current_player_data.get("is_ai"):
                    # 短暂延迟后检查并恢复AI任务
                    asyncio.create_task(AIGameController.check_and_resume_ai_turn(game_id))
        
        while True:
            data = await websocket.receive_text()
            
            # 消息格式验证
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }))
                continue
            
            # 使用 Pydantic 验证消息结构
            try:
                validated_msg = GameMessage(**message)
            except ValidationError as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Invalid message structure: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }))
                continue
            
            # 处理心跳响应
            if message.get("type") == "pong":
                continue  # 心跳响应无需广播
            
            # 添加元数据
            message["player_id"] = player_id
            message["timestamp"] = datetime.now().isoformat()
            
            # 获取玩家名称
            player_name = manager.get_player_name(game_id, player_id)
            if player_name:
                message["player_name"] = player_name
            
            # 安全广播
            try:
                await manager.broadcast(game_id, message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"Player {player_id} disconnected from game {game_id}")
        manager.disconnect(game_id, player_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
        manager.disconnect(game_id, player_id, websocket)


@router.websocket("/room/ws/{room_code}/{player_id}")
async def room_websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    """WebSocket 房间实时通信端点
    用于房间状态实时同步

    Args:
        room_code: 房间编码
        player_id: 玩家ID
    """
    from app.db.session import SessionLocal
    from app.api.room import build_room_response
    from sqlalchemy.orm import joinedload

    # 验证 player_id 是否为有效整数
    try:
        player_id_int = int(player_id)
    except ValueError:
        logger.warning(f"Invalid player_id format: {player_id}")
        await websocket.close(code=1008, reason="Invalid player_id format")
        return

    db = SessionLocal()
    try:
        room = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == room_code,
            OnlineRoom.is_deleted == 0
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        if not room:
            logger.warning(f"Room not found: {room_code}")
            await websocket.close(code=1008, reason="Room not found")
            return

        player = db.query(RoomPlayer).filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.user_id == player_id_int
        ).first()

        if not player:
            logger.warning(f"Player {player_id} not in room {room_code}")
            await websocket.close(code=1008, reason="Player not in this room")
            return

        player_name = player.player_name

        # 构建房间快照（将 Pydantic 模型转换为字典，以便 JSON 序列化）
        room_response = build_room_response(room)
        room_snapshot = {
            "type": "room_updated",
            "data": room_response.model_dump() if hasattr(room_response, 'model_dump') else room_response.dict()
        }

    finally:
        db.close()

    success = await manager.connect(room_code, player_id, websocket, player_name)
    if not success:
        return
    
    logger.info(f"Player {player_id} ({player_name}) connected to room WebSocket {room_code}")

    # 连接成功后立即发送完整房间快照
    try:
        await websocket.send_text(json.dumps(room_snapshot))
        logger.info(f"Sent room snapshot to player {player_id}")
    except Exception as e:
        logger.error(f"Failed to send room snapshot to player {player_id}: {e}")
        manager.disconnect(room_code, player_id, websocket)
        return

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }))
                continue

            if message.get("type") == "pong":
                continue

            message["player_id"] = player_id
            message["timestamp"] = datetime.now().isoformat()

            try:
                await manager.broadcast(room_code, message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    except WebSocketDisconnect:
        logger.info(f"Player {player_id} disconnected from room WebSocket {room_code}")
        manager.disconnect(room_code, player_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
        manager.disconnect(room_code, player_id, websocket)
