from pydantic import BaseModel, Field
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


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"


# ========================================
# 首页模块 Schemas
# ========================================

class SoundSettingsUpdate(BaseModel):
    sound_enabled: bool = Field(description="音效开关")


class SoundSettingsResponse(BaseModel):
    sound_enabled: bool = Field(description="音效开关状态")


class RuleCategory(BaseModel):
    name: str = Field(description="计分项名称")
    description: str = Field(description="计分项说明")


class GameRulesResponse(BaseModel):
    rules: str = Field(description="游戏规则说明")
    categories: List[RuleCategory] = Field(description="13个计分项列表")


# ========================================
# 房间模块 Schemas
# ========================================

class CreateRoomRequest(BaseModel):
    player_name: str = Field(description="玩家名称")
    room_name: Optional[str] = Field(default=None, description="房间名称（可选）")
    max_players: int = Field(default=4, ge=2, le=4, description="最大玩家数（2-4）")
    game_mode: GameMode = Field(default=GameMode.ONLINE, description="游戏模式")


class JoinRoomRequest(BaseModel):
    room_code: str = Field(description="房间号")
    player_name: str = Field(description="玩家名称")


class LeaveRoomRequest(BaseModel):
    room_code: str = Field(description="房间号")
    player_id: str = Field(description="玩家ID")


class StartGameRequest(BaseModel):
    player_id: str = Field(description="房主ID")


class DissolveRoomRequest(BaseModel):
    player_id: str = Field(description="房主ID")


class RoomPlayer(BaseModel):
    player_id: str = Field(description="玩家ID")
    name: str = Field(description="玩家名称")
    is_host: bool = Field(description="是否为房主")


class RoomResponse(BaseModel):
    room_code: str = Field(description="房间号")
    room_name: str = Field(description="房间名称")
    max_players: int = Field(description="最大玩家数")
    players: List[RoomPlayer] = Field(description="玩家列表")
    status: RoomStatus = Field(description="房间状态")
    host_id: Optional[str] = Field(default=None, description="房主ID")


class RoomListItem(BaseModel):
    room_code: str = Field(description="房间号")
    room_name: str = Field(description="房间名称")
    player_count: int = Field(description="当前玩家数")
    max_players: int = Field(description="最大玩家数")
    status: RoomStatus = Field(description="房间状态")


class RoomListResponse(BaseModel):
    rooms: List[RoomListItem] = Field(description="房间列表")


class JoinRoomResponse(BaseModel):
    room: RoomResponse = Field(description="房间信息")
    player_id: str = Field(description="你的玩家ID")


class StartGameResponse(BaseModel):
    game_id: str = Field(description="游戏ID")
    room_code: str = Field(description="房间号")


# ========================================
# 游戏模块 Schemas
# ========================================

class CreateGameRequest(BaseModel):
    game_mode: GameMode = Field(description="游戏模式")
    player_names: List[str] = Field(description="玩家名称列表")


class DiceRollRequest(BaseModel):
    player_id: str = Field(description="玩家ID")
    locked_dice: List[int] = Field(default_factory=list, description="要锁定的骰子索引（0-4）")


class DiceResetRequest(BaseModel):
    player_id: str = Field(description="玩家ID")


class DiceToggleRequest(BaseModel):
    player_id: str = Field(description="玩家ID")
    dice_index: int = Field(ge=0, le=4, description="骰子索引（0-4）")


class ScoreSubmitRequest(BaseModel):
    player_id: str = Field(description="玩家ID")
    category: str = Field(description="计分项名称")


class QuitGameRequest(BaseModel):
    player_id: str = Field(description="玩家ID")


class GamePlayer(BaseModel):
    player_id: str = Field(description="玩家ID")
    name: str = Field(description="玩家名称")
    is_ai: bool = Field(description="是否为AI")
    scores: Dict[str, Optional[int]] = Field(description="各计分项得分")
    total_score: int = Field(description="总分")


class GameStateResponse(BaseModel):
    game_id: str = Field(description="游戏ID")
    game_mode: GameMode = Field(description="游戏模式")
    current_player: Optional[str] = Field(description="当前操作玩家ID")
    players: List[GamePlayer] = Field(description="玩家列表")
    dice: List[int] = Field(description="骰子点数（5个）")
    dice_locked: List[bool] = Field(description="骰子锁定状态")
    rolls_left: int = Field(description="剩余掷骰次数")
    status: GameStatus = Field(description="游戏状态")
    created_at: str = Field(description="创建时间")
    finished_at: Optional[str] = Field(default=None, description="结束时间")


class DiceRollResponse(BaseModel):
    dice: List[int] = Field(description="骰子点数")
    dice_locked: List[bool] = Field(description="骰子锁定状态")
    rolls_left: int = Field(description="剩余掷骰次数")


class DiceToggleResponse(BaseModel):
    dice_locked: List[bool] = Field(description="骰子锁定状态")


class ScoreSubmitResponse(BaseModel):
    category: str = Field(description="计分项")
    score: int = Field(description="得分")
    game_state: GameStateResponse = Field(description="游戏状态")
    next_player: Optional[str] = Field(description="下一玩家ID")
    is_game_finished: bool = Field(description="游戏是否结束")


# ========================================
# 计分模块 Schemas
# ========================================

class PossibleScoresResponse(BaseModel):
    possible_scores: Dict[str, Optional[int]] = Field(description="各计分项的可能得分")


class ScoreHistoryItem(BaseModel):
    game_id: str = Field(description="游戏ID")
    game_mode: GameMode = Field(description="游戏模式")
    played_at: str = Field(description="游戏时间")
    players: List[GamePlayer] = Field(description="玩家列表")
    winner: Optional[str] = Field(description="赢家")
    final_scores: Dict[str, int] = Field(description="最终得分")


class ScoreHistoryRequest(BaseModel):
    player_id: str = Field(description="玩家ID")
    limit: int = Field(default=10, ge=1, le=50, description="查询数量（1-50）")


class ScoreHistoryResponse(BaseModel):
    history: List[ScoreHistoryItem] = Field(description="历史记录列表")


class LeaderboardItem(BaseModel):
    rank: int = Field(description="排名")
    player_name: str = Field(description="玩家名称")
    total_games: int = Field(description="总游戏数")
    wins: int = Field(description="胜利数")
    best_score: int = Field(description="最高分")


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardItem] = Field(description="排行榜")


class PlayerPanelItem(BaseModel):
    player_id: str = Field(description="玩家ID")
    username: str = Field(description="玩家昵称")
    avatar: str = Field(description="玩家头像URL")
    player_order: int = Field(description="操作顺序1-2")


class InitScorePanelResponse(BaseModel):
    game_id: str = Field(description="对局ID")
    players: List[PlayerPanelItem] = Field(description="玩家静态信息列表")


class LockedItem(BaseModel):
    item_id: int = Field(description="计分项ID")
    score_value: int = Field(description="已提交的分数")


class GetLockStatusResponse(BaseModel):
    player_id: str = Field(description="玩家ID")
    locked_items: List[LockedItem] = Field(description="已锁定（已提交）的计分项列表")
    unlocked_items: List[int] = Field(description="未锁定（未提交）的计分项ID列表")


class SubmitScoreRequest(BaseModel):
    player_id: int = Field(description="提交计分的玩家ID")
    score_item_id: int = Field(description="计分项ID，1-6或8-14，7奖励分不可直接提交")
    score_value: int = Field(description="本次得分")
    dice_data: List[int] = Field(description="当前5颗骰子结果")
    round_number: int = Field(description="当前回合数1-13")


class SubmitScoreResponse(BaseModel):
    submit_success: bool = Field(description="是否提交成功")
    player_id: int = Field(description="玩家ID")
    score_item_id: int = Field(description="已提交计分项ID")
    score_value: int = Field(description="实际得分")
    total_score: int = Field(description="更新后累计总分")
    upper_score: int = Field(description="更新后上半区得分")
    lower_score: int = Field(description="更新后下半区得分")
    bonus_score: int = Field(description="更新后奖励分")
    game_status: int = Field(description="更新后对局状态，1准备 2进行 3结束 4退出")
    next_player_id: Optional[int] = Field(description="下一位操作玩家ID，game_status=2时返回")


# ========================================
# 结算模块 Schemas
# ========================================

class SettlementPlayer(BaseModel):
    player_id: str = Field(description="玩家ID")
    name: str = Field(description="玩家名称")
    final_score: int = Field(description="最终得分")
    rank: int = Field(description="排名")
    is_winner: bool = Field(description="是否为赢家")
    scores: Dict[str, Optional[int]] = Field(description="各计分项得分")


class SettlementResponse(BaseModel):
    game_id: str = Field(description="游戏ID")
    finished_at: str = Field(description="结束时间")
    players: List[SettlementPlayer] = Field(description="玩家结算信息")


class RematchRequest(BaseModel):
    player_id: str = Field(description="玩家ID")


class RematchResponse(BaseModel):
    new_game_id: str = Field(description="新游戏ID")
    game_state: GameStateResponse = Field(description="新游戏状态")


class BackToHomeRequest(BaseModel):
    player_id: str = Field(description="玩家ID")


class FinalRankingPlayer(BaseModel):
    rank: int = Field(description="名次，1开始")
    player_id: str = Field(description="玩家ID")
    username: str = Field(description="玩家昵称")
    avatar: str = Field(description="玩家头像URL")
    total_score: int = Field(description="累计总分")


class FinalRankingResponse(BaseModel):
    ranking_list: List[FinalRankingPlayer] = Field(description="最终排名列表，按total_score降序")


class ScoreSummaryResponse(BaseModel):
    player_id: str = Field(description="玩家ID")
    upper_score: int = Field(description="上层数字区得分")
    upper_bonus: int = Field(description="上层达标奖励")
    upper_subtotal: int = Field(description="上层小计")
    lower_score: int = Field(description="下层组合区得分")
    yahtzee_bonus: int = Field(description="重复快艇奖励分")
    total_score: int = Field(description="总分")


class GameHighlightsResponse(BaseModel):
    yahtzee_count: int = Field(description="快艇次数")
    highest_round_score: int = Field(description="最高单回合得分")
    upper_bonus_scored: int = Field(description="上半区奖励是否获得（0/1）")
