from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f'sqlite:///{tmp_path}/test.db', {'admin_invite':'admin-secret','teacher_invite':'teacher-secret','ai_token':'ai-secret'})) as c:
        yield c

def register(c, name, role='student'):
    r=c.post('/api/auth/register',json={'username':name,'password':'Password123!','role':role,'invite_code':f'{role}-secret'})
    assert r.status_code==200,r.text
    r=c.post('/api/auth/login',json={'username':name,'password':'Password123!'})
    return {'Authorization':'Bearer '+r.json()['data']['token']}

def setup(c):
    admin=register(c,'admin','admin'); teacher=register(c,'teacher','teacher'); student=register(c,'student')
    users=c.get('/api/admin/users',headers=admin).json()['data']
    uid=next(u['id'] for u in users if u['username']=='student'); tid=next(u['id'] for u in users if u['username']=='teacher')
    course=c.post('/api/admin/courses',headers=admin,json={'name':'软件工程','teacher_id':tid}).json()['data']['id']
    now=datetime.now(timezone.utc)
    sid=c.post('/api/admin/sessions',headers=admin,json={'course_id':course,'class_name':'软工一班','room':'A101','start_time':(now-timedelta(hours=1)).isoformat(),'end_time':(now+timedelta(hours=2)).isoformat()}).json()['data']['id']
    assert c.post(f'/api/admin/sessions/{sid}/schedule',headers=admin,json={'user_ids':[uid]}).status_code==200
    return admin,teacher,student,sid,uid

def test_registration_cannot_elevate_or_use_weak_password(client):
    assert client.post('/api/auth/register',json={'username':'evil','password':'Password123!','role':'admin'}).status_code==403
    assert client.post('/api/auth/register',json={'username':'weak','password':'123'}).status_code==422

def test_manual_flow_and_scoped_history(client):
    a,t,s,sid,_=setup(client)
    outsider=register(client,'outsider'); other_teacher=register(client,'teacher2','teacher')
    assert client.post('/api/emoji',headers=outsider,json={'session_id':sid,'emoji':'happy'}).status_code==403
    assert client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':'happy'}).status_code==200
    assert len(client.get('/api/emoji/history',headers=s).json()['data'])==1
    assert client.get('/api/emoji/history',headers=outsider).json()['data']==[]
    assert client.get('/api/emoji/history',headers=other_teacher).json()['data']==[]
    assert client.get('/api/admin/users',headers=s).status_code==403
    assert client.get(f'/api/admin/dashboard/realtime?sessionId={sid}',headers=other_teacher).status_code==403
    data=client.get(f'/api/admin/dashboard/realtime?sessionId={sid}',headers=t).json()['data']
    assert data['counts']['happy']==1 and data['participants']==1
    assert 'happy' in client.get('/api/admin/emoji/export',headers=a).text

def test_password_rotation_and_disabled_user(client):
    a,t,s,sid,uid=setup(client)
    assert client.put('/api/auth/password',headers=s,json={'old_password':'wrong','new_password':'NewPassword123'}).status_code==400
    assert client.put('/api/auth/password',headers=s,json={'old_password':'Password123!','new_password':'NewPassword123'}).status_code==200
    assert client.get('/api/users/me',headers=s).status_code==401
    fresh=client.post('/api/auth/login',json={'username':'student','password':'NewPassword123'}).json()['data']['token']
    assert client.patch(f'/api/admin/users/{uid}',headers=a,json={'status':'disabled'}).status_code==200
    assert client.get('/api/users/me',headers={'Authorization':'Bearer '+fresh}).status_code==401

def test_ai_auth_threshold_and_idempotency(client):
    a,t,s,sid,_=setup(client)
    payload={'session_id':sid,'emoji':'sad','confidence':0.9,'event_id':'camera-event-1','device_id':'cam1','timestamp':datetime.now(timezone.utc).isoformat()}
    assert client.post('/api/ai/emoji-results',headers=s,json=payload).status_code==401
    headers={'X-AI-Token':'ai-secret'}
    low=dict(payload,confidence=0.2,event_id='low')
    assert client.post('/api/ai/emoji-results',headers=headers,json=low).json()['data']['accepted'] is False
    for _ in range(2):
        assert client.post('/api/ai/emoji-results',headers=headers,json=payload).status_code==200
    rows=client.get('/api/emoji/history',headers=t).json()['data']
    assert len(rows)==1 and rows[0]['user_id'] is None and rows[0]['source']=='AI'
    assert client.get('/api/emoji/history',headers=s).json()['data']==[]
    assert client.get('/api/admin/statistics?source=MANUAL',headers=a).json()['data']['total']==0

def test_invalid_sessions_and_future_schedule(client):
    a,t,s,sid,uid=setup(client)
    future=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    assert client.post(f'/api/admin/sessions/{sid}/schedule',headers=a,json={'user_ids':[uid],'scheduled_at':future}).status_code==200
    assert client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':'happy'}).status_code==403
    assert client.post('/api/emoji',headers=s,json={'session_id':sid,'emoji':'madeup'}).status_code==422
    assert client.get('/api/admin/statistics?from=2026-12-01T00:00:00Z&to=2026-01-01T00:00:00Z',headers=a).status_code==400
