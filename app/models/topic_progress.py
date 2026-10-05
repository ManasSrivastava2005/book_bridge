from datetime import datetime
from sqlalchemy import ForeignKey,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class TopicProgress(Base):
    __tablename__='topic_progress'
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),primary_key=True)
    topic_id:Mapped[int]=mapped_column(ForeignKey('curriculum_nodes.id'),primary_key=True)
    completed_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
