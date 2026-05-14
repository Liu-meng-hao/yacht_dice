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

router = APIRouter()


@router.post("/create", response_model=GameStateResponse)
async def create_game(game_mode: GameMode, player_names: List[str]):
    game = GameManager.create_game(game_mode, player_names)
    game.start()
    return game.to_dict()


@router.get("/{game_id}", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    game = GameManager.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="游戏不存在")
    return game.to_dict()


@router.post("/{game_id}/roll")
async def roll_dice(game_id: str, request: DiceRollRequest):
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


@router.post("/{game_id}/score")
async def submit_score(game_id: str, request: ScoreSubmitRequest):
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


@router.post("/rooms/create", response_model=RoomResponse)
async def create_room(request: CreateRoomRequest):
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


@router.post("/rooms/join")
async def join_room(request: JoinRoomRequest):
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


@router.get("/rooms/{room_code}", response_model=RoomResponse)
async def get_room(room_code: str):
    if room_code not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    return rooms[room_code]


@router.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str):
    await manager.connect(room_code, player_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(room_code, {"player_id": player_id, "data": data})
    except WebSocketDisconnect:
        manager.disconnect(room_code, player_id, websocket)
