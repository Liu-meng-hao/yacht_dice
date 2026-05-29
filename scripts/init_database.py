import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.user_setting import UserSetting
from app.core.security import get_password_hash

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始数据定义
AI_USERS = [
    {"nickname": "AI-简单", "ai_difficulty": 1, "client_id": "client-ai-easy"},
    {"nickname": "AI-中等", "ai_difficulty": 2, "client_id": "client-ai-medium"},
    {"nickname": "AI-困难", "ai_difficulty": 3, "client_id": "client-ai-hard"}
]

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


def drop_and_recreate_db():
    """使用SQL直接清空并重建表"""
    print("正在使用SQL命令清空数据...")
    
    sql_commands = [
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE player_score_detail;",
        "TRUNCATE TABLE game_round;",
        "TRUNCATE TABLE game_player;",
        "TRUNCATE TABLE room_player;",
        "TRUNCATE TABLE user_setting;",
        "TRUNCATE TABLE user;",
        "SET FOREIGN_KEY_CHECKS = 1;"
    ]
    
    with engine.connect() as conn:
        for cmd in sql_commands:
            conn.execute(text(cmd))
            print(f"    执行: {cmd[:50]}...")
        conn.commit()
    
    print("所有表已清空")


def init_ai_users():
    """初始化AI用户"""
    db = SessionLocal()
    try:
        print("\n创建AI用户...")
        
        for ai_data in AI_USERS:
            new_ai = User(
                client_id=ai_data["client_id"],
                nickname=ai_data["nickname"],
                user_type=2,  # AI用户
                ai_difficulty=ai_data["ai_difficulty"],
                points=0
            )
            db.add(new_ai)
            print(f"    创建AI: {ai_data['nickname']}")
        
        db.commit()
        print("AI用户创建完成")
        
    except Exception as e:
        db.rollback()
        print(f"创建AI用户失败: {e}")
        raise
    finally:
        db.close()


def init_test_users():
    """初始化测试用户"""
    db = SessionLocal()
    try:
        print("\n创建测试用户...")
        
        for user_data in TEST_USERS:
            hashed_password = get_password_hash(user_data["password"])
            
            new_user = User(
                client_id=user_data["nickname"],
                nickname=user_data["nickname"],
                phone=user_data["phone"],
                password=hashed_password,
                user_type=1,  # 真实玩家
                points=user_data["points"]
            )
            db.add(new_user)
            db.flush()
            
            # 创建用户设置
            new_setting = UserSetting(
                user_id=new_user.id,
                sound_enabled=1,
                rule_popup_enabled=1
            )
            db.add(new_setting)
            
            print(f"    创建用户: {user_data['nickname']}")
        
        db.commit()
        print("测试用户创建完成")
        
    except Exception as e:
        db.rollback()
        print(f"创建测试用户失败: {e}")
        raise
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
        
        users = db.query(User).order_by(User.id).all()
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
    print("数据库彻底初始化工具")
    print("=" * 60)
    print("\n⚠️ 警告：此操作将删除所有现有数据！")
    print("请确保已备份重要数据。")
    
    # 获取用户确认
    print("\n确定要继续吗？(y/N): y")
    
    # 清空所有表
    drop_and_recreate_db()
    
    # 初始化AI用户
    init_ai_users()
    
    # 初始化测试用户
    init_test_users()
    
    # 显示最终状态
    show_current_users()
    
    print("\n" + "=" * 60)
    print("数据库初始化完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
