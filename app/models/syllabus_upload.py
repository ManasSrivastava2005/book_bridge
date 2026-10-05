from datetime import datetime
from sqlalchemy import Integer,String,Text,JSON,DateTime,ForeignKey,UniqueConstraint,func
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class SyllabusUpload(Base):
    __tablename__='syllabus_uploads'
    __table_args__=(UniqueConstraint('user_id','request_key'),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    request_key:Mapped[str]=mapped_column(String(36))
    content_hash:Mapped[str]=mapped_column(String(64))
    filename:Mapped[str]=mapped_column(String(40))
    original_name:Mapped[str]=mapped_column(String(255))
    extracted_text:Mapped[str]=mapped_column(Text)
    proposal:Mapped[dict]=mapped_column(JSON)
    state:Mapped[str]=mapped_column(String(20),default='proposed')
    curriculum_id:Mapped[int|None]=mapped_column(ForeignKey('curricula.id'))
    subject_id:Mapped[int|None]=mapped_column(ForeignKey('curriculum_nodes.id'),nullable=True)
    confirmation_hash:Mapped[str|None]=mapped_column(String(64))
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
    confirmed_at:Mapped[datetime|None]=mapped_column(DateTime)
