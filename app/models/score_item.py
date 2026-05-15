from sqlalchemy import Column, Integer, String, Text
from app.db.session import Base


class ScoreItem(Base):
    __tablename__ = "score_item"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    item_name = Column(String(50), nullable=False, comment="计分项名称")
    item_category = Column(String(20), nullable=False, comment="计分项分类：upper-上半区，lower-下半区")
    score_rule = Column(Text, nullable=True, comment="计分规则描述")
    base_score = Column(Integer, nullable=True, comment="基础分数")
    is_bonus = Column(Integer, nullable=False, default=0, comment="是否为奖励项：0-否，1-是")
