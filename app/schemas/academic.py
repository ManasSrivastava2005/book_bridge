from pydantic import BaseModel,Field,ConfigDict,field_validator
class AcademicWrite(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    college:str|None=Field(None,max_length=200)
    program:str|None=Field(None,max_length=120)
    branch:str|None=Field(None,max_length=100)
    specialization:str|None=Field(None,max_length=120)
    semester:int|None=Field(None,ge=1,le=20)
    curriculum_id:int|None=Field(None,gt=0)
    subject_ids:list[int]=Field(default_factory=list)
    custom_subjects:list[str]=Field(default_factory=list,max_length=50)
    goals:str|None=Field(None,max_length=1000)
    @field_validator('custom_subjects')
    @classmethod
    def subjects(cls,values):
        cleaned=list(dict.fromkeys(v.strip() for v in values if v.strip()))
        if any(len(v)>150 for v in cleaned):raise ValueError('Subject names must be at most 150 characters')
        return cleaned
