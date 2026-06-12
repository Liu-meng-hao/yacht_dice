from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.db.session import get_db
from app.models.user import User
from app.models.game_player import GamePlayer
from app.models.game import Game
from app.models.score_item import ScoreItem
from app.schemas.leaderboard import (
    HighestScoreResponse, HighestScoreItem,
    ExperienceResponse, ExperienceItem,
    WinStreakResponse, WinStreakItem,
    AddExperienceRequest,
    UpdateWinStreakRequest,
    GameSettleRequest,
    GameSettlePlayerResult,
    GameSettleResponse,
    UpdateGamesRequest,
    UpdateGamesResponse,
    TotalGamesLeaderboardResponse,
    TotalGamesLeaderboardItem,
    WinRateResponse,
    WinRateItem
)
from app.core.dependencies import get_current_user
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple

router = APIRouter()

# 导入Redis相关
from app.db.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Redis缓存配置
CACHE_TTL = 300  # 5分钟缓存
CACHE_KEY_HIGHEST_SCORE = "leaderboard:highest_score"
CACHE_KEY_EXPERIENCE = "leaderboard:experience"
CACHE_KEY_WIN_STREAK = "leaderboard:win_streak"
CACHE_KEY_TOTAL_GAMES = "leaderboard:total_games"
CACHE_KEY_WIN_RATE = "leaderboard:win_rate"

# 游戏模式系数配置
GAME_MODE_MULTIPLIER = {
    1: 1.0,  # 本地模式
    2: 1.2,  # 人机对战
    3: 1.5   # 联机对战
}

# 排名奖励配置 (玩家数 -> 排名 -> 奖励)
RANK_REWARDS = {
    2: {1: 30, 2: 10},
    3: {1: 50, 2: 25, 3: 10},
    4: {1: 80, 2: 40, 3: 20, 4: 10}
}

# 安全限制配置
MAX_EXPERIENCE = 1_000_000_000  # 最大经验值 10亿
MAX_WIN_STREAK = 1000  # 最大连胜数
MIN_PLAYERS = 2
MAX_PLAYERS = 4


@router.get(
    "/highest-score",
    summary="获取单局历史最高得分排行榜",
    description="获取玩家单局游戏最高分排行榜"
)
async def get_highest_score_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取单局历史最高得分排行榜接口"""
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    # 尝试从Redis缓存获取
    redis_client = get_redis_client()
    cache_key = f"{CACHE_KEY_HIGHEST_SCORE}:{limit}"
    
    if redis_client and redis_client.get_client():
        cached = redis_client.get_client().get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                logger.info(f"命中缓存: {cache_key}")
                return JSONResponse(
                    content={"code": 200, "msg": "获取排行榜成功", "data": cached_data},
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"缓存解析失败: {e}")
    
    # 查询每个玩家的最高得分
    subquery = db.query(
        GamePlayer.user_id,
        func.max(GamePlayer.total_score).label('max_score')
    ).join(
        Game, Game.id == GamePlayer.game_id
    ).filter(
        Game.game_status == 3,
        Game.is_deleted == 0,
        GamePlayer.is_ai == 0
    ).group_by(
        GamePlayer.user_id
    ).subquery()
    
    leaderboard_data = db.query(
        User.id,
        User.nickname,
        User.avatar,
        subquery.c.max_score,
        Game.end_time
    ).join(
        subquery, User.id == subquery.c.user_id
    ).join(
        GamePlayer,
        (GamePlayer.user_id == subquery.c.user_id) & (GamePlayer.total_score == subquery.c.max_score)
    ).join(
        Game, Game.id == GamePlayer.game_id
    ).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).order_by(
        desc(subquery.c.max_score)
    ).limit(limit).all()
    
    leaderboard = []
    seen_user_ids = set()
    
    for rank, (user_id, nickname, avatar, score, achieve_time) in enumerate(leaderboard_data, 1):
        if user_id in seen_user_ids:
            continue
        seen_user_ids.add(user_id)
        
        leaderboard.append({
            "rank": rank,
            "user_id": user_id,
            "nickname": nickname,
            "avatar": avatar,
            "score": score,
            "achieve_time": achieve_time.isoformat() if achieve_time else None
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).count()
    
    result = {"leaderboard": leaderboard, "total_count": total_count}
    
    if redis_client and redis_client.get_client():
        try:
            redis_client.get_client().setex(
                cache_key, CACHE_TTL, json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"缓存已更新: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    return JSONResponse(
        content={"code": 200, "msg": "获取排行榜成功", "data": result},
        media_type="application/json"
    )


@router.get(
    "/win-rate",
    summary="获取胜率排行榜",
    description="获取胜率排行榜（要求总对局数 >= 10，仅统计非本地模式）"
)
async def get_win_rate_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取胜率排行榜接口"""
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    # 尝试从Redis缓存获取
    redis_client = get_redis_client()
    cache_key = f"{CACHE_KEY_WIN_RATE}:{limit}"
    
    if redis_client and redis_client.get_client():
        cached = redis_client.get_client().get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                logger.info(f"命中缓存: {cache_key}")
                return JSONResponse(
                    content={"code": 200, "msg": "获取排行榜成功", "data": cached_data},
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"缓存解析失败: {e}")
    
    # 查询胜率排行榜
    # 门槛：总对局数 >= 10
    # 排序：胜率降序，总局数降序，最后游戏时间降序
    users = db.query(
        User,
        (func.cast(User.total_wins, func.Float) / func.nullif(User.total_games, 0) * 100).label('win_rate')
    ).filter(
        User.is_deleted == 0,
        User.user_type == 1,
        User.total_games >= 10
    ).order_by(
        desc('win_rate'),
        desc(User.total_games),
        desc(User.last_play_time)
    ).limit(limit).all()
    
    leaderboard = []
    for rank, (user, win_rate) in enumerate(users, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "total_games": user.total_games,
            "total_wins": user.total_wins,
            "win_rate": round(win_rate, 2) if win_rate is not None else 0.0,
            "last_play_time": user.last_play_time.isoformat() if user.last_play_time else None
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1,
        User.total_games >= 10
    ).count()
    
    result = {"leaderboard": leaderboard, "total_count": total_count}
    
    if redis_client and redis_client.get_client():
        try:
            redis_client.get_client().setex(
                cache_key, CACHE_TTL, json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"缓存已更新: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    return JSONResponse(
        content={"code": 200, "msg": "获取排行榜成功", "data": result},
        media_type="application/json"
    )


@router.get(
    "/experience",
    summary="获取经验值排行榜",
    description="获取玩家经验值排行榜"
)
async def get_experience_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取经验值排行榜接口"""
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    # 尝试从Redis缓存获取
    redis_client = get_redis_client()
    cache_key = f"{CACHE_KEY_EXPERIENCE}:{limit}"
    
    if redis_client and redis_client.get_client():
        cached = redis_client.get_client().get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                logger.info(f"命中缓存: {cache_key}")
                return JSONResponse(
                    content={"code": 200, "msg": "获取排行榜成功", "data": cached_data},
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"缓存解析失败: {e}")
    
    # 查询经验值排行榜
    users = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).order_by(
        desc(User.total_experience)
    ).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "experience": user.total_experience,
            "achieve_time": user.last_play_time.isoformat() if user.last_play_time else None
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).count()
    
    result = {"leaderboard": leaderboard, "total_count": total_count}
    
    if redis_client and redis_client.get_client():
        try:
            redis_client.get_client().setex(
                cache_key, CACHE_TTL, json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"缓存已更新: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    return JSONResponse(
        content={"code": 200, "msg": "获取排行榜成功", "data": result},
        media_type="application/json"
    )


@router.get(
    "/win-streak",
    summary="获取连胜排行榜",
    description="获取玩家连胜排行榜"
)
async def get_win_streak_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取连胜排行榜接口"""
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    # 尝试从Redis缓存获取
    redis_client = get_redis_client()
    cache_key = f"{CACHE_KEY_WIN_STREAK}:{limit}"
    
    if redis_client and redis_client.get_client():
        cached = redis_client.get_client().get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                logger.info(f"命中缓存: {cache_key}")
                return JSONResponse(
                    content={"code": 200, "msg": "获取排行榜成功", "data": cached_data},
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"缓存解析失败: {e}")
    
    # 查询连胜排行榜
    users = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).order_by(
        desc(User.max_win_streak)
    ).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "streak": user.max_win_streak,
            "achieve_time": user.max_win_streak_time.isoformat() if user.max_win_streak_time else None
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).count()
    
    result = {"leaderboard": leaderboard, "total_count": total_count}
    
    if redis_client and redis_client.get_client():
        try:
            redis_client.get_client().setex(
                cache_key, CACHE_TTL, json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"缓存已更新: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    return JSONResponse(
        content={"code": 200, "msg": "获取排行榜成功", "data": result},
        media_type="application/json"
    )


@router.get(
    "/ranking-games",
    summary="获取总对局次数排行榜",
    description="获取按照total_games降序排列的用户排行榜（包含最后游戏时间）"
)
async def get_ranking_games_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取总对局次数排行榜接口"""
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    # 尝试从Redis缓存获取
    redis_client = get_redis_client()
    cache_key = f"{CACHE_KEY_TOTAL_GAMES}:{limit}"
    
    if redis_client and redis_client.get_client():
        cached = redis_client.get_client().get(cache_key)
        if cached:
            try:
                cached_data = json.loads(cached)
                logger.info(f"命中缓存: {cache_key}")
                return JSONResponse(
                    content={"code": 200, "msg": "获取排行榜成功", "data": cached_data},
                    media_type="application/json"
                )
            except Exception as e:
                logger.warning(f"缓存解析失败: {e}")
    
    # 查询总对局次数排行榜
    users = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).order_by(
        desc(User.total_games)
    ).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, 1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "total_games": user.total_games,
            "last_play_time": user.last_play_time.isoformat() if user.last_play_time else None
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).count()
    
    result = {"leaderboard": leaderboard, "total_count": total_count}
    
    if redis_client and redis_client.get_client():
        try:
            redis_client.get_client().setex(
                cache_key, CACHE_TTL, json.dumps(result, ensure_ascii=False)
            )
            logger.info(f"缓存已更新: {cache_key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    return JSONResponse(
        content={"code": 200, "msg": "获取排行榜成功", "data": result},
        media_type="application/json"
    )


@router.post(
    "/add-experience",
    summary="增加玩家经验值",
    description="根据计分项或直接指定增加玩家经验值"
)
async def add_experience(
    request: AddExperienceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """增加玩家经验值接口"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user or user.is_deleted:
        return JSONResponse(
            content={"code": 404, "msg": "用户不存在", "data": None},
            media_type="application/json"
        )
    
    # 确定要增加的经验值
    added_exp = 0
    
    if request.experience_value is not None:
        # 直接指定经验值
        added_exp = request.experience_value
    elif request.score_item_id is not None:
        # 根据计分项获取经验值
        score_item = db.query(ScoreItem).filter(ScoreItem.id == request.score_item_id).first()
        if not score_item:
            return JSONResponse(
                content={"code": 404, "msg": "计分项不存在", "data": None},
                media_type="application/json"
            )
        added_exp = score_item.experience_value
    else:
        return JSONResponse(
            content={"code": 400, "msg": "必须提供score_item_id或experience_value", "data": None},
            media_type="application/json"
        )
    
    # 验证经验值不能为负数
    if added_exp < 0:
        return JSONResponse(
            content={"code": 400, "msg": "经验值不能为负数", "data": None},
            media_type="application/json"
        )
    
    # 计算新的经验值，不能超过上限
    new_experience = min(user.total_experience + added_exp, MAX_EXPERIENCE)
    actual_added = new_experience - user.total_experience
    
    # 增加经验值
    user.total_experience = new_experience
    user.last_play_time = datetime.now()
    db.commit()
    db.refresh(user)
    
    # 清除排行榜缓存
    redis_client = get_redis_client()
    if redis_client and redis_client.get_client():
        try:
            keys_to_delete = []
            for key in redis_client.get_client().scan_iter(f"{CACHE_KEY_EXPERIENCE}:*"):
                keys_to_delete.append(key)
            if keys_to_delete:
                redis_client.get_client().delete(*keys_to_delete)
            logger.info("经验值排行榜缓存已清除")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")
    
    return JSONResponse(
        content={
            "code": 200,
            "msg": "经验值增加成功",
            "data": {
                "user_id": user.id,
                "added_experience": actual_added,
                "total_experience": user.total_experience
            }
        },
        media_type="application/json"
    )


@router.post(
    "/update-win-streak",
    summary="更新玩家连胜状态",
    description="游戏结束时更新玩家的连胜状态"
)
async def update_win_streak(
    request: UpdateWinStreakRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新玩家连胜状态接口"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user or user.is_deleted:
        return JSONResponse(
            content={"code": 404, "msg": "用户不存在", "data": None},
            media_type="application/json"
        )
    
    if request.is_win:
        # 胜利，增加当前连胜，但不超过上限
        user.current_win_streak = min(user.current_win_streak + 1, MAX_WIN_STREAK)
        
        # 检查是否刷新最大连胜记录
        if user.current_win_streak > user.max_win_streak:
            user.max_win_streak = user.current_win_streak
            user.max_win_streak_time = datetime.now()
    else:
        # 失败，重置当前连胜
        user.current_win_streak = 0
    
    user.last_play_time = datetime.now()
    db.commit()
    db.refresh(user)
    
    # 清除排行榜缓存
    redis_client = get_redis_client()
    if redis_client and redis_client.get_client():
        try:
            keys_to_delete = []
            for key in redis_client.get_client().scan_iter(f"{CACHE_KEY_WIN_STREAK}:*"):
                keys_to_delete.append(key)
            if keys_to_delete:
                redis_client.get_client().delete(*keys_to_delete)
            logger.info("连胜排行榜缓存已清除")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")
    
    return JSONResponse(
        content={
            "code": 200,
            "msg": "连胜状态更新成功",
            "data": {
                "user_id": user.id,
                "is_win": request.is_win,
                "current_win_streak": user.current_win_streak,
                "max_win_streak": user.max_win_streak
            }
        },
        media_type="application/json"
    )


@router.post(
    "/update-games",
    summary="更新总对局次数",
    description="游戏结束时，更新胜利玩家的total_games字段和last_play_time（任何游戏模式都生效）"
)
async def update_games(
    request: UpdateGamesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新总对局次数接口
    
    - **winner_id**: 胜利玩家的ID
    - **game_mode**: 游戏模式：local（本地）、ai（AI对战）、online（联机对战）
    - **last_play_time**: 最后一次获胜时间（ISO格式字符串）
    """
    # 验证游戏模式参数
    valid_game_modes = ["local", "ai", "online"]
    if request.game_mode not in valid_game_modes:
        return JSONResponse(
            content={"code": 400, "msg": f"无效的游戏模式，有效值: {valid_game_modes}", "data": None},
            media_type="application/json"
        )
    
    user = db.query(User).filter(User.id == request.winner_id).first()
    if not user:
        return JSONResponse(
            content={"code": 404, "msg": "用户不存在", "data": None},
            media_type="application/json"
        )
    
    # 仅非本地模式更新统计数据（胜率排行榜相关）
    if request.game_mode != "local":
        user.total_games = (user.total_games or 0) + 1
        user.total_wins = (user.total_wins or 0) + 1
    
    # 更新最后游戏时间（所有模式都更新）
    if request.last_play_time:
        try:
            # 解析 ISO 格式的时间字符串
            user.last_play_time = datetime.fromisoformat(request.last_play_time.replace("Z", "+00:00"))
        except ValueError:
            return JSONResponse(
                content={"code": 400, "msg": "无效的时间格式，请使用ISO格式（如：2024-01-01T12:00:00）", "data": None},
                media_type="application/json"
            )
    
    db.commit()
    db.refresh(user)
    
    # 清除总对局次数排行榜和胜率排行榜缓存
    redis_client = get_redis_client()
    if redis_client and redis_client.get_client():
        try:
            keys_to_delete = []
            # 清除对局数排行榜缓存
            for key in redis_client.get_client().scan_iter(f"{CACHE_KEY_TOTAL_GAMES}:*"):
                keys_to_delete.append(key)
            # 清除胜率排行榜缓存
            for key in redis_client.get_client().scan_iter(f"{CACHE_KEY_WIN_RATE}:*"):
                keys_to_delete.append(key)
            
            if keys_to_delete:
                redis_client.get_client().delete(*keys_to_delete)
            logger.info("相关排行榜缓存已清除")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")
    
    return JSONResponse(
        content={
            "code": 200,
            "msg": "总对局次数更新成功",
            "data": {
                "user_id": user.id,
                "total_games": user.total_games,
                "last_play_time": user.last_play_time.isoformat() if user.last_play_time else None,
                "message": "总对局次数更新成功"
            }
        },
        media_type="application/json"
    )


# ==================== 游戏结算接口 ====================

def calculate_rank_reward(player_count: int, rank: int) -> int:
    """根据人数和排名计算奖励"""
    rewards = RANK_REWARDS.get(player_count, {})
    return rewards.get(rank, 0)


def calculate_streak_bonus(current_streak: int) -> float:
    """计算连胜加成"""
    # 连胜数 ×5%，最多50%
    bonus = min(current_streak * 0.05, 0.5)
    return bonus


def calculate_score_bonus(total_score: int) -> int:
    """计算得分加成：每10分+1经验"""
    return total_score // 10


@router.post(
    "/game-settle",
    summary="游戏结束结算",
    description="游戏结束时统一结算所有玩家经验和连胜"
)
async def game_settle(
    request: GameSettleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """游戏结算接口"""
    player_count = len(request.players)
    results = []
    
    # 1. 验证玩家数在合法范围内
    if player_count < MIN_PLAYERS or player_count > MAX_PLAYERS:
        return JSONResponse(
            content={"code": 400, "msg": f"玩家数必须在 {MIN_PLAYERS}-{MAX_PLAYERS} 之间", "data": None},
            media_type="application/json"
        )
    
    # 2. 验证游戏是否存在且状态正确
    game = db.query(Game).filter(Game.id == request.game_id).first()
    if not game:
        return JSONResponse(
            content={"code": 404, "msg": "游戏不存在", "data": None},
            media_type="application/json"
        )
    if game.is_deleted:
        return JSONResponse(
            content={"code": 400, "msg": "游戏已删除", "data": None},
            media_type="application/json"
        )
    
    # 3. 验证请求的 game_mode 与数据库一致
    if request.game_mode != game.game_mode:
        return JSONResponse(
            content={"code": 400, "msg": f"游戏模式不匹配，实际为 {game.game_mode}", "data": None},
            media_type="application/json"
        )
    
    # 4. 验证游戏是否已结束
    if game.game_status != 3:
        return JSONResponse(
            content={"code": 400, "msg": "游戏未结束，无法结算", "data": None},
            media_type="application/json"
        )
    
    # 5. 验证所有玩家的 rank 合法
    ranks = set()
    for player in request.players:
        if player.rank < 1 or player.rank > player_count:
            return JSONResponse(
                content={"code": 400, "msg": f"rank 必须在 1-{player_count} 之间", "data": None},
                media_type="application/json"
            )
        if player.rank in ranks:
            return JSONResponse(
                content={"code": 400, "msg": "rank 不能重复", "data": None},
                media_type="application/json"
            )
        ranks.add(player.rank)
    
    # 6. 验证所有玩家是否参与了该游戏
    game_player_ids = set()
    game_players = db.query(GamePlayer).filter(GamePlayer.game_id == request.game_id).all()
    for gp in game_players:
        game_player_ids.add(gp.user_id)
    
    for player in request.players:
        if player.user_id not in game_player_ids:
            return JSONResponse(
                content={"code": 400, "msg": f"玩家 {player.user_id} 未参与该游戏", "data": None},
                media_type="application/json"
            )
    
    # 获取游戏模式系数（使用数据库中的）
    mode_multiplier = GAME_MODE_MULTIPLIER.get(game.game_mode, 1.0)
    
    # 按rank排序，确保第1名是胜者
    sorted_players = sorted(request.players, key=lambda p: p.rank)
    
    for player_settle in sorted_players:
        # 获取用户
        user = db.query(User).filter(User.id == player_settle.user_id).first()
        if not user or user.is_deleted:
            continue
        
        # 记录旧状态
        old_experience = user.total_experience
        old_streak = user.current_win_streak
        
        # 判断是否胜利（第1名为胜）
        is_win = (player_settle.rank == 1)
        
        # 计算各部分经验
        # 注意：计分项基础经验需要从game_player表中读取该玩家本游戏的所有计分项
        # 暂时简化处理：假设已经在游戏过程中累加过了，这里只计算额外奖励
        
        # 本地模式不给予任何额外奖励
        if game.game_mode == 1:
            rank_reward = 0
            score_bonus = 0
            streak_bonus = 0
            effective_mode_multiplier = 1.0
        else:
            rank_reward = calculate_rank_reward(player_count, player_settle.rank)
            score_bonus = calculate_score_bonus(player_settle.total_score)
            streak_bonus = calculate_streak_bonus(old_streak)
            effective_mode_multiplier = mode_multiplier
        
        # 计算总经验奖励（游戏结束部分）
        # (排名奖励 + 得分加成) × (1 + 连胜加成) × 模式系数
        additional_exp = int(
            (rank_reward + score_bonus)
            * (1 + streak_bonus)
            * effective_mode_multiplier
        )
        
        # 更新经验（不超过上限）
        new_experience = min(user.total_experience + additional_exp, MAX_EXPERIENCE)
        actual_added = new_experience - user.total_experience
        user.total_experience = new_experience
        
        # 更新连胜（本地模式不更新）
        streak_updated = False
        if game.game_mode != 1:
            if is_win:
                user.current_win_streak = min(user.current_win_streak + 1, MAX_WIN_STREAK)
                if user.current_win_streak > user.max_win_streak:
                    user.max_win_streak = user.current_win_streak
                    user.max_win_streak_time = datetime.now()
                streak_updated = True
                
                # 更新总胜利次数 (仅非本地模式)
                user.total_wins = (user.total_wins or 0) + 1
            else:
                user.current_win_streak = 0
                streak_updated = True
            
            # 更新总对局次数 (仅非本地模式计入统计)
            user.total_games = (user.total_games or 0) + 1
        
        user.last_play_time = datetime.now()
        
        # 构建返回结果
        results.append({
            "user_id": user.id,
            "rank": player_settle.rank,
            "base_experience": 0,  # 游戏过程中已加
            "rank_reward": rank_reward,
            "score_bonus": score_bonus,
            "streak_bonus": streak_bonus,
            "mode_multiplier": effective_mode_multiplier,
            "total_experience": actual_added,
            "old_experience": old_experience,
            "new_experience": user.total_experience,
            "win_streak_updated": streak_updated,
            "old_streak": old_streak,
            "new_streak": user.current_win_streak
        })
    
    # 提交所有更改
    db.commit()
    
    # 清除缓存
    redis_client = get_redis_client()
    if redis_client and redis_client.get_client():
        try:
            exp_keys = list(redis_client.get_client().scan_iter(f"{CACHE_KEY_EXPERIENCE}:*"))
            streak_keys = list(redis_client.get_client().scan_iter(f"{CACHE_KEY_WIN_STREAK}:*"))
            games_keys = list(redis_client.get_client().scan_iter(f"{CACHE_KEY_TOTAL_GAMES}:*"))
            win_rate_keys = list(redis_client.get_client().scan_iter(f"{CACHE_KEY_WIN_RATE}:*"))
            if exp_keys:
                redis_client.get_client().delete(*exp_keys)
            if streak_keys:
                redis_client.get_client().delete(*streak_keys)
            if games_keys:
                redis_client.get_client().delete(*games_keys)
            if win_rate_keys:
                redis_client.get_client().delete(*win_rate_keys)
            logger.info("排行榜缓存已清除")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")
    
    return JSONResponse(
        content={
            "code": 200,
            "msg": "游戏结算成功",
            "data": {
                "game_id": request.game_id,
                "results": results
            }
        },
        media_type="application/json"
    )
