from sqlalchemy import Column, BigInteger, String, DateTime, Integer
from sqlalchemy.sql import func
from app.db.session import Base


class User(Base):
    __tablename__ = "user"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    client_id = Column(String(100), unique=True, index=True, nullable=False, comment="客户端ID（匿名用户标识）")
    user_type = Column(Integer, nullable=False, default=1, comment="用户类型：1-真实玩家，2-AI")
    ai_difficulty = Column(Integer, nullable=True, comment="AI难度：1-简单，2-中等，3-困难")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    nickname = Column(String(50), nullable=True, comment="昵称")
    points = Column(Integer, nullable=False, default=0, comment="积分")
    total_games = Column(Integer, nullable=False, default=0, comment="总游戏次数")
    total_wins = Column(Integer, nullable=False, default=0, comment="总胜利次数")
    highest_score = Column(Integer, nullable=False, default=0, comment="最高分")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
    last_play_time = Column(DateTime, nullable=True, comment="最后游戏时间")
    is_deleted = Column(Integer, nullable=False, default=0, comment="是否删除：0-未删除，1-已删除")
