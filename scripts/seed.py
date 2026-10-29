"""Explicit demo initializer; never runs on application startup."""
import argparse,secrets,os
from datetime import timedelta
from sqlalchemy import select
from backend.main import app
from backend.models import Base,User,Course,ClassSession,ScheduleUser,EmojiRecord,now
from backend.security import hash_password

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true');args=parser.parse_args()
    if not args.demo: parser.error('Use --demo for local demonstration accounts only')
    Base.metadata.create_all(app.state.engine)
    with app.state.factory() as db:
        if db.scalar(select(User).where(User.username=='admin')):
            print('Demo admin already exists; no accounts or passwords changed.');return
        password=os.getenv('DEMO_PASSWORD') or 'Demo'+secrets.token_urlsafe(12)+'9'
        accounts=[]
        for name,role in [('admin','admin'),('teacher','teacher'),('student','student'),('student2','student')]:
            user=User(username=name,role=role,password_hash=hash_password(password),email=f'{name}@example.test');db.add(user);db.flush();accounts.append(user)
        course=Course(name='软件工程实践',teacher_id=accounts[1].id);db.add(course);db.flush()
        session=ClassSession(course_id=course.id,class_name='软工一班',room='教学楼 A301',start_time=now()-timedelta(hours=1),end_time=now()+timedelta(hours=12));db.add(session);db.flush()
        for student in accounts[2:]: db.add(ScheduleUser(session_id=session.id,user_id=student.id,scheduled_at=now()-timedelta(hours=1)))
        for i,emotion in enumerate(['happy','neutral','happy','surprise','sad','happy','neutral','happy','fear','happy','surprise','neutral']):
            db.add(EmojiRecord(user_id=accounts[2+i%2].id,session_id=session.id,emoji=emotion,source='MANUAL',timestamp=now()-timedelta(minutes=24-i*2),device_id='DEMO_SYNTHETIC'))
        db.commit()
    print('DEMO ONLY: admin / teacher / student / student2')
    print('Temporary demo password: '+password)
    print('Synthetic records are marked DEMO_SYNTHETIC. Classroom lasts 12 hours; create a new session later.')

if __name__=='__main__': main()
