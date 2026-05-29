import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.user_setting import UserSetting
from app.models.game_player import GamePlayer as GamePlayerModel
from app.models.game_round import GameRound
from app.models.room_player import RoomPlayer
from app.models.player_score_detail import PlayerScoreDetail
from app.core.security import get_password_hash

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试用户定义
TEST_USERS = [
    {
        "nickname": "testplayer1",
        "phone": "13800138001",
        "password": "Test@1234",
        "points": 2000
    },
    {
        "nickname": "testplayer2",
        "phone": "13800138002",
        "password": "Test@5678",
        "points": 1580
    },
    {
        "nickname": "testplayer3",
        "phone": "13800138003",
        "password": "Test@9012",
        "points": 3000
    }
]

TEST_USER_NICKNAMES = [user["nickname"] for user in TEST_USERS]


def delete_user_and_related(db, user_id):
    """删除单个用户及其所有关联数据"""
    # 删除游戏回合记录
    db.query(GameRound).filter(GameRound.current_player_id == user_id).delete(synchronize_session=False)
    
    # 删除玩家分数详情
    db.query(PlayerScoreDetail).filter(PlayerScoreDetail.player_id == user_id).delete(synchronize_session=False)
    
    # 删除游戏玩家记录
    db.query(GamePlayerModel).filter(GamePlayerModel.user_id == user_id).delete(synchronize_session=False)
    
    # 删除房间玩家记录
    db.query(RoomPlayer).filter(RoomPlayer.user_id == user_id).delete(synchronize_session=False)
    
    # 删除用户设置
    db.query(UserSetting).filter(UserSetting.user_id == user_id).delete(synchronize_session=False)
    
    # 删除用户
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


def clean_test_data():
    """清理所有不需要的数据（无密码用户和重复测试用户）"""
    db = SessionLocal()
    try:
        print("开始清理数据...")
        
        # 1. 删除没有密码的真实用户（user_type=1）
        no_pwd_users = db.query(User).filter(
            User.user_type == 1,
            (User.password.is_(None) | (User.password == ""))
        ).all()
        
        if no_pwd_users:
            print(f"\n[1/3] 清理无密码真实用户...")
            user_ids = [user.id for user in no_pwd_users]
            
            # 删除关联数据
            db.query(GameRound).filter(GameRound.current_player_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(PlayerScoreDetail).filter(PlayerScoreDetail.player_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(GamePlayerModel).filter(GamePlayerModel.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(RoomPlayer).filter(RoomPlayer.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(UserSetting).filter(UserSetting.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
            
            db.commit()
            print(f"    已删除 {len(no_pwd_users)} 个无密码用户")
        else:
            print(f"\n[1/3] 没有需要清理的无密码用户")
        
        # 2. 删除重复的测试用户（保留最新的一个）
        print("\n[2/3] 清理重复测试用户...")
        for nickname in TEST_USER_NICKNAMES:
            users = db.query(User).filter(User.nickname == nickname).order_by(User.id.desc()).all()
            if len(users) > 1:
                # 保留第一个（ID最大的），删除其余的
                users_to_delete = users[1:]
                for user in users_to_delete:
                    delete_user_and_related(db, user.id)
                db.commit()
                print(f"    {nickname}: 删除了 {len(users_to_delete)} 个重复记录")
        
        # 3. 删除多余的AI机器人用户（保留3个标准AI）
        print("\n[3/3] 清理多余的AI机器人...")
        ai_users = db.query(User).filter(User.user_type == 2).all()
        standard_ais = ["AI-简单", "AI-中等", "AI-困难"]
        ai_to_delete = [user for user in ai_users if user.nickname not in standard_ais]
        
        if ai_to_delete:
            for ai in ai_to_delete:
                delete_user_and_related(db, ai.id)
            db.commit()
            print(f"    删除了 {len(ai_to_delete)} 个多余的AI机器人")
        else:
            print(f"    没有多余的AI机器人需要删除")
        
        print("\n数据清理完成")
        
    except Exception as e:
        db.rollback()
        print(f"清理失败: {e}")
    finally:
        db.close()


def add_test_users():
    """添加/更新测试用户数据（确保每个测试用户只有一条记录）"""
    db = SessionLocal()
    try:
        print("\n添加测试用户...")
        
        for user_data in TEST_USERS:
            # 检查是否已存在
            existing = db.query(User).filter(User.nickname == user_data["nickname"]).first()
            
            if existing:
                # 更新现有用户
                hashed_password = get_password_hash(user_data["password"])
                existing.phone = user_data["phone"]
                existing.password = hashed_password
                existing.points = user_data["points"]
                db.commit()
                print(f"    更新用户: {user_data['nickname']}")
            else:
                # 创建新用户
                hashed_password = get_password_hash(user_data["password"])
                
                new_user = User(
                    client_id=user_data["nickname"],
                    nickname=user_data["nickname"],
                    phone=user_data["phone"],
                    password=hashed_password,
                    user_type=1,
                    points=user_data["points"]
                )
                db.add(new_user)
                db.flush()
                
                # 创建用户设置（如果不存在）
                setting = db.query(UserSetting).filter(UserSetting.user_id == new_user.id).first()
                if not setting:
                    new_setting = UserSetting(
                        user_id=new_user.id,
                        sound_enabled=1,
                        rule_popup_enabled=1
                    )
                    db.add(new_setting)
                
                db.commit()
                print(f"    创建用户: {user_data['nickname']}")
        
        print("测试用户添加完成")
    except Exception as e:
        db.rollback()
        print(f"添加失败: {e}")
    finally:
        db.close()


def show_current_users():
    """显示当前用户列表"""
    db = SessionLocal()
    try:
        print("\n当前用户列表:")
        print("-" * 80)
        print(f"{'ID':<5} {'昵称':<15} {'类型':<8} {'密码':<8} {'积分':<6}")
        print("-" * 80)
        
        users = db.query(User).order_by(User.user_type, User.id).all()
        for user in users:
            user_type = "真实玩家" if user.user_type == 1 else "AI"
            has_pwd = "有" if user.password else "无"
            print(f"{user.id:<5} {user.nickname:<15} {user_type:<8} {has_pwd:<8} {user.points:<6}")
        
        print("-" * 80)
        print(f"总计: {len(users)} 个用户")
        
    finally:
        db.close()


def main():
    print("=" * 60)
    print("测试数据清理与初始化工具")
    print("=" * 60)
    
    # 显示当前状态
    show_current_users()
    
    # 清理数据
    clean_test_data()
    
    # 添加测试用户
    add_test_users()
    
    # 显示最终状态
    show_current_users()
    
    print("\n" + "=" * 60)
    print("操作完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
