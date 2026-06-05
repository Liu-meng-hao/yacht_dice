from pydantic import BaseModel, Field
from typing import Optional, List


class UpdateWinsRequest(BaseModel):
    """更新胜利次数请求模型"""
    winner_id: int = Field(..., description="胜利玩家ID")
    game_mode: str = Field(..., description="游戏模式：local（本地）、ai（AI对战）、online（联机对战）")


class UpdateWinsResponse(BaseModel):
    """更新胜利次数响应模型"""
    user_id: int
    total_wins: int
    message: str


class LeaderboardItem(BaseModel):
    """排行榜项模型"""
    rank: int
    user_id: int
    nickname: Optional[str] = None
    total_wins: int


class UpdateGamesRequest(BaseModel):
    """更新总对局次数请求模型"""
    winner_id: int = Field(..., description="胜利玩家ID")
    game_mode: str = Field(..., description="游戏模式：local（本地）、ai（AI对战）、online（联机对战）")
    last_play_time: Optional[str] = Field(None, description="最后一次获胜时间（ISO格式字符串，如：2024-01-01T12:00:00）")


class UpdateGamesResponse(BaseModel):
    """更新总对局次数响应模型"""
    user_id: int
    total_games: int
    message: str


class TotalGamesLeaderboardItem(BaseModel):
    """总对局次数排行榜项模型"""
    rank: int
    user_id: int
    nickname: Optional[str] = None
    total_games: int
    last_play_time: Optional[str] = None  # 最后一次获胜时间


class TotalGamesLeaderboardResponse(BaseModel):
    """总对局次数排行榜响应模型"""
    leaderboard: List[TotalGamesLeaderboardItem]
    total_count: int


class LeaderboardResponse(BaseModel):
    """排行榜响应模型"""
    leaderboard: List[LeaderboardItem]
    total_count: int