from sqlalchemy import Column, BigInteger, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.db.session import Base


class PlayerScoreDetail(Base):
    __tablename__ = "player_score_detail"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    game_id = Column(BigInteger, ForeignKey("game.id"), nullable=False, comment="游戏ID")
    player_id = Column(BigInteger, ForeignKey("user.id"), nullable=False, comment="玩家ID")
    score_item_id = Column(Integer, ForeignKey("score_item.id"), nullable=False, comment="计分项ID")
    round_number = Column(Integer, nullable=True, comment="回合数")
    score_value = Column(Integer, nullable=False, default=0, comment="得分值")
    submit_time = Column(DateTime, nullable=True, comment="提交时间")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
