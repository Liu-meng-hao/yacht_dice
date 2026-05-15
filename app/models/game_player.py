from sqlalchemy import Column, BigInteger, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.db.session import Base


class GamePlayer(Base):
    __tablename__ = "game_player"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    game_id = Column(BigInteger, ForeignKey("game.id"), nullable=False, comment="游戏ID")
    user_id = Column(BigInteger, ForeignKey("user.id"), nullable=False, comment="用户ID")
    is_owner = Column(Integer, nullable=False, default=0, comment="是否房主：0-否，1-是")
    player_order = Column(Integer, nullable=False, comment="玩家顺序")
    total_score = Column(Integer, nullable=False, default=0, comment="总得分")
    upper_score = Column(Integer, nullable=False, default=0, comment="上半区得分")
    lower_score = Column(Integer, nullable=False, default=0, comment="下半区得分")
    bonus_score = Column(Integer, nullable=False, default=0, comment="奖励分")
    is_ai = Column(Integer, nullable=False, default=0, comment="是否AI：0-否，1-是")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
