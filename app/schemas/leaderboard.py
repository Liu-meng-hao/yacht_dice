from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HighestScoreItem(BaseModel):
    """单局最高分排行榜项"""
    rank: int
    user_id: int
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    score: int
    achieve_time: Optional[datetime] = None


class HighestScoreResponse(BaseModel):
    """单局最高分排行榜响应"""
    leaderboard: List[HighestScoreItem]
    total_count: int


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
    avatar: Optional[str] = None
    total_games: int
    last_play_time: Optional[datetime] = None


class TotalGamesLeaderboardResponse(BaseModel):
    """总对局次数排行榜响应模型"""
    leaderboard: List[TotalGamesLeaderboardItem]
    total_count: int


class ExperienceItem(BaseModel):
    """经验值排行榜项"""
    rank: int
    user_id: int
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    experience: int
    achieve_time: Optional[datetime] = None


class ExperienceResponse(BaseModel):
    """经验值排行榜响应"""
    leaderboard: List[ExperienceItem]
    total_count: int


class WinStreakItem(BaseModel):
    """连胜排行榜项"""
    rank: int
    user_id: int
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    streak: int
    achieve_time: Optional[datetime] = None


class WinStreakResponse(BaseModel):
    """连胜排行榜响应"""
    leaderboard: List[WinStreakItem]
    total_count: int


class AddExperienceRequest(BaseModel):
    """增加经验值请求"""
    user_id: int = Field(..., description="玩家ID")
    score_item_id: Optional[int] = Field(None, description="计分项ID")
    experience_value: Optional[int] = Field(None, description="直接指定要增加的经验值")


class UpdateWinStreakRequest(BaseModel):
    """更新连胜状态请求"""
    user_id: int = Field(..., description="玩家ID")
    is_win: bool = Field(..., description="是否胜利")


class GamePlayerSettle(BaseModel):
    """游戏单个玩家结算信息"""
    user_id: int = Field(..., description="玩家ID")
    rank: int = Field(..., description="排名，从1开始")
    total_score: int = Field(..., description="总得分")


class GameSettleRequest(BaseModel):
    """游戏结束结算请求"""
    game_id: int = Field(..., description="游戏ID")
    game_mode: int = Field(..., description="游戏模式：1-本地，2-人机，3-联机")
    players: List[GamePlayerSettle] = Field(..., description="所有玩家结算信息列表")


class GameSettlePlayerResult(BaseModel):
    """单个玩家的结算结果"""
    user_id: int
    rank: int
    base_experience: int = 0
    rank_reward: int = 0
    score_bonus: int = 0
    streak_bonus: float = 0
    mode_multiplier: float = 1.0
    total_experience: int = 0
    old_experience: int = 0
    new_experience: int = 0
    win_streak_updated: bool = False
    old_streak: int = 0
    new_streak: int = 0


class GameSettleResponse(BaseModel):
    """游戏结算响应"""
    game_id: int
    results: List[GameSettlePlayerResult]
