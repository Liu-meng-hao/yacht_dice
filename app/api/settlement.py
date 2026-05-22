from fastapi import APIRouter
from typing import List
from app.schemas.game import (
    SettlementResponse,
    SettlementPlayer,
    RematchRequest,
    RematchResponse,
    BackToHomeRequest,
    GameMode,
    GameStatus,
    GameStateResponse,
    GamePlayer,
    FinalRankingPlayer,
    FinalRankingResponse,
    ScoreSummaryResponse,
    GameHighlightsResponse
)
from app.game.game_manager import GameManager
from app.core.response import ApiResponse, ApiResponseModel
from app.db.session import get_db
from app.models import GamePlayer as GamePlayerModel
from app.models import User, PlayerScoreDetail

router = APIRouter(tags=["结算"])



@router.post(
    "/{game_id}/rematch",
    summary="再来一局",
    description="开始新一局游戏",
    responses={
        200: {
            "model": ApiResponseModel[RematchResponse],
            "description": "成功响应"
        }
    }
)
async def rematch(game_id: str, request: RematchRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    player_names = [p["name"] for p in game_dict["players"]]
    game_mode = game_dict["game_mode"]
    game_data.close()
    
    new_game_data = GameManager.create_game(game_mode, player_names)
    GameManager.start_game(new_game_data)
    new_game_dict = new_game_data.to_dict()
    
    return ApiResponse.success(
        data=RematchResponse(
            new_game_id=new_game_dict["game_id"],
            game_state=GameStateResponse(
                game_id=new_game_dict["game_id"],
                game_mode=GameMode(new_game_dict["game_mode"]),
                current_player=new_game_dict["current_player"],
                players=[GamePlayer(**p) for p in new_game_dict["players"]],
                dice=new_game_dict["dice"],
                dice_locked=new_game_dict["dice_locked"],
                rolls_left=new_game_dict["rolls_left"],
                status=GameStatus(new_game_dict["status"]),
                created_at=new_game_dict["created_at"],
                finished_at=new_game_dict["finished_at"]
            )
        ),
        msg="新游戏已创建"
    )


@router.post(
    "/{game_id}/back",
    summary="返回首页",
    description="返回模式选择首页",
    responses={
        200: {
            "model": ApiResponseModel[None],
            "description": "成功响应"
        }
    }
)
async def back_to_home(game_id: str, request: BackToHomeRequest):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_data.close()
    GameManager.remove_game(game_id)
    return ApiResponse.success(msg="已返回首页")


@router.get(
    "/{game_id}/final-ranking",
    summary="获取最终排名",
    description="获取游戏结束后的最终排名列表，按总分降序排列",
    responses={
        200: {
            "model": ApiResponseModel[FinalRankingResponse],
            "description": "成功响应"
        }
    }
)
async def get_final_ranking(game_id: str):
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        game_players = db.query(GamePlayerModel).filter(
            GamePlayerModel.game_id == int(game_id)
        ).order_by(GamePlayerModel.total_score.desc()).all()
        
        if not game_players:
            return ApiResponse.error(msg="游戏不存在", code=404)
        
        ranking_list = []
        for rank, gp in enumerate(game_players, 1):
            user = db.query(User).filter(User.id == gp.user_id).first()
            ranking_list.append(FinalRankingPlayer(
                rank=rank,
                player_id=str(gp.user_id),
                username=user.nickname if user else "未知玩家",
                avatar=user.avatar if user and user.avatar else "",
                total_score=gp.total_score
            ))
        
        return ApiResponse.success(
            data=FinalRankingResponse(ranking_list=ranking_list),
            msg="成功"
        )
    except Exception as e:
        return ApiResponse.error(msg=f"获取排名失败: {str(e)}", code=500)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass



@router.get(
    "/{game_id}/score-summary",
    summary="获取分数明细",
    description="获取指定玩家在本局游戏中的详细分数构成",
    responses={
        200: {
            "model": ApiResponseModel[ScoreSummaryResponse],
            "description": "成功响应"
        }
    }
)
async def get_score_summary(game_id: str, player_id: int):
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        game_player = db.query(GamePlayerModel).filter(
            GamePlayerModel.game_id == int(game_id),
            GamePlayerModel.user_id == player_id
        ).first()
        
        if not game_player:
            return ApiResponse.error(msg="玩家不存在", code=404)
        
        yahtzee_count = db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == int(game_id),
            PlayerScoreDetail.player_id == player_id,
            PlayerScoreDetail.score_item_id == 13,
            PlayerScoreDetail.score_value == 50
        ).count()
        
        yahtzee_bonus = yahtzee_count * 100
        
        return ApiResponse.success(
            data=ScoreSummaryResponse(
                player_id=str(player_id),
                upper_score=game_player.upper_score,
                upper_bonus=game_player.bonus_score,
                upper_subtotal=game_player.upper_score + game_player.bonus_score,
                lower_score=game_player.lower_score,
                yahtzee_bonus=yahtzee_bonus,
                total_score=game_player.total_score
            ),
            msg="成功"
        )
    except Exception as e:
        return ApiResponse.error(msg=f"获取分数明细失败: {str(e)}", code=500)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass


@router.get(
    "/{game_id}/highlights",
    summary="获取精彩回顾",
    description="获取指定玩家在本局游戏中的精彩回顾数据",
    responses={
        200: {
            "model": ApiResponseModel[GameHighlightsResponse],
            "description": "成功响应"
        }
    }
)
async def get_game_highlights(game_id: str, player_id: int):
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        game_player = db.query(GamePlayerModel).filter(
            GamePlayerModel.game_id == int(game_id),
            GamePlayerModel.user_id == player_id
        ).first()
        
        if not game_player:
            return ApiResponse.error(msg="玩家不存在", code=404)
        
        yahtzee_count = db.query(PlayerScoreDetail).filter(
            PlayerScoreDetail.game_id == int(game_id),
            PlayerScoreDetail.player_id == player_id,
            PlayerScoreDetail.score_item_id == 13,
            PlayerScoreDetail.score_value == 50
        ).count()
        
        highest_score_result = db.query(PlayerScoreDetail.score_value).filter(
            PlayerScoreDetail.game_id == int(game_id),
            PlayerScoreDetail.player_id == player_id
        ).order_by(PlayerScoreDetail.score_value.desc()).first()
        
        highest_round_score = highest_score_result[0] if highest_score_result else 0
        
        upper_total = db.query(
            db.func.sum(PlayerScoreDetail.score_value)
        ).filter(
            PlayerScoreDetail.game_id == int(game_id),
            PlayerScoreDetail.player_id == player_id,
            PlayerScoreDetail.score_item_id.between(1, 6)
        ).scalar() or 0
        
        upper_bonus_scored = 1 if upper_total >= 63 else 0
        
        return ApiResponse.success(
            data=GameHighlightsResponse(
                yahtzee_count=yahtzee_count,
                highest_round_score=highest_round_score,
                upper_bonus_scored=upper_bonus_scored
            ),
            msg="成功"
        )
    except Exception as e:
        return ApiResponse.error(msg=f"获取精彩回顾失败: {str(e)}", code=500)
    finally:
        try:
            next(db_gen, None)
        except StopIteration:
            pass
