import os,hmac
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,Header,Query
from fastapi.responses import JSONResponse,Response,FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from sqlalchemy import create_engine,event,select,delete
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from .models import Base,User,Course,ClassSession,ScheduleUser,AuthSession
from .schemas import Register,Login,Password,CourseInput,SessionInput,ScheduleInput,ManualInput,AIInput,StatusInput,utc
from .services import Service,public,role,fail
from .security import token_hash

def create_app(database_url=None,config=None):
    cfg={'admin_invite':os.getenv('ADMIN_INVITE',''),'teacher_invite':os.getenv('TEACHER_INVITE',''),'ai_token':os.getenv('AI_SERVICE_TOKEN',''),'ai_threshold':float(os.getenv('AI_THRESHOLD','0.6'))}
    cfg.update(config or {})
    if not 0<=cfg['ai_threshold']<=1: raise ValueError('AI_THRESHOLD must be within [0,1]')
    url=database_url or os.getenv('DATABASE_URL','sqlite:///./emoji.db')
    engine=create_engine(url,connect_args={'check_same_thread':False} if url.startswith('sqlite') else {})
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def enable_fk(conn,_): conn.execute('PRAGMA foreign_keys=ON')
    factory=sessionmaker(engine,expire_on_commit=False)
    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()
    app=FastAPI(title='课堂情绪检查器 API',version='1.0.0',lifespan=lifespan)
    app.state.factory=factory; app.state.config=cfg; app.state.engine=engine
    @app.exception_handler(HTTPException)
    async def http_error(req,exc): return JSONResponse({'code':exc.status_code,'message':str(exc.detail)},status_code=exc.status_code)
    @app.exception_handler(RequestValidationError)
    async def validation(req,exc): return JSONResponse({'code':422,'message':'输入不符合要求，请检查字段、密码强度和时间格式'},status_code=422)
    @app.exception_handler(IntegrityError)
    async def conflict(req,exc): return JSONResponse({'code':409,'message':'数据冲突，请刷新后重试'},status_code=409)
    @app.middleware('http')
    async def headers(req,call_next):
        response=await call_next(req)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'" if not req.url.path.startswith('/docs') else "frame-ancestors 'none'"
        if req.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
        return response
    def service():
        with factory() as db: yield Service(db,cfg)
    def current(authorization:str=Header(default=''),s:Service=Depends(service)):
        if not authorization.startswith('Bearer '): fail(401,'请先登录')
        return s.authenticate(authorization[7:])
    def filters(sessionId:int|None=None,course:int|None=None,class_name:str|None=Query(None,alias='class'),start:datetime|None=Query(None,alias='from'),end:datetime|None=Query(None,alias='to'),source:str|None=None):
        try: start=utc(start) if start else None; end=utc(end) if end else None
        except ValueError: fail(400,'筛选时间必须包含时区')
        if start and end and start>end: fail(400,'开始时间不能晚于结束时间')
        if source not in (None,'AI','MANUAL'): fail(400,'来源无效')
        return dict(session_id=sessionId,course=course,class_name=class_name,start=start,end=end,source=source)
    def ok(data=None): return {'code':0,'data':data}
    @app.get('/api/health')
    def health(): return ok({'status':'ok'})
    @app.post('/api/auth/register')
    def register(p:Register,s:Service=Depends(service)): return ok(s.register(p))
    @app.post('/api/auth/login')
    def login(p:Login,s:Service=Depends(service)): return ok(s.login(p))
    @app.post('/api/auth/logout')
    def logout(authorization:str=Header(default=''),u=Depends(current),s:Service=Depends(service)):
        s.db.execute(delete(AuthSession).where(AuthSession.token_hash==token_hash(authorization[7:]))); s.db.commit(); return ok()
    @app.put('/api/auth/password')
    def password(p:Password,u=Depends(current),s:Service=Depends(service)): s.password(u,p); return ok()
    @app.get('/api/users/me')
    def me(u=Depends(current)): return ok(public(u))
    @app.get('/api/admin/users')
    def users(u=Depends(current),s:Service=Depends(service)):
        role(u,'admin'); return ok([public(x) for x in s.db.scalars(select(User).order_by(User.id)).all()])
    @app.patch('/api/admin/users/{uid}')
    def status(uid:int,p:StatusInput,u=Depends(current),s:Service=Depends(service)):
        role(u,'admin')
        if uid==u.id: fail(400,'不能更改当前账户状态')
        target=s.db.get(User,uid)
        if not target: fail(404,'用户不存在')
        target.status=p.status
        if p.status=='disabled': s.db.execute(delete(AuthSession).where(AuthSession.user_id==uid))
        s.audit(u,f'user_status:{uid}:{p.status}'); s.db.commit(); return ok(public(target))
    @app.get('/api/courses')
    def courses(u=Depends(current),s:Service=Depends(service)):
        q=select(Course)
        if u.role=='teacher': q=q.where(Course.teacher_id==u.id)
        if u.role=='student': q=q.where(Course.id.in_([x.course_id for x in s.repo.sessions(u)]))
        return ok([public(x) for x in s.db.scalars(q).all()])
    @app.post('/api/admin/courses')
    def add_course(p:CourseInput,u=Depends(current),s:Service=Depends(service)):
        role(u,'admin'); teacher=s.db.get(User,p.teacher_id)
        if not teacher or teacher.role!='teacher' or teacher.status!='active': fail(400,'授课人必须是有效教师')
        row=Course(**p.model_dump()); s.db.add(row); s.db.commit(); return ok(public(row))
    @app.get('/api/sessions')
    def sessions(u=Depends(current),s:Service=Depends(service)):
        return ok([{**public(x),'course_name':s.db.get(Course,x.course_id).name} for x in s.repo.sessions(u)])
    @app.post('/api/admin/sessions')
    def add_session(p:SessionInput,u=Depends(current),s:Service=Depends(service)):
        role(u,'admin')
        if p.end_time<=p.start_time: fail(400,'结束时间必须晚于开始时间')
        if not s.db.get(Course,p.course_id): fail(404,'课程不存在')
        row=ClassSession(**p.model_dump()); s.db.add(row); s.db.commit(); return ok(public(row))
    @app.post('/api/admin/sessions/{sid}/schedule')
    def schedule(sid:int,p:ScheduleInput,u=Depends(current),s:Service=Depends(service)): return ok(s.schedule(u,sid,p))
    @app.get('/api/admin/sessions/{sid}/schedule')
    def get_schedule(sid:int,u=Depends(current),s:Service=Depends(service)):
        role(u,'admin','teacher'); s.session(u,sid)
        return ok([{**public(x),'username':s.db.get(User,x.user_id).username} for x in s.db.scalars(select(ScheduleUser).where(ScheduleUser.session_id==sid)).all()])
    @app.post('/api/emoji')
    def emoji(p:ManualInput,u=Depends(current),s:Service=Depends(service)): return ok(s.record(u,p))
    @app.get('/api/emoji/history')
    def history(u=Depends(current),s:Service=Depends(service),f=Depends(filters),limit:int=Query(200,ge=1,le=1000),offset:int=Query(0,ge=0)):
        return ok([public(x) for x in s.repo.records(u,**f)[offset:offset+limit]])
    @app.get('/api/emoji/statistics')
    def basic_stats(u=Depends(current),s:Service=Depends(service),f=Depends(filters)): return ok(s.statistics(u,**f))
    @app.get('/api/admin/statistics')
    def stats(u=Depends(current),s:Service=Depends(service),f=Depends(filters)):
        role(u,'admin','teacher'); return ok(s.statistics(u,**f))
    @app.get('/api/admin/dashboard/realtime')
    def dashboard(sessionId:int,u=Depends(current),s:Service=Depends(service)):
        role(u,'admin','teacher'); s.session(u,sessionId); return ok(s.statistics(u,session_id=sessionId))
    @app.get('/api/admin/emoji/export')
    def export(u=Depends(current),s:Service=Depends(service),f=Depends(filters),format:str='csv'):
        if format!='csv': fail(400,'仅支持 CSV')
        return Response(s.export(u,**f),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename=emoji-records.csv'})
    @app.post('/api/ai/emoji-results')
    def ai(p:AIInput,x_ai_token:str=Header(default=''),s:Service=Depends(service)):
        if not cfg['ai_token'] or not hmac.compare_digest(x_ai_token.encode(),cfg['ai_token'].encode()): fail(401,'AI 服务认证失败')
        return ok(s.ai_record(p))
    web=Path(__file__).resolve().parent.parent/'web'
    if web.exists():
        app.mount('/static',StaticFiles(directory=web),name='static')
        @app.get('/',include_in_schema=False)
        def home(): return FileResponse(web/'index.html')
    return app
app=create_app()
