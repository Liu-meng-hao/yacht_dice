from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class GameMode(str, Enum):
    LOCAL = "local"
    AI = "ai"
    ONLINE = "online"


class RoomStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


class CreateGameRequest(BaseModel):
    game_mode: GameMode
    player_names: List[str]


class DiceRollRequest(BaseModel):
    game_id: str
    player_id: str
    locked_dice: List[int] = []


class ScoreSubmitRequest(BaseModel):
    game_id: str
    player_id: str
    category: str


class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = None
    max_players: int = 4
    game_mode: GameMode = GameMode.ONLINE


class JoinRoomRequest(BaseModel):
    room_code: str
    player_name: str


class RoomResponse(BaseModel):
    room_code: str
    room_name: str
    max_players: int
    players: List[Dict[str, Any]]
    status: RoomStatus
    is_host: bool = False


class GameStateResponse(BaseModel):
    game_id: str
    game_mode: GameMode
    current_player: Optional[str]
    players: List[Dict[str, Any]]
    dice: List[int]
    rolls_left: int
    scores: Dict[str, Dict[str, Optional[int]]]
    status: str


class GameRecordResponse(BaseModel):
    id: int
    game_id: str
    game_mode: GameMode
    players: List[Dict[str, Any]]
    scores: Dict[str, Dict[str, Optional[int]]]
    winner: Optional[str]
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    
    class Config:
        from_attributes = True
