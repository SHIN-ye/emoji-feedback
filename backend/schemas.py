from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
Emoji=Literal['happy','neutral','sad','angry','surprise','fear','disgust']
Role=Literal['student','teacher','admin']
def utc(value):
    if value.tzinfo is None: raise ValueError('时间必须包含时区')
    return value.astimezone(timezone.utc).replace(tzinfo=None)
def strong(value):
    if len(value)<10 or not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value): raise ValueError('密码至少10位且包含字母和数字')
    return value
class Input(BaseModel):
    model_config=ConfigDict(extra='forbid')
class Register(Input):
    username:str=Field(min_length=3,max_length=50,pattern=r'^[\w.-]+$')
    password:str=Field(max_length=128)
    role:Role='student'
    email:str=Field(default='',max_length=254)
    invite_code:str=Field(default='',max_length=200)
    _password=field_validator('password')(strong)
class Login(Input):
    username:str=Field(max_length=50)
    password:str=Field(max_length=128)
class Password(Input):
    old_password:str=Field(max_length=128)
    new_password:str=Field(max_length=128)
    _password=field_validator('new_password')(strong)
class CourseInput(Input):
    name:str=Field(min_length=1,max_length=120)
    teacher_id:int=Field(gt=0)
class SessionInput(Input):
    course_id:int=Field(gt=0)
    class_name:str=Field(min_length=1,max_length=80)
    room:str=Field(default='',max_length=80)
    start_time:datetime
    end_time:datetime
    _times=field_validator('start_time','end_time')(utc)
class ScheduleInput(Input):
    user_ids:list[int]=Field(min_length=1,max_length=500)
    scheduled_at:datetime|None=None
    @field_validator('scheduled_at')
    @classmethod
    def check_time(cls,v): return utc(v) if v else v
class ManualInput(Input):
    session_id:int=Field(gt=0)
    emoji:Emoji
class AIInput(ManualInput):
    confidence:float=Field(ge=0,le=1,allow_inf_nan=False)
    timestamp:datetime
    device_id:str=Field(min_length=1,max_length=100)
    event_id:str=Field(min_length=1,max_length=100)
    _time=field_validator('timestamp')(utc)
class StatusInput(Input):
    status:Literal['active','disabled']
