"""
强制重建数据库表（无需确认）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import engine, Base, SessionLocal
from app.models import user, game, online_room, room_player, game_player, game_round, player_score_detail, score_item, user_setting

print("========== 强制重建数据库表 ==========")

try:
    db = SessionLocal()
    
    # 禁用外键检查
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    db.commit()
    
    # 获取所有表名并删除
    result = db.execute(text("SHOW TABLES"))
    tables = [row[0] for row in result]
    
    for table in tables:
        db.execute(text(f"DROP TABLE IF EXISTS {table}"))
        print(f"已删除表: {table}")
    
    db.commit()
    
    # 重新启用外键检查
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    db.commit()
    
    db.close()
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("\n✅ 数据库表创建成功！")
    print("\n已创建的表：")
    for table in Base.metadata.tables:
        print(f"  - {table}")
        
except Exception as e:
    print(f"\n❌ 操作失败：{e}")
    sys.exit(1)
