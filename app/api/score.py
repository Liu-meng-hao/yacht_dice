from fastapi import APIRouter, Depends
from typing import Dict, List
import json
from app.schemas.game import (
    PossibleScoresResponse,
    ScoreHistoryRequest,
    ScoreHistoryResponse,
    LeaderboardResponse,
    LeaderboardItem,
    InitScorePanelResponse,
    PlayerPanelItem,
    GetLockStatusResponse,
    LockedItem,
    SubmitScoreRequest,
    SubmitScoreResponse
)
from app.game.game_manager import GameManager
from app.game.scoring import ScoreCalculator
from app.models.user import User
from app.models import GamePlayer, PlayerScoreDetail, ScoreItem, GameRound
from sqlalchemy import func
from app.core.response import ApiResponse, ApiResponseModel
from app.core.dependencies import get_current_user

router = APIRouter(tags=["计分"])


@router.get(
    "/score-panel/init/{game_id}",
    summary="初始化计分面板",
    description="获取计分面板的玩家静态信息",
    responses={
        200: {
            "model": ApiResponseModel[InitScorePanelResponse],
            "description": "成功响应"
        }
    }
)
async def init_score_panel(game_id: str, user: User = Depends(get_current_user)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    db_game = game_data.db_game
    db_players = game_data.db_players
    
    players = []
    for p in db_players:
        user = game_data.db.query(User).filter(User.id == p.user_id).first()
        players.append(PlayerPanelItem(
            player_id=str(p.user_id),
            username=user.nickname if user and user.nickname else f"Player{p.player_order}",
            avatar=user.avatar if user and user.avatar else "",
            player_order=p.player_order
        ))
    
    game_data.close()
    
    return ApiResponse.success(
        data=InitScorePanelResponse(
            game_id=str(db_game.id),
            players=players
        ),
        msg="获取成功"
    )


@router.get(
    "/game/{game_id}/lock-status",
    summary="获取锁定状态",
    description="获取玩家已锁定和未锁定的计分项列表",
    responses={
        200: {
            "model": ApiResponseModel[GetLockStatusResponse],
            "description": "成功响应"
        }
    }
)
async def get_lock_status(game_id: str, player_id: str, user: User = Depends(get_current_user)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    db = game_data.db
    
    game_player = db.query(GamePlayer).filter(
        GamePlayer.game_id == game_data.db_game.id,
        GamePlayer.user_id == int(player_id)
    ).first()
    
    if not game_player:
        game_data.close()
        return ApiResponse.error(msg="玩家不存在", code=404)
    
    locked_details = db.query(PlayerScoreDetail).filter(
        PlayerScoreDetail.player_id == game_player.user_id,
        PlayerScoreDetail.score_value.isnot(None)
    ).all()
    
    locked_items = [
        LockedItem(item_id=d.score_item_id, score_value=d.score_value)
        for d in locked_details
    ]
    locked_item_ids = {d.score_item_id for d in locked_details}
    
    all_score_items = db.query(ScoreItem).all()
    unlocked_items = [item.id for item in all_score_items if item.id not in locked_item_ids]
    
    game_data.close()
    
    return ApiResponse.success(
        data=GetLockStatusResponse(
            player_id=player_id,
            locked_items=locked_items,
            unlocked_items=unlocked_items
        ),
        msg="获取成功"
    )



# @router.post(
#     "/game/{game_id}/submit-score",
#     summary="提交分数（已弃用）",
#     description="玩家提交计分项得分，已合并到 /{game_id}/score 接口",
#     deprecated=True,
#     responses={
#         200: {
#             "model": ApiResponseModel[SubmitScoreResponse],
#             "description": "成功响应"
#         }
#     }
# )
# async def submit_score(game_id: str, request: SubmitScoreRequest):
#     game_data = GameManager.get_game(game_id)
#     if not game_data:
#         return ApiResponse.error(msg="游戏不存在", code=404)
#     
#     db = game_data.db
#     db_game = game_data.db_game
#     
#     player_id = request.player_id
#     score_item_id = request.score_item_id
#     score_value = request.score_value
#     dice_data = request.dice_data
#     round_number = request.round_number
#     
#     game_player = db.query(GamePlayer).filter(
#         GamePlayer.game_id == db_game.id,
#         GamePlayer.user_id == player_id
#     ).first()
#     
#     if not game_player:
#         game_data.close()
#         return ApiResponse.error(msg="玩家不存在", code=404)
#     
#     if score_item_id == 7:
#         game_data.close()
#         return ApiResponse.error(msg="奖励分不可直接提交", code=400)
#     
#     existing_detail = db.query(PlayerScoreDetail).filter(
#         PlayerScoreDetail.player_id == player_id,
#         PlayerScoreDetail.score_item_id == score_item_id
#     ).first()
#     
#     if existing_detail:
#         game_data.close()
#         return ApiResponse.error(msg="该计分项已提交", code=400)
#     
#     try:
#         new_detail = PlayerScoreDetail(
#             game_id=db_game.id,
#             player_id=player_id,
#             score_item_id=score_item_id,
#             round_number=round_number,
#             score_value=score_value
#         )
#         db.add(new_detail)
#         
#         upper_items = [1, 2, 3, 4, 5, 6]
#         lower_items = [8, 9, 10, 11, 12, 13, 14]
#         
#         upper_score = db.query(db.func.sum(PlayerScoreDetail.score_value)).filter(
#             PlayerScoreDetail.game_id == db_game.id,
#             PlayerScoreDetail.player_id == player_id,
#             PlayerScoreDetail.score_item_id.in_(upper_items)
#         ).scalar() or 0
#         
#         lower_score = db.query(db.func.sum(PlayerScoreDetail.score_value)).filter(
#             PlayerScoreDetail.game_id == db_game.id,
#             PlayerScoreDetail.player_id == player_id,
#             PlayerScoreDetail.score_item_id.in_(lower_items)
#         ).scalar() or 0
#         
#         bonus_score = 35 if upper_score >= 63 else 0
#         total_score = upper_score + lower_score + bonus_score
#         
#         game_player.upper_score = upper_score
#         game_player.lower_score = lower_score
#         game_player.bonus_score = bonus_score
#         game_player.total_score = total_score
#         
#         all_players = db.query(GamePlayer).filter(GamePlayer.game_id == db_game.id).all()
#         all_submitted = True
#         
#         for p in all_players:
#             submitted_count = db.query(PlayerScoreDetail).filter(
#                 PlayerScoreDetail.player_id == p.user_id
#             ).count()
#             if submitted_count < 13:
#                 all_submitted = False
#                 break
#         
#         if all_submitted:
#             db_game.game_status = 3
#             db.query(GameRound).filter(
#                 GameRound.game_id == db_game.id,
#                 GameRound.round_number == round_number
#             ).update({"round_status": 3, "end_time": func.now()})
#             next_player_id = None
#         else:
#             current_player_idx = None
#             for i, p in enumerate(all_players):
#                 if p.user_id == player_id:
#                     current_player_idx = i
#                     break
#             
#             next_player_idx = (current_player_idx + 1) % len(all_players)
#             next_player = all_players[next_player_idx]
#             
#             db.query(GameRound).filter(
#                 GameRound.game_id == db_game.id,
#                 GameRound.round_number == round_number
#             ).update({"round_status": 3, "end_time": func.now()})
#             
#             new_round = GameRound(
#                 game_id=db_game.id,
#                 round_number=round_number + 1,
#                 current_player_id=next_player.user_id,
#                 dice_data=None,
#                 reroll_count=0,
#                 round_status=2,
#                 start_time=func.now()
#             )
#             db.add(new_round)
#             next_player_id = next_player.user_id
#         
#         db.commit()
#         
#         game_data.close()
#         
#         return ApiResponse.success(
#             data=SubmitScoreResponse(
#                 submit_success=True,
#                 player_id=player_id,
#                 score_item_id=score_item_id,
#                 score_value=score_value,
#                 total_score=total_score,
#                 upper_score=upper_score,
#                 lower_score=lower_score,
#                 bonus_score=bonus_score,
#                 game_status=db_game.game_status,
#                 next_player_id=next_player_id
#             ),
#             msg="提交成功"
#         )
#     
#     except Exception as e:
#         db.rollback()
#         game_data.close()
#         return ApiResponse.error(msg=f"提交失败: {str(e)}", code=500)



@router.get(
    "/possible/{game_id}",
    summary="获取可能得分",
    description="计算当前骰子在所有计分项的可能得分",
    responses={
        200: {
            "model": ApiResponseModel[PossibleScoresResponse],
            "description": "成功响应"
        }
    }
)
async def get_possible_scores(game_id: str, user: User = Depends(get_current_user)):
    game_data = GameManager.get_game(game_id)
    if not game_data:
        return ApiResponse.error(msg="游戏不存在", code=404)
    
    game_dict = game_data.to_dict()
    dice = game_dict["dice"]
    possible_scores: Dict[str, int] = {}
    
    for category in ScoreCalculator.CATEGORIES:
        try:
            possible_scores[category] = ScoreCalculator.calculate_score(dice, category)
        except:
            possible_scores[category] = None
    
    game_data.close()
    
    return ApiResponse.success(
        data=PossibleScoresResponse(possible_scores=possible_scores),
        msg="获取成功"
    )


# @router.get(
#     "/history",
#     summary="获取历史记录",
#     description="获取当前玩家的历史游戏记录",
#     responses={
#         200: {
#             "model": ApiResponseModel[ScoreHistoryResponse],
#             "description": "成功响应"
#         }
#     }
# )
# async def get_score_history(request: ScoreHistoryRequest):
#     return ApiResponse.success(
#         data=ScoreHistoryResponse(history=[]),
#         msg="获取成功（功能开发中")


# @router.get(
#     "/leaderboard",
#     summary="获取排行榜",
#     description="获取排行榜",
#     responses={
#         200: {
#             "model": ApiResponseModel[LeaderboardResponse],
#             "description": "成功响应"
#         }
#     }
# )
# async def get_leaderboard():
#     return ApiResponse.success(
#         data=LeaderboardResponse(leaderboard=[]),
#         msg="获取成功（功能开发中）"
#     )
