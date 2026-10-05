from sqlalchemy import Integer,String,ForeignKey,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class AcademicProfile(Base):
    __tablename__='academic_profiles'
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id'),primary_key=True)
    college:Mapped[str|None]=mapped_column(String(200))
    program:Mapped[str|None]=mapped_column(String(120))
    specialization:Mapped[str|None]=mapped_column(String(120))
    curriculum_id:Mapped[int|None]=mapped_column(ForeignKey('curricula.id'))
    subject_ids:Mapped[list]=mapped_column(JSON,default=list)
    custom_subjects:Mapped[list]=mapped_column(JSON,default=list)
    goals:Mapped[str|None]=mapped_column(String(1000))
    daily_minutes:Mapped[int]=mapped_column(Integer,default=60,server_default='60')
