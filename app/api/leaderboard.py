from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.leaderboard import UpdateWinsRequest

router = APIRouter()


@router.post(
    "/update-wins",
    summary="更新胜利次数",
    description="游戏结束时，根据游戏模式更新胜利玩家的total_wins字段（仅online模式生效）"
)
async def update_wins(
    request: UpdateWinsRequest,
    db: Session = Depends(get_db)
):
    """
    更新胜利次数接口
    
    - **winner_id**: 胜利玩家的ID
    - **game_mode**: 游戏模式：local（本地）、ai（AI对战）、online（联机对战）
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
    
    if user.is_deleted:
        return JSONResponse(
            content={"code": 400, "msg": "用户已被删除", "data": None},
            media_type="application/json"
        )
    
    # 只有联机模式（online）才更新胜利次数
    if request.game_mode == "online":
        user.total_wins += 1
        db.commit()
        db.refresh(user)
        
        return JSONResponse(
            content={
                "code": 200,
                "msg": "胜利次数更新成功",
                "data": {
                    "user_id": user.id,
                    "total_wins": user.total_wins,
                    "message": "胜利次数更新成功"
                }
            },
            media_type="application/json"
        )
    else:
        # 非联机模式，不更新胜利次数
        return JSONResponse(
            content={
                "code": 200,
                "msg": f"{request.game_mode}模式不更新胜利次数",
                "data": {
                    "user_id": user.id,
                    "total_wins": user.total_wins,
                    "message": f"{request.game_mode}模式不更新胜利次数"
                }
            },
            media_type="application/json"
        )


@router.get(
    "/ranking",
    summary="获取排行榜",
    description="获取按照total_wins降序排列的用户排行榜"
)
async def get_leaderboard(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    获取排行榜接口
    
    - **limit**: 返回的排行榜数量，默认10
    """
    if limit <= 0 or limit > 100:
        return JSONResponse(
            content={"code": 400, "msg": "limit必须在1-100之间", "data": None},
            media_type="application/json"
        )
    
    users = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).order_by(
        User.total_wins.desc()
    ).limit(limit).all()
    
    leaderboard = []
    for rank, user in enumerate(users, start=1):
        leaderboard.append({
            "rank": rank,
            "user_id": user.id,
            "nickname": user.nickname,
            "total_wins": user.total_wins
        })
    
    total_count = db.query(User).filter(
        User.is_deleted == 0,
        User.user_type == 1
    ).count()
    
    return JSONResponse(
        content={
            "code": 200,
            "msg": "获取排行榜成功",
            "data": {
                "leaderboard": leaderboard,
                "total_count": total_count
            }
        },
        media_type="application/json"
    )