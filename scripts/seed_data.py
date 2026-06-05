"""
数据填充脚本
运行此脚本可以在数据库中插入测试数据
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.game import Game
from app.models.score_item import ScoreItem
from app.models.online_room import OnlineRoom
from app.models.game_player import GamePlayer
from app.models.game_round import GameRound
from app.models.player_score_detail import PlayerScoreDetail


def seed_score_items():
    """插入计分项目数据（快艇骰子13个计分项）"""
    print("\n========== 插入计分项目数据 ==========")
    
    db = SessionLocal()
    try:
        existing_count = db.query(ScoreItem).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个计分项目，跳过插入")
            return
        
        score_items_data = [
            {"item_name": "ones", "item_category": "upper", "score_rule": "一点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "twos", "item_category": "upper", "score_rule": "二点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "threes", "item_category": "upper", "score_rule": "三点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "fours", "item_category": "upper", "score_rule": "四点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "fives", "item_category": "upper", "score_rule": "五点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "sixes", "item_category": "upper", "score_rule": "六点的总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "threeOfAKind", "item_category": "lower", "score_rule": "三个相同，所有骰子总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "fourOfAKind", "item_category": "lower", "score_rule": "四个相同，所有骰子总和", "base_score": 0, "is_bonus": 0},
            {"item_name": "fullHouse", "item_category": "lower", "score_rule": "三个+一对，25分", "base_score": 25, "is_bonus": 0},
            {"item_name": "smallStraight", "item_category": "lower", "score_rule": "小顺子，30分", "base_score": 30, "is_bonus": 0},
            {"item_name": "largeStraight", "item_category": "lower", "score_rule": "大顺子，40分", "base_score": 40, "is_bonus": 0},
            {"item_name": "yahtzee", "item_category": "lower", "score_rule": "五个相同，50分", "base_score": 50, "is_bonus": 1},
            {"item_name": "chance", "item_category": "lower", "score_rule": "任意组合，所有骰子总和", "base_score": 0, "is_bonus": 0}
        ]
        
        for item_data in score_items_data:
            item = ScoreItem(**item_data)
            db.add(item)
            print(f"创建计分项: {item_data['item_name']}")
        
        db.commit()
        print(f"\n共创建 {len(score_items_data)} 个计分项目")
        
    except Exception as e:
        db.rollback()
        print(f"插入失败: {e}")
        sys.exit(1)
    finally:
        db.close()


def seed_users():
    """插入测试用户数据（匿名玩家模式）"""
    print("\n========== 插入用户数据 ==========")
    
    db = SessionLocal()
    try:
        existing_count = db.query(User).count()
        if existing_count > 0:
            print(f"数据库中已有 {existing_count} 个用户，跳过插入")
            return
        
        users_data = [
            {"client_id": "client-001", "nickname": "玩家1", "user_type": 1, "points": 150, "total_games": 10, "total_wins": 7, "highest_score": 320},
            {"client_id": "client-002", "nickname": "玩家2", "user_type": 1, "points": 120, "total_games": 8, "total_wins": 4, "highest_score": 280},
            {"client_id": "client-ai-easy", "nickname": "AI-简单", "user_type": 2, "ai_difficulty": 1, "points": 0, "total_games": 0, "total_wins": 0, "highest_score": 0},
            {"client_id": "client-ai-medium", "nickname": "AI-中等", "user_type": 2, "ai_difficulty": 2, "points": 0, "total_games": 0, "total_wins": 0, "highest_score": 0},
            {"client_id": "client-ai-hard", "nickname": "AI-困难", "user_type": 2, "ai_difficulty": 3, "points": 0, "total_games": 0, "total_wins": 0, "highest_score": 0}
        ]
        
        for user_data in users_data:
            user = User(**user_data)
            db.add(user)
            print(f"创建用户: {user_data['nickname']}")
        
        db.commit()
        print(f"\n共创建 {len(users_data)} 个用户")
        
    except Exception as e:
        db.rollback()
        print(f"插入失败: {e}")
        sys.exit(1)
    finally:
        db.close()


def seed_game_records():
    """插入测试游戏记录数据"""
    print("\n========== 插入测试游戏记录 ==========")
    print("(跳过，游戏记录通常由游戏逻辑自动生成)")


def clear_all_data():
    """清空所有数据（谨慎使用！）"""
    print("\n【警告】此操作将清空所有数据！")
    confirm = input("确认清空？(输入 YES 确认): ")
    
    if confirm != "YES":
        print("操作已取消")
        return
    
    db = SessionLocal()
    try:
        db.query(PlayerScoreDetail).delete()
        db.query(GameRound).delete()
        db.query(GamePlayer).delete()
        db.query(Game).delete()
        db.query(OnlineRoom).delete()
        db.query(ScoreItem).delete()
        db.query(User).delete()
        db.commit()
        print("所有数据已清空")
    except Exception as e:
        db.rollback()
        print(f"清空失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "clear":
            clear_all_data()
        elif sys.argv[1] == "users":
            seed_users()
        elif sys.argv[1] == "score_items":
            seed_score_items()
    else:
        seed_score_items()
        seed_users()
        seed_game_records()
        print("\n所有测试数据插入完成！")
