from sqlalchemy import Column, BigInteger, String, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class OnlineRoom(Base):
    __tablename__ = "online_room"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    room_code = Column(String(10), unique=True, nullable=False, comment="房间编码")
    room_name = Column(String(100), nullable=True, comment="房间名称")
    owner_id = Column(BigInteger, ForeignKey("user.id"), nullable=True, comment="房主ID（废弃，使用host_id）")
    host_id = Column(String(100), nullable=True, comment="房主ID（字符串UUID）")
    max_player_count = Column(Integer, nullable=False, default=4, comment="最大玩家数")
    current_player_count = Column(Integer, nullable=False, default=1, comment="当前玩家数")
    room_status = Column(Integer, nullable=False, default=1, comment="房间状态：1-等待，2-游戏中，3-已解散")
    game_id = Column(BigInteger, nullable=True, comment="关联的游戏ID")
    game_mode = Column(String(20), nullable=False, default="online", comment="游戏模式：local-本地多人，ai-人机对战，online-在线联机")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
    is_deleted = Column(Integer, nullable=False, default=0, comment="是否删除：0-正常，1-删除")

    players = relationship("RoomPlayer", back_populates="room", cascade="all, delete-orphan")