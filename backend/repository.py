from sqlalchemy import select
from .models import Course, ClassSession, ScheduleUser, EmojiRecord
class Repository:
    def __init__(self,db): self.db=db
    def sessions_query(self,user):
        q=select(ClassSession).join(Course)
        if user.role=='teacher': q=q.where(Course.teacher_id==user.id)
        if user.role=='student': q=q.join(ScheduleUser).where(ScheduleUser.user_id==user.id)
        return q
    def sessions(self,user): return self.db.scalars(self.sessions_query(user).order_by(ClassSession.start_time.desc())).all()
    def records(self,user,session_id=None,course=None,class_name=None,start=None,end=None,source=None):
        q=select(EmojiRecord).join(ClassSession).join(Course)
        if user.role=='student': q=q.where(EmojiRecord.user_id==user.id)
        if user.role=='teacher': q=q.where(Course.teacher_id==user.id)
        if session_id is not None: q=q.where(EmojiRecord.session_id==session_id)
        if course is not None: q=q.where(Course.id==course)
        if class_name: q=q.where(ClassSession.class_name==class_name)
        if start: q=q.where(EmojiRecord.timestamp>=start)
        if end: q=q.where(EmojiRecord.timestamp<=end)
        if source: q=q.where(EmojiRecord.source==source)
        return self.db.scalars(q.order_by(EmojiRecord.timestamp.desc(),EmojiRecord.id.desc())).all()
