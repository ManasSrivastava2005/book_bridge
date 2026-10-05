from datetime import datetime
from sqlalchemy import Integer,String,Text,DateTime,ForeignKey,UniqueConstraint,func
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class Announcement(Base):
    __tablename__='announcements'
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    title:Mapped[str]=mapped_column(String(150))
    message:Mapped[str]=mapped_column(Text)
    category:Mapped[str]=mapped_column(String(40))
    target_kind:Mapped[str]=mapped_column(String(30))
    target_value:Mapped[str|None]=mapped_column(String(120))
    created_by:Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
    sent_at:Mapped[datetime|None]=mapped_column(DateTime)

class AnnouncementDelivery(Base):
    __tablename__='announcement_deliveries'
    __table_args__=(UniqueConstraint('announcement_id','user_id'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    announcement_id:Mapped[int]=mapped_column(ForeignKey('announcements.id'))
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
    notification_id:Mapped[int]=mapped_column(ForeignKey('notifications.id'))
