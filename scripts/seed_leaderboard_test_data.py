"""
排行榜测试数据脚本
生成游戏记录和游戏玩家数据，用于测试排行榜
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.game import Game
from app.models.game_player import GamePlayer


def seed_test_games():
    """生成测试游戏数据"""
    print("=" * 60)
    print("生成排行榜测试数据")
    print("=" * 60)
    
    db = SessionLocal()
    try:
        # 获取真实用户
        users = db.query(User).filter(
            User.is_deleted == 0,
            User.user_type == 1
        ).all()
        
        if len(users) < 2:
            print("用户数量不足，无法生成测试数据")
            return
        
        print(f"\n找到 {len(users)} 个用户")
        
        # 为每个用户生成几局游戏
        game_count = 5
        print(f"\n为每个用户生成 {game_count} 局游戏...")
        
        # 预定义一些分数范围，让排行榜更有区分度
        user_scores = {}
        for idx, user in enumerate(users):
            # 越靠前的用户可能有更高的分数
            base_score = 150 + (len(users) - idx) * 30
            user_scores[user.id] = {
                "min": base_score - 50,
                "max": base_score + 100
            }
        
        for game_idx in range(game_count):
            # 创建游戏
            game = Game(
                game_mode=3,  # 联机模式
                player_count=2,
                total_rounds=13,
                game_status=3,  # 已结束
                start_time=datetime.now() - timedelta(days=game_count - game_idx),
                end_time=datetime.now() - timedelta(days=game_count - game_idx - 0.5),
                is_deleted=0
            )
            db.add(game)
            db.flush()
            
            # 选两个用户
            game_users = random.sample(users, 2)
            
            # 创建游戏玩家记录
            for idx, user in enumerate(game_users):
                score_range = user_scores[user.id]
                total_score = random.randint(score_range["min"], score_range["max"])
                
                # 随机生成上半区、下半区、奖励分
                upper_score = random.randint(50, 100)
                lower_score = random.randint(50, 150)
                bonus_score = total_score - upper_score - lower_score
                if bonus_score < 0:
                    bonus_score = 0
                
                game_player = GamePlayer(
                    game_id=game.id,
                    user_id=user.id,
                    is_owner=1 if idx == 0 else 0,
                    player_order=idx + 1,
                    total_score=total_score,
                    upper_score=upper_score,
                    lower_score=lower_score,
                    bonus_score=bonus_score,
                    is_ai=0
                )
                db.add(game_player)
                
                print(f"  Game {game.id}: {user.nickname} = {total_score} 分")
            
            # 设置游戏赢家（分数高的）
            winner_user = game_users[0]
            game.winner_id = winner_user.id
            
            db.commit()
        
        print(f"\n✅ 成功生成 {game_count} 局测试游戏！")
        
        # 显示当前最高分预览
        print("\n" + "=" * 60)
        print("当前最高分预览")
        print("=" * 60)
        
        from sqlalchemy import func, desc
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
        
        results = db.query(
            User.id,
            User.nickname,
            subquery.c.max_score
        ).join(
            subquery, User.id == subquery.c.user_id
        ).order_by(
            desc(subquery.c.max_score)
        ).limit(5).all()
        
        print(f"\n{'Rank':<6}{'User':<15}{'Score':<8}")
        print("-" * 60)
        for rank, (user_id, nickname, score) in enumerate(results, 1):
            print(f"{rank:<6}{nickname:<15}{score:<8}")
        
        print("\n" + "=" * 60)
        print("测试数据生成完成！")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_games()
