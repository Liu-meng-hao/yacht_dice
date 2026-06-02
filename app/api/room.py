from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any
from app.schemas.game import (
    CreateRoomRequest,
    JoinRoomRequest,
    LeaveRoomRequest,
    StartGameRequest,
    DissolveRoomRequest,
    KickPlayerRequest,
    ReadyRequest,
    RoomResponse,
    RoomPlayer as RoomPlayerSchema,
    RoomListResponse,
    RoomListItem,
    JoinRoomResponse,
    StartGameResponse,
    RoomStatus
)
from app.models.online_room import OnlineRoom
from app.models.room_player import RoomPlayer
from app.models.user import User
from app.game.game_manager import GameManager
from app.core.response import ApiResponse, ApiResponseModel
from app.core.security import verify_token
from app.db.session import get_db
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import random
from app.websocket.manager import manager

router = APIRouter(tags=["房间"])

# OAuth2 令牌方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户（通过 Token 验证）"""
    payload = verify_token(token)
    nickname = payload.get("sub")
    user_id = payload.get("user_id")
    
    if not nickname or not user_id:
        raise HTTPException(status_code=401, detail="令牌信息不完整")
    
    user = db.query(User).filter(User.id == user_id, User.nickname == nickname).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    return user


def generate_room_code(db: Session):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    while True:
        code = ''.join(random.choice(chars) for _ in range(6))
        exists = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == code,
            OnlineRoom.is_deleted == 0
        ).first()
        if not exists:
            return code


def get_room_status_enum(status: int) -> RoomStatus:
    if status == 1:
        return RoomStatus.WAITING
    elif status == 2:
        return RoomStatus.PLAYING
    elif status == 3:
        return RoomStatus.FINISHED
    return RoomStatus.WAITING


def build_room_response(room: OnlineRoom) -> RoomResponse:
    players = []
    for p in room.players:
        points = p.user.points if p.user else 0
        players.append(RoomPlayerSchema(
            player_id=str(p.user_id),
            name=p.player_name,
            is_host=p.is_host,
            is_ready=p.is_ready,
            points=points
        ))

    return RoomResponse(
        room_code=room.room_code,
        room_name=room.room_name or f"房间 {room.room_code}",
        max_players=room.max_player_count,
        players=players,
        status=get_room_status_enum(room.room_status),
        host_id=room.host_id
    )


@router.post(
    "/create",
    summary="创建房间",
    description="创建新的联机游戏房间（需要登录）",
    responses={
        200: {
            "model": ApiResponseModel[RoomResponse],
            "description": "成功响应"
        }
    }
)
async def create_room(
    request: CreateRoomRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"创建房间请求: user_id={user.id}, request={request}")
        
        room_code = generate_room_code(db)
        logger.info(f"生成房间码: {room_code}")

        room = OnlineRoom(
            room_code=room_code,
            room_name=request.room_name or f"房间 {room_code}",
            max_player_count=request.max_players,
            current_player_count=1,
            room_status=1,
            host_id=str(user.id)
        )

        room_player = RoomPlayer(
            room=room,
            user_id=user.id,
            player_name=user.nickname,
            is_host=True,
            is_ready=True
        )

        db.add(room)
        db.add(room_player)
        db.commit()
        db.refresh(room)
        logger.info(f"房间创建成功: room_id={room.id}")

        room_with_players = db.query(OnlineRoom).filter(
            OnlineRoom.id == room.id
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        return ApiResponse.success(
            data=build_room_response(room_with_players),
            msg="房间创建成功"
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"创建房间失败: {e}")
        return ApiResponse.error(msg=f"创建房间失败: {str(e)}", code=500)


@router.post(
    "/join",
    summary="加入房间",
    description="加入指定的联机房间（需要登录）",
    responses={
        200: {
            "model": ApiResponseModel[JoinRoomResponse],
            "description": "成功响应"
        }
    }
)
async def join_room(
    request: JoinRoomRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    room = db.query(OnlineRoom).filter(
        OnlineRoom.room_code == request.room_code,
        OnlineRoom.is_deleted == 0
    ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

    if not room:
        return ApiResponse.error(msg="房间不存在", code=404)

    if room.room_status != 1:
        return ApiResponse.error(msg="房间已开始游戏", code=409)

    if room.current_player_count >= room.max_player_count:
        return ApiResponse.error(msg="房间已满", code=400)

    existing_player = db.query(RoomPlayer).filter(
        RoomPlayer.room_id == room.id,
        RoomPlayer.user_id == user.id
    ).first()

    if existing_player:
        return ApiResponse.error(
            msg="你已在房间中",
            code=409,
            data={
                "room_code": room.room_code,
                "player_id": user.id,
                "room": build_room_response(room)
            }
        )

    player = RoomPlayer(
        room_id=room.id,
        user_id=user.id,
        player_name=user.nickname,
        is_host=False,
        is_ready=False
    )

    room.current_player_count += 1
    db.add(player)
    db.commit()
    db.refresh(room)

    room_with_players = db.query(OnlineRoom).filter(
        OnlineRoom.id == room.id
    ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

    await manager.broadcast(room_code, {
        "type": "room_updated",
        "data": build_room_response(room_with_players)
    })

    return ApiResponse.success(
        data=JoinRoomResponse(
            room=build_room_response(room_with_players),
            player_id=str(user.id)
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
async def leave_room(request: LeaveRoomRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        room = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == request.room_code,
            OnlineRoom.is_deleted == 0
        ).first()

        if not room:
            return ApiResponse.error(msg="房间不存在", code=404)

        player = db.query(RoomPlayer).filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.user_id == user.id
        ).first()

        if not player:
            return ApiResponse.error(msg="你不在这个房间", code=400)

        is_host = player.is_host
        db.delete(player)
        room.current_player_count -= 1

        if room.current_player_count == 0:
            room.is_deleted = 1
            db.commit()
            await manager.broadcast(room_code, {
                "type": "room_updated",
                "data": None
            })
            return ApiResponse.success(msg="离开房间成功")
        elif is_host:
            first_player = db.query(RoomPlayer).filter(
                RoomPlayer.room_id == room.id
            ).first()
            if first_player:
                first_player.is_host = True
                room.host_id = str(first_player.user_id)

        db.commit()

        room_after = db.query(OnlineRoom).filter(
            OnlineRoom.id == room.id
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        await manager.broadcast(room_code, {
            "type": "room_updated",
            "data": build_room_response(room_after)
        })

        return ApiResponse.success(msg="离开房间成功")
    except Exception as e:
        db.rollback()
        return ApiResponse.error(msg=f"服务器内部错误: {str(e)}", code=500)


@router.post(
    "/{room_code}/kick",
    summary="房主踢出玩家",
    description="房主将指定玩家移出房间",
    responses={
        200: {
            "model": ApiResponseModel[RoomResponse],
            "description": "成功响应"
        }
    }
)
async def kick_player(room_code: str, request: KickPlayerRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        room = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == room_code,
            OnlineRoom.is_deleted == 0
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        if not room:
            return ApiResponse.error(msg="房间不存在", code=404)

        if room.host_id != str(user.id):
            return ApiResponse.error(msg="只有房主才能踢人", code=403)

        if room.room_status != 1:
            return ApiResponse.error(msg="游戏已开始，无法踢人", code=409)

        target_player = db.query(RoomPlayer).filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.user_id == request.target_player_id
        ).first()

        if not target_player:
            return ApiResponse.error(msg="目标玩家不在房间中", code=404)

        if user.id == request.target_player_id:
            return ApiResponse.error(msg="房主不能踢自己", code=400)

        target_player_id_str = str(request.target_player_id)
        db.delete(target_player)
        room.current_player_count -= 1

        if room.current_player_count == 0:
            room.is_deleted = 1
            db.commit()
            await manager.broadcast(room_code, {
                "type": "room_updated",
                "data": None
            })
        else:
            db.commit()
            room_after = db.query(OnlineRoom).filter(
                OnlineRoom.id == room.id
            ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

            await manager.broadcast(room_code, {
                "type": "room_updated",
                "data": build_room_response(room_after)
            })

        await manager.send_personal_message(room_code, target_player_id_str, {
            "type": "player_kicked",
            "data": {
                "room_code": room_code,
                "player_id": request.target_player_id,
                "message": "你已被房主移出房间"
            }
        })

        if room.current_player_count > 0:
            room_after = db.query(OnlineRoom).filter(
                OnlineRoom.id == room.id
            ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()
            return ApiResponse.success(data=build_room_response(room_after), msg="踢出玩家成功")
        else:
            return ApiResponse.success(data=None, msg="踢出玩家成功")

    except Exception as e:
        db.rollback()
        return ApiResponse.error(msg=f"服务器内部错误: {str(e)}", code=500)


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
async def get_room_list(db: Session = Depends(get_db)):
    rooms = db.query(OnlineRoom).filter(
        OnlineRoom.room_status == 1,
        OnlineRoom.is_deleted == 0
    ).all()

    room_list = [
        RoomListItem(
            room_code=room.room_code,
            room_name=room.room_name or f"房间 {room.room_code}",
            player_count=room.current_player_count,
            max_players=room.max_player_count,
            status=get_room_status_enum(room.room_status)
        ) for room in rooms
    ]

    return ApiResponse.success(
        data=RoomListResponse(rooms=room_list),
        msg="获取成功"
    )


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
async def get_room(room_code: str, db: Session = Depends(get_db)):
    room = db.query(OnlineRoom).filter(
        OnlineRoom.room_code == room_code,
        OnlineRoom.is_deleted == 0
    ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

    if not room:
        return ApiResponse.error(msg="房间不存在", code=404)

    return ApiResponse.success(
        data=build_room_response(room),
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
async def start_game(room_code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = db.query(OnlineRoom).filter(
        OnlineRoom.room_code == room_code,
        OnlineRoom.is_deleted == 0
    ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

    if not room:
        return ApiResponse.error(msg="房间不存在", code=404)

    if room.host_id != str(user.id):
        return ApiResponse.error(msg="只有房主才能开始游戏", code=403)

    if room.room_status != 1:
        return ApiResponse.error(msg="房间已开始游戏", code=409)

    if room.current_player_count < 2:
        return ApiResponse.error(msg="至少需要2名玩家", code=400)

    # 构建玩家列表（包含用户ID，以便复用已存在的用户）
    players = []
    for p in room.players:
        players.append({
            "user_id": p.user_id,
            "player_name": p.player_name,
            "is_ai": False
        })
    
    game_data = GameManager.create_game("online", players)
    GameManager.start_game(game_data)
    game_dict = game_data.to_dict()
    game_id = game_dict["game_id"]
    game_data.close()

    room.room_status = 2
    room.game_id = int(game_id)
    db.commit()

    await manager.broadcast(room_code, {
        "type": "room_updated",
        "data": build_room_response(room)
    })

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
async def dissolve_room(room_code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = db.query(OnlineRoom).filter(
        OnlineRoom.room_code == room_code,
        OnlineRoom.is_deleted == 0
    ).first()

    if not room:
        return ApiResponse.error(msg="房间不存在", code=404)

    if room.host_id != str(user.id):
        return ApiResponse.error(msg="只有房主才能解散房间", code=403)

    room.is_deleted = 1
    db.commit()

    await manager.broadcast(room_code, {
        "type": "room_updated",
        "data": None
    })

    return ApiResponse.success(msg="房间已解散")


@router.post(
    "/{room_code}/ready",
    summary="玩家准备/取消准备",
    description="玩家设置准备状态，房主不能取消准备",
    responses={
        200: {
            "model": ApiResponseModel[RoomResponse],
            "description": "成功响应"
        }
    }
)
async def set_ready(room_code: str, request: ReadyRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        room = db.query(OnlineRoom).filter(
            OnlineRoom.room_code == room_code,
            OnlineRoom.is_deleted == 0
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        if not room:
            return ApiResponse.error(msg="房间不存在", code=404)

        if room.room_status != 1:
            return ApiResponse.error(msg="游戏已开始，无法更改准备状态", code=409)

        player = db.query(RoomPlayer).filter(
            RoomPlayer.room_id == room.id,
            RoomPlayer.user_id == user.id
        ).first()

        if not player:
            return ApiResponse.error(msg="你不在这个房间", code=404)

        if player.is_host and not request.is_ready:
            return ApiResponse.error(msg="房主不能取消准备", code=400)

        player.is_ready = request.is_ready
        db.commit()

        room_after = db.query(OnlineRoom).filter(
            OnlineRoom.id == room.id
        ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

        await manager.broadcast(room_code, {
            "type": "room_updated",
            "data": build_room_response(room_after)
        })

        return ApiResponse.success(data=build_room_response(room_after), msg="设置成功")

    except Exception as e:
        db.rollback()
        return ApiResponse.error(msg=f"服务器内部错误: {str(e)}", code=500)


@router.get(
    "/current",
    summary="获取当前房间",
    description="获取用户当前所在的房间（用于刷新/状态恢复）",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def get_current_room(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    player = db.query(RoomPlayer).filter(
        RoomPlayer.user_id == user.id
    ).first()

    if not player:
        return ApiResponse.success(data=None, msg="获取成功")

    room = db.query(OnlineRoom).filter(
        OnlineRoom.id == player.room_id,
        OnlineRoom.is_deleted == 0
    ).options(joinedload(OnlineRoom.players).joinedload(RoomPlayer.user)).first()

    if not room:
        return ApiResponse.success(data=None, msg="获取成功")

    return ApiResponse.success(
        data={
            "room": build_room_response(room),
            "playerId": user.id
        },
        msg="获取成功"
    )