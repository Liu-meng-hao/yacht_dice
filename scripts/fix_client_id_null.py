import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_client_id_null():
    """修复 room_player 表的 client_id 字段，将其设置为允许 NULL"""
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}?charset=utf8mb4"
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # 修改 room_player 表的 client_id 字段允许 NULL
            print("正在修改 room_player 表的 client_id 字段...")
            conn.execute(text("ALTER TABLE room_player MODIFY client_id VARCHAR(100) NULL;"))
            conn.commit()
            print("✅ 成功将 room_player.client_id 设置为允许 NULL")
            
    except Exception as e:
        print(f"❌ 修改失败: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("修复 room_player.client_id 字段")
    print("=" * 60)
    fix_client_id_null()
    print("\n修复完成！")
