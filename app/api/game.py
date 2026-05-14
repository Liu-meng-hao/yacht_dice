from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List
from app.schemas.game import (
    GameMode,
    DiceRollRequest,
    ScoreSubmitRequest,
    CreateRoomRequest,
    JoinRoomRequest,
    RoomResponse,
    GameStateResponse
)
from app.game.game_manager import GameManager
from app.websocket.manager import manager
import uuid
import random

router = APIRouter(tags=["游戏"])


@router.post("/create", response_model=GameStateResponse, summary="创建游戏", description="创建新的快艇骰子游戏对局")
async def create_game(game_mode: GameMode, player_names: List[str]):
    """
    创建新的快艇骰子游戏
    
    - **game_mode**: 游戏模式（local/ai/online）
    - **player_names**: 玩家名称列表
    """
    game = GameManager.create_game(game_mode, player_names)
    game.start()
    return game.to_dict()


@router.get("/{game_id}", response_model=GameStateResponse, summary="获取游戏状态", description="获取指定游戏的当前状态")
async def get_game_state(game_id: str):
    """
    获取游戏状态
    
    - **game_id**: 游戏ID
    """
    game = GameManager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return game.to_dict()


@router.post("/{game_id}/roll", summary="掷骰子", description="掷骰子，支持锁定指定骰子")
async def roll_dice(game_id: str, request: DiceRollRequest):
    """
    掷骰子
    
    - **game_id**: 游戏ID
    - **locked_dice**: 要锁定的骰子索引列表（0-4）
    """
    game = GameManager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    try:
        dice = game.roll_dice(request.locked_dice)
        return {
            "dice": dice,
            "rolls_left": game.rolls_left
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/score", summary="提交分数", description="将当前骰子组合的分数提交到指定计分项")
async def submit_score(game_id: str, request: ScoreSubmitRequest):
    """
    提交分数
    
    - **game_id**: 游戏ID
    - **player_id**: 玩家ID
    - **category**: 计分项名称
    """
    game = GameManager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    try:
        score = game.submit_score(request.player_id, request.category)
        return {
            "category": request.category,
            "score": score,
            "game_state": game.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


rooms = {}


def generate_room_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(6))


@router.post("/rooms/create", response_model=RoomResponse, summary="创建房间", description="创建联机游戏房间")
async def create_room(request: CreateRoomRequest):
    """
    创建联机房间
    
    - **room_name**: 房间名称（可选）
    - **max_players**: 最大玩家数（默认4）
    - **game_mode**: 游戏模式
    """
    room_code = generate_room_code()
    while room_code in rooms:
        room_code = generate_room_code()
    
    room = {
        "room_code": room_code,
        "room_name": request.room_name or f"房间 {room_code}",
        "max_players": request.max_players,
        "players": [],
        "status": "waiting",
        "host_id": None
    }
    rooms[room_code] = room
    return room


@router.post("/rooms/join", summary="加入房间", description="加入指定的联机房间")
async def join_room(request: JoinRoomRequest):
    """
    加入联机房间
    
    - **room_code**: 房间号
    - **player_name**: 玩家名称
    """
    if request.room_code not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    room = rooms[request.room_code]
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="房间已开始游戏")
    if len(room["players"]) >= room["max_players"]:
        raise HTTPException(status_code=400, detail="房间已满")
    
    player_id = str(uuid.uuid4())
    player = {
        "player_id": player_id,
        "name": request.player_name,
        "is_host": len(room["players"]) == 0
    }
    
    if player["is_host"]:
        room["host_id"] = player_id
    
    room["players"].append(player)
    
    return {
        "room": room,
        "player_id": player_id
    }


@router.get("/rooms/{room_code}", response_model=RoomResponse, summary="获取房间信息", description="获取指定房间的详细信息")
async def get_room(room_code: str):
    """
    获取房间信息
    
    - **room_code**: 房间号
    """
    if room_code not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    return rooms[room_code]


@router.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    """
    WebSocket 连接端点
    
    - **room_code**: 房间号
    - **player_id**: 玩家ID
    """
    await manager.connect(room_code, player_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(room_code, {"player_id": player_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(room_code, player_id, websocket)
