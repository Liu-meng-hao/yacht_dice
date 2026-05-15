from sqlalchemy import Column, BigInteger, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from app.db.session import Base


class Game(Base):
    __tablename__ = "game"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="对局唯一ID")
    game_mode = Column(Integer, nullable=False, comment="游戏模式：1-本地，2-人机，3-联机")
    room_id = Column(BigInteger, ForeignKey("online_room.id"), nullable=True, comment="联机房间ID")
    player_count = Column(Integer, nullable=False, comment="玩家总数")
    total_rounds = Column(Integer, nullable=False, default=13, comment="固定13轮")
    game_status = Column(Integer, nullable=False, default=1, comment="游戏状态：1-准备，2-进行，3-结束，4-退出")
    winner_id = Column(BigInteger, ForeignKey("user.id"), nullable=True, comment="胜利玩家ID")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    is_deleted = Column(Integer, nullable=False, default=0, comment="是否删除：0-正常，1-删除")
