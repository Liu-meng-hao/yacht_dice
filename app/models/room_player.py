from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class RoomPlayer(Base):
    __tablename__ = "room_player"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    room_id = Column(BigInteger, ForeignKey("online_room.id"), nullable=False, comment="房间ID")
    user_id = Column(BigInteger, ForeignKey("user.id"), nullable=False, comment="用户ID（关联user表）")
    client_id = Column(String(100), nullable=False, comment="客户端ID")
    player_name = Column(String(50), nullable=False, comment="玩家名称")
    is_host = Column(Boolean, nullable=False, default=False, comment="是否房主")
    create_time = Column(DateTime, server_default=func.now(), comment="加入时间")

    room = relationship("OnlineRoom", back_populates="players")
    user = relationship("User")