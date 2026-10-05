from datetime import datetime
from sqlalchemy import Integer,String,DateTime,ForeignKey,func
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class ResourceUsage(Base):
    """Request events; not evidence of completed reading or a completed transfer."""
    __tablename__='resource_usage'
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    resource_kind:Mapped[str]=mapped_column(String(30),index=True)
    resource_id:Mapped[int]=mapped_column(Integer,index=True)
    title:Mapped[str]=mapped_column(String(255))
    user_id:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    action:Mapped[str]=mapped_column(String(30),default='download_request')
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now(),index=True)
