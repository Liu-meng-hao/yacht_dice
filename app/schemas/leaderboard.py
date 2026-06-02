from pydantic import BaseModel, Field
from typing import Optional, List


class UpdateWinsRequest(BaseModel):
    """更新胜利次数请求模型"""
    winner_id: int = Field(..., description="胜利玩家ID")


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


class LeaderboardResponse(BaseModel):
    """排行榜响应模型"""
    leaderboard: List[LeaderboardItem]
    total_count: int