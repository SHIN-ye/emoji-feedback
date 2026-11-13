"""Explicit camera acceptance run. Uses an isolated DB; never saves camera frames."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
import httpx
import uvicorn
from backend.main import create_app


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--duration', type=float, default=20)
    p.add_argument('--source', default='0')
    p.add_argument('--capture-stdin', action='store_true')
    args = p.parse_args()
    output = Path('artifacts') / ('ai-camera-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    output.mkdir(parents=True)
    token = secrets.token_urlsafe(32) + 'A1'
    app = create_app('sqlite:///' + (output / 'verification.db').resolve().as_posix(),
                     {'admin_invite': token, 'teacher_invite': token, 'ai_token': token})
    import socket
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning'))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{port}'
    try:
        for _ in range(100):
            if server.started: break
            time.sleep(.1)
        with httpx.Client(base_url=base, timeout=30) as client:
            def data(method, path, **kwargs):
                response = client.request(method, path, **kwargs)
                response.raise_for_status()
                return response.json()['data']
            accounts = {}
            for role in ('admin', 'teacher'):
                user = data('POST', '/api/auth/register', json={'username':role, 'password':token, 'role':role, 'invite_code':token})
                login = data('POST', '/api/auth/login', json={'username':role, 'password':token})
                accounts[role] = (user['id'], {'Authorization':'Bearer ' + login['token']})
            admin = accounts['admin'][1]
            course = data('POST', '/api/admin/courses', headers=admin, json={'name':'Camera acceptance', 'teacher_id':accounts['teacher'][0]})
            now = datetime.now(timezone.utc)
            session = data('POST', '/api/admin/sessions', headers=admin, json={'course_id':course['id'], 'class_name':'AI verification', 'room':'local', 'start_time':(now-timedelta(minutes=1)).isoformat(), 'end_time':(now+timedelta(hours=2)).isoformat()})
            env = dict(os.environ, AI_SERVICE_TOKEN=token)
            with (output / 'worker.log').open('w', encoding='utf-8') as log:
                command = [sys.executable, '-m', 'ai.worker', '--source', args.source,
                           '--session', str(session['id']), '--url', base, '--duration', str(args.duration)]
                if args.capture_stdin:
                    command.append('--capture-stdin')
                run = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
            records = data('GET', '/api/emoji/history', headers=accounts['teacher'][1])
            dashboard = data('GET', '/api/admin/dashboard/realtime', headers=accounts['teacher'][1], params={'sessionId':session['id']})
            report = {'worker_exit':run.returncode, 'records':records, 'dashboard':dashboard, 'passed':run.returncode == 0 and len(records)>0 and dashboard['sources'].get('AI')==len(records)}
            (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'output':str(output), 'passed':report['passed'], 'AI_records':len(records)}))
            return 0 if report['passed'] else 1
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()

if __name__ == '__main__':
    raise SystemExit(main())
