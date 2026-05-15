from sqlalchemy import Column, BigInteger, Integer, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.db.session import Base


class GameRound(Base):
    __tablename__ = "game_round"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    game_id = Column(BigInteger, ForeignKey("game.id"), nullable=False, comment="游戏ID")
    round_number = Column(Integer, nullable=False, comment="回合数（1-13）")
    current_player_id = Column(BigInteger, ForeignKey("user.id"), nullable=False, comment="当前玩家ID")
    dice_data = Column(JSON, nullable=True, comment="骰子数据（JSON数组）")
    reroll_count = Column(Integer, nullable=False, default=0, comment="重掷次数（0-2）")
    round_status = Column(Integer, nullable=False, default=2, comment="回合状态：1-待开始，2-进行中，3-已完成")
    start_time = Column(DateTime, server_default=func.now(), comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
