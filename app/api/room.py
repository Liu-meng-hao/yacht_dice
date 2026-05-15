from fastapi import APIRouter
from typing import Dict, Any
from app.schemas.game import (
    CreateRoomRequest,
    JoinRoomRequest,
    LeaveRoomRequest,
    StartGameRequest,
    DissolveRoomRequest,
    RoomResponse,
    RoomPlayer,
    RoomListResponse,
    RoomListItem,
    JoinRoomResponse,
    StartGameResponse,
    RoomStatus
)
from app.game.game_manager import GameManager
from app.core.response import ApiResponse, ApiResponseModel
import uuid
import random

router = APIRouter(tags=["房间"])

rooms: Dict[str, Dict[str, Any]] = {}


def generate_room_code():
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(random.choice(chars) for _ in range(6))


@router.post(
    "/create",
    summary="创建房间",
    description="创建新的联机游戏房间",
    responses={
        200: {
            "model": ApiResponseModel[RoomResponse],
            "description": "成功响应"
        }
    }
)
async def create_room(request: CreateRoomRequest):
    room_code = generate_room_code()
    while room_code in rooms:
        room_code = generate_room_code()
    
    player_id = str(uuid.uuid4())
    
    room = {
        "room_code": room_code,
        "room_name": request.room_name or f"房间 {room_code}",
        "max_players": request.max_players,
        "players": [
            {
                "player_id": player_id,
                "name": request.player_name,
                "is_host": True
            }
        ],
        "status": RoomStatus.WAITING,
        "host_id": player_id
    }
    
    rooms[room_code] = room
    
    return ApiResponse.success(
        data=RoomResponse(
            room_code=room["room_code"],
            room_name=room["room_name"],
            max_players=room["max_players"],
            players=[RoomPlayer(**p) for p in room["players"]],
            status=room["status"],
            host_id=room["host_id"]
        ),
        msg="房间创建成功"
    )


@router.post(
    "/join",
    summary="加入房间",
    description="加入指定的联机房间",
    responses={
        200: {
            "model": ApiResponseModel[JoinRoomResponse],
            "description": "成功响应"
        }
    }
)
async def join_room(request: JoinRoomRequest):
    if request.room_code not in rooms:
        return ApiResponse.error(msg="房间不存在", code=404)
    
    room = rooms[request.room_code]
    
    if room["status"] != RoomStatus.WAITING:
        return ApiResponse.error(msg="房间已开始游戏", code=409)
    
    if len(room["players"]) >= room["max_players"]:
        return ApiResponse.error(msg="房间已满", code=400)
    
    player_id = str(uuid.uuid4())
    player = {
        "player_id": player_id,
        "name": request.player_name,
        "is_host": False
    }
    
    room["players"].append(player)
    
    return ApiResponse.success(
        data=JoinRoomResponse(
            room=RoomResponse(
                room_code=room["room_code"],
                room_name=room["room_name"],
                max_players=room["max_players"],
                players=[RoomPlayer(**p) for p in room["players"]],
                status=room["status"],
                host_id=room["host_id"]
            ),
            player_id=player_id
        ),
        msg="加入房间成功"
    )


@router.post(
    "/leave",
    summary="离开房间",
    description="离开当前房间",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def leave_room(request: LeaveRoomRequest):
    if request.room_code not in rooms:
        return ApiResponse.error(msg="房间不存在", code=404)
    
    room = rooms[request.room_code]
    player_index = next((i for i, p in enumerate(room["players"]) if p["player_id"] == request.player_id), -1)
    
    if player_index == -1:
        return ApiResponse.error(msg="你不在这个房间", code=400)
    
    is_host = room["players"][player_index]["is_host"]
    room["players"].pop(player_index)
    
    if len(room["players"]) == 0:
        del rooms[request.room_code]
    elif is_host:
        room["players"][0]["is_host"] = True
        room["host_id"] = room["players"][0]["player_id"]
    
    return ApiResponse.success(msg="离开房间成功")


@router.get(
    "/{room_code}",
    summary="获取房间信息",
    description="获取指定房间的详细信息",
    responses={
        200: {
            "model": ApiResponseModel[RoomResponse],
            "description": "成功响应"
        }
    }
)
async def get_room(room_code: str):
    if room_code not in rooms:
        return ApiResponse.error(msg="房间不存在", code=404)
    
    room = rooms[room_code]
    return ApiResponse.success(
        data=RoomResponse(
            room_code=room["room_code"],
            room_name=room["room_name"],
            max_players=room["max_players"],
            players=[RoomPlayer(**p) for p in room["players"]],
            status=room["status"],
            host_id=room["host_id"]
        ),
        msg="获取成功"
    )


@router.get(
    "/list",
    summary="获取房间列表",
    description="获取所有等待中的房间列表",
    responses={
        200: {
            "model": ApiResponseModel[RoomListResponse],
            "description": "成功响应"
        }
    }
)
async def get_room_list():
    room_list = []
    for room in rooms.values():
        if room["status"] == RoomStatus.WAITING:
            room_list.append(RoomListItem(
                room_code=room["room_code"],
                room_name=room["room_name"],
                player_count=len(room["players"]),
                max_players=room["max_players"],
                status=room["status"]
            ))
    
    return ApiResponse.success(
        data=RoomListResponse(rooms=room_list),
        msg="获取成功"
    )


@router.post(
    "/{room_code}/start",
    summary="房主开始游戏",
    description="房主开始游戏",
    responses={
        200: {
            "model": ApiResponseModel[StartGameResponse],
            "description": "成功响应"
        }
    }
)
async def start_game(room_code: str, request: StartGameRequest):
    if room_code not in rooms:
        return ApiResponse.error(msg="房间不存在", code=404)
    
    room = rooms[room_code]
    
    if room["host_id"] != request.player_id:
        return ApiResponse.error(msg="只有房主才能开始游戏", code=403)
    
    if room["status"] != RoomStatus.WAITING:
        return ApiResponse.error(msg="房间已开始游戏", code=409)
    
    if len(room["players"]) < 2:
        return ApiResponse.error(msg="至少需要2名玩家", code=400)
    
    player_names = [p["name"] for p in room["players"]]
    game_data = GameManager.create_game("online", player_names)
    GameManager.start_game(game_data)
    game_dict = game_data.to_dict()
    game_id = game_dict["game_id"]
    game_data.close()
    
    room["status"] = RoomStatus.PLAYING
    room["game_id"] = game_id
    
    return ApiResponse.success(
        data=StartGameResponse(
            game_id=game_id,
            room_code=room_code
        ),
        msg="游戏开始"
    )


@router.delete(
    "/{room_code}",
    summary="房主解散房间",
    description="房主解散房间",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def dissolve_room(room_code: str, request: DissolveRoomRequest):
    if room_code not in rooms:
        return ApiResponse.error(msg="房间不存在", code=404)
    
    room = rooms[room_code]
    
    if room["host_id"] != request.player_id:
        return ApiResponse.error(msg="只有房主才能解散房间", code=403)
    
    del rooms[room_code]
    
    return ApiResponse.success(msg="房间已解散")
