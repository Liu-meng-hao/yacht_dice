"""
查看数据库中的计分项数据
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.score_item import ScoreItem
from app.db.session import SessionLocal

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}?charset=utf8mb4"

engine = create_engine(SQLALCHEMY_DATABASE_URL)


def check_score_items():
    """查看所有计分项"""
    db = SessionLocal()
    try:
        print("=" * 60)
        print("数据库中的计分项")
        print("=" * 60)
        
        items = db.query(ScoreItem).order_by(ScoreItem.id).all()
        
        print(f"\n{'ID':<4} {'名称':<25} {'分类':<10} {'基础分':<8} {'经验值':<8}")
        print("-" * 60)
        
        for item in items:
            category = item.item_category or "N/A"
            base_score = item.base_score or "N/A"
            exp_value = item.experience_value if hasattr(item, 'experience_value') else "N/A"
            print(f"{item.id:<4} {item.item_name:<25} {category:<10} {str(base_score):<8} {str(exp_value):<8}")
        
        print("-" * 60)
        print(f"总计: {len(items)} 个计分项\n")
        
    finally:
        db.close()


if __name__ == "__main__":
    check_score_items()
