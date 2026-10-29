import csv,io,secrets,hmac
from collections import Counter,defaultdict
from datetime import timedelta,datetime
from fastapi import HTTPException
from sqlalchemy import select,delete
from .models import User,ClassSession,ScheduleUser,EmojiRecord,AuthSession,AuditLog,now
from .security import hash_password,verify_password,token_hash
from .repository import Repository
EMOJIS=['happy','neutral','sad','angry','surprise','fear','disgust']
def fail(code,message): raise HTTPException(code,message)
def public(obj):
    return {c.name:(getattr(obj,c.name).isoformat()+'Z' if isinstance(getattr(obj,c.name),datetime) else getattr(obj,c.name)) for c in obj.__table__.columns if c.name not in ('password_hash','token_hash')}
def role(user,*allowed):
    if user.role not in allowed: fail(403,'无权执行此操作')
def csv_safe(value):
    s='' if value is None else str(value)
    return "'"+s if s.lstrip().startswith(('=','+','-','@')) or s.startswith(('\t','\r','\n')) else s
class Service:
    def __init__(self,db,config): self.db=db; self.config=config; self.repo=Repository(db)
    def audit(self,user,action): self.db.add(AuditLog(user_id=user.id if user else None,action=action))
    def register(self,p):
        if p.role!='student':
            expected=self.config.get(p.role+'_invite','')
            if not expected or not hmac.compare_digest(p.invite_code.encode(),expected.encode()): fail(403,'该角色需要有效邀请码')
        if self.db.scalar(select(User).where(User.username==p.username)): fail(409,'用户名已存在')
        user=User(username=p.username,password_hash=hash_password(p.password),role=p.role,email=p.email)
        self.db.add(user); self.db.flush(); self.audit(user,'register'); self.db.commit(); return public(user)
    def login(self,p):
        user=self.db.scalar(select(User).where(User.username==p.username))
        if not user:
            hash_password(p.password); fail(401,'用户名或密码错误')
        if not verify_password(p.password,user.password_hash) or user.status!='active': fail(401,'用户名或密码错误或账户已停用')
        token=secrets.token_urlsafe(32)
        self.db.add(AuthSession(token_hash=token_hash(token),user_id=user.id,expires_at=now()+timedelta(hours=8)))
        self.audit(user,'login'); self.db.commit(); return {'token':token,'user':public(user)}
    def authenticate(self,token):
        session=self.db.get(AuthSession,token_hash(token))
        if not session or session.expires_at<=now(): fail(401,'登录已失效，请重新登录')
        user=self.db.get(User,session.user_id)
        if user.status!='active': fail(401,'账户已停用')
        return user
    def password(self,user,p):
        if not verify_password(p.old_password,user.password_hash): fail(400,'原密码错误')
        user.password_hash=hash_password(p.new_password)
        self.db.execute(delete(AuthSession).where(AuthSession.user_id==user.id)); self.audit(user,'password_changed'); self.db.commit()
    def session(self,user,sid):
        session=self.db.get(ClassSession,sid)
        if not session: fail(404,'课堂不存在')
        if not self.db.scalar(self.repo.sessions_query(user).where(ClassSession.id==sid)): fail(403,'无权访问该课堂')
        return session
    def schedule(self,user,sid,p):
        role(user,'admin'); self.session(user,sid)
        students=self.db.scalars(select(User).where(User.id.in_(p.user_ids))).all()
        if len(students)!=len(set(p.user_ids)) or any(u.role!='student' or u.status!='active' for u in students): fail(400,'只能安排有效学生账户')
        for uid in set(p.user_ids):
            row=self.db.scalar(select(ScheduleUser).where(ScheduleUser.session_id==sid,ScheduleUser.user_id==uid))
            if not row: row=ScheduleUser(session_id=sid,user_id=uid); self.db.add(row)
            row.scheduled_at=p.scheduled_at or now()
        self.audit(user,f'schedule:{sid}'); self.db.commit(); return {'count':len(set(p.user_ids))}
    def record(self,user,p):
        role(user,'student'); session=self.session(user,p.session_id); current=now()
        schedule=self.db.scalar(select(ScheduleUser).where(ScheduleUser.session_id==session.id,ScheduleUser.user_id==user.id))
        if schedule.scheduled_at>current: fail(403,'课堂安排尚未生效')
        if not session.start_time<=current<=session.end_time: fail(400,'当前不在课堂时间内')
        row=EmojiRecord(user_id=user.id,session_id=session.id,emoji=p.emoji,source='MANUAL',timestamp=current)
        self.db.add(row); self.db.commit(); return public(row)
    def ai_record(self,p):
        old=self.db.scalar(select(EmojiRecord).where(EmojiRecord.event_id==p.event_id))
        if old:
            if any(getattr(old,k)!=getattr(p,k) for k in ('session_id','emoji','confidence','device_id','timestamp')): fail(409,'事件编号已用于其他结果')
            return {'accepted':True,'duplicate':True,'id':old.id}
        session=self.db.get(ClassSession,p.session_id)
        if not session: fail(404,'课堂不存在')
        if not session.start_time<=p.timestamp<=session.end_time or p.timestamp>now()+timedelta(minutes=1): fail(400,'AI 时间不在课堂范围内')
        if p.confidence<self.config['ai_threshold']: return {'accepted':False,'reason':'low_confidence'}
        row=EmojiRecord(**p.model_dump(),source='AI'); self.db.add(row); self.db.commit()
        return {'accepted':True,'duplicate':False,'id':row.id}
    def statistics(self,user,**filters):
        rows=self.repo.records(user,**filters); counts=Counter(r.emoji for r in rows); timeline=defaultdict(Counter)
        for r in rows: timeline[r.timestamp.replace(second=0,microsecond=0).isoformat()+'Z'][r.emoji]+=1
        return {'total':len(rows),'participants':len({r.user_id for r in rows if r.source=='MANUAL'}),'counts':{k:counts[k] for k in EMOJIS},'sources':dict(Counter(r.source for r in rows)),'timeline':[{'time':t,**{k:c[k] for k in EMOJIS}} for t,c in sorted(timeline.items())],'updated_at':now().isoformat()+'Z'}
    def export(self,user,**filters):
        role(user,'admin'); buf=io.StringIO(); writer=csv.writer(buf)
        fields=['id','user_id','session_id','emoji','timestamp','source','confidence','device_id']; writer.writerow(fields)
        for row in self.repo.records(user,**filters):
            data=public(row); writer.writerow([csv_safe(data[k]) for k in fields])
        self.audit(user,'csv_export'); self.db.commit(); return '\ufeff'+buf.getvalue()
