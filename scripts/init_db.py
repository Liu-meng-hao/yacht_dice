"""
数据库初始化脚本
运行此脚本可以自动创建所有数据库表
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base, engine
from app.models import user, game, online_room, room_player


def init_database():
    """初始化数据库，创建所有表"""
    print("开始创建数据库表...")
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建成功！")
        print("\n已创建的表：")
        for table in Base.metadata.tables:
            print(f"  - {table}")
    except Exception as e:
        print(f"❌ 创建失败：{e}")
        sys.exit(1)


def drop_database():
    """删除所有表（谨慎使用！）"""
    print("⚠️  警告：此操作将删除所有数据库表！")
    confirm = input("确认删除？(输入 YES 确认): ")
    
    if confirm != "YES":
        print("操作已取消")
        return
    
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ 所有表已删除！")
    except Exception as e:
        print(f"❌ 删除失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_database()
    else:
        init_database()
