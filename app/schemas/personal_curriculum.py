from pydantic import BaseModel,ConfigDict,Field,model_validator

class PersonalNode(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    id:int|None=Field(None,gt=0)
    title:str=Field(min_length=1,max_length=200)
    code:str|None=Field(None,max_length=50)
    objectives:str|None=Field(None,max_length=2000)
    subtopics:list[str]=Field(default_factory=list,max_length=50)
    children:list['PersonalNode']=Field(default_factory=list,max_length=100)

class PersonalCurriculumWrite(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    curriculum_id:int|None=Field(None,gt=0)
    expected_version:int=Field(0,ge=0)
    semester:int|None=Field(None,ge=1,le=20)
    title:str=Field(min_length=1,max_length=200)
    subjects:list[PersonalNode]=Field(default_factory=list)

    @model_validator(mode='after')
    def bounded_tree(self):
        ids=set()
        def visit(nodes,depth):
            for node in nodes:
                if node.id in ids:raise ValueError('A node cannot appear twice')
                if node.id:ids.add(node.id)
                if any(not s.strip() or len(s)>300 for s in node.subtopics):raise ValueError('Subtopics must be nonblank and at most 300 characters')
                if depth==2 and node.children:raise ValueError('Use subject, unit and topic levels only')
                visit(node.children,depth+1)
        visit(self.subjects,0)
        return self
