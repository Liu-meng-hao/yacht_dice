from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.session import Base


class GameRecord(Base):
    __tablename__ = "game_records"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    game_id = Column(String(64), unique=True, index=True, nullable=False)
    game_mode = Column(String(20), nullable=False)
    players = Column(JSON, nullable=False)
    scores = Column(JSON, nullable=False)
    winner = Column(String(50), nullable=True)
    status = Column(String(20), default="in_progress")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
