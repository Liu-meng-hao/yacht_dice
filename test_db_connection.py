"""
数据库连接测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.session import engine, SessionLocal
from app.db.redis_client import redis_client
from app.models.score_item import ScoreItem

print("========== 数据库连接测试 ==========")

# 测试 MySQL 连接
try:
    db = SessionLocal()
    db.execute(text("SELECT 1"))
    print("✅ MySQL 连接成功")
    
    # 检查 ScoreItem 表是否有数据
    score_count = db.query(ScoreItem).count()
    print(f"✅ ScoreItem 表有 {score_count} 条记录")
    if score_count == 0:
        print("⚠️  ScoreItem 表为空，请执行: python scripts/seed_data.py")
    
    db.close()
except Exception as e:
    print(f"❌ MySQL 连接失败: {e}")
    sys.exit(1)

# 测试 Redis 连接
try:
    client = redis_client.get_client()
    client.ping()
    print("✅ Redis 连接成功")
except Exception as e:
    print(f"❌ Redis 连接失败: {e}")

print("\n========== 测试完成 ==========")
