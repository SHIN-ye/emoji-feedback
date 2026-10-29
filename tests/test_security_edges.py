import csv,io
from datetime import datetime,timedelta,timezone
from sqlalchemy import select
from test_api import client,setup,register
from backend.models import User,AuthSession

def test_csv_formula_device_and_filtered_counts(client):
    a,t,s,sid,_=setup(client)
    for emotion in ['happy','happy','sad']:
        assert client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':emotion}).status_code==200
    p={'session_id':sid,'emoji':'fear','confidence':0.75,'event_id':'formula','device_id':'=1+1','timestamp':datetime.now(timezone.utc).isoformat()}
    assert client.post('/api/ai/emoji-results',headers={'X-AI-Token':'ai-secret'},json=p).status_code==200
    stats=client.get('/api/admin/statistics?class=软工一班&source=MANUAL',headers=t).json()['data']
    assert stats['total']==3 and stats['counts']['happy']==2 and stats['participants']==1
    assert client.get('/api/admin/statistics?class=其他班',headers=a).json()['data']['total']==0
    response=client.get('/api/admin/emoji/export',headers=a)
    rows=list(csv.DictReader(io.StringIO(response.text.lstrip('\ufeff'))))
    assert next(r for r in rows if r['source']=='AI')['device_id']=="'=1+1"
    assert client.get('/api/admin/emoji/export',headers=t).status_code==403
    assert client.post('/api/ai/emoji-results',headers={'X-AI-Token':'ai-secret'},json=dict(p,emoji='sad')).status_code==409

def test_storage_and_logout(client):
    a,t,s,sid,_=setup(client)
    with client.app.state.factory() as db:
        user=db.scalar(select(User).where(User.username=='student'))
        stored=db.scalar(select(AuthSession).where(AuthSession.user_id==user.id))
        assert user.password_hash!='Password123!' and user.password_hash.startswith('pbkdf2_sha256$')
        assert stored.token_hash!=s['Authorization'][7:]
    assert client.post('/api/auth/logout',headers=s).status_code==200
    assert client.get('/api/users/me',headers=s).status_code==401
    assert client.post('/api/auth/login',json={'username':"' OR 1=1 --",'password':'Password123!'}).status_code==401

def test_closed_session_rejects_submission(client):
    a,t,s,sid,uid=setup(client)
    course=client.get('/api/courses',headers=a).json()['data'][0]['id']
    now=datetime.now(timezone.utc)
    payload={'course_id':course,'class_name':'closed','start_time':(now-timedelta(hours=2)).isoformat(),'end_time':(now-timedelta(hours=1)).isoformat()}
    sid=client.post('/api/admin/sessions',headers=a,json=payload).json()['data']['id']
    client.post(f'/api/admin/sessions/{sid}/schedule',headers=a,json={'user_ids':[uid]})
    assert client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':'neutral'}).status_code==400
    assert client.post('/api/admin/sessions',headers=a,json=dict(payload,end_time=payload['start_time'])).status_code==400
    assert client.post('/api/admin/sessions',headers=a,json=dict(payload,start_time='2026-10-29T00:00:00')).status_code==422

def test_teacher_cannot_read_other_course_statistics(client):
    a,t,s,sid,_=setup(client); other=register(client,'anotherteacher','teacher')
    client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':'neutral'})
    assert client.get('/api/admin/statistics',headers=other).json()['data']['total']==0
    assert client.get(f'/api/admin/sessions/{sid}/schedule',headers=other).status_code==403
    assert client.get('/api/users/me',headers=s).json()['data'].get('password_hash') is None

def test_unicode_invitation_is_rejected_normally(client):
    response=client.post('/api/auth/register',json={'username':'unicode','password':'Password123!','role':'teacher','invite_code':'中文邀请码'})
    assert response.status_code==403
