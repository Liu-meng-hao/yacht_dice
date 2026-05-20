from sqlalchemy import Column, BigInteger, Integer, DateTime
from sqlalchemy.sql import func
from app.db.session import Base


class UserSetting(Base):
    __tablename__ = "user_setting"
    
    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")
    user_id = Column(BigInteger, nullable=False, comment="关联用户ID")
    sound_enabled = Column(Integer, nullable=False, default=1, comment="音效开关：0-关，1-开")
    rule_popup_enabled = Column(Integer, nullable=False, default=1, comment="规则弹窗开关：0-关，1-开")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
