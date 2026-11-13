from ai.worker import process_frame
from test_api import client, setup


def test_frame_to_database_and_teacher_dashboard(client):
    _, teacher, _, sid, _ = setup(client)
    frame = object()
    def analyze(actual, **kwargs):
        assert actual is frame and kwargs['enforce_detection']
        return [{'face_confidence': 1, 'emotion': {emotion: 95}} for emotion in
                ('happy', 'neutral', 'sad', 'angry', 'surprise', 'fear', 'disgust')]
    results = process_frame(frame, sid, .6, 'integration-camera', analyze,
                            'http://testserver', 'ai-secret', client)
    assert len(results) == 7 and all(r['accepted'] for r in results)
    rows = client.get('/api/emoji/history', headers=teacher).json()['data']
    assert len(rows) == 7
    assert all(r['source'] == 'AI' and r['user_id'] is None and r['confidence'] == .95 for r in rows)
    dashboard = client.get('/api/admin/dashboard/realtime', params={'sessionId': sid}, headers=teacher).json()['data']
    assert dashboard['total'] == 7 and dashboard['sources']['AI'] == 7
    assert dashboard['participants'] == 0


def test_frame_without_face_does_not_write(client):
    _, teacher, _, sid, _ = setup(client)
    def no_face(frame, **kwargs):
        raise ValueError('Face could not be detected')
    assert process_frame(object(), sid, .6, 'camera', no_face, 'http://testserver', 'ai-secret', client) == []
    def low_confidence(frame, **kwargs):
        return {'face_confidence': 1, 'emotion': {'sad': 40}}
    assert process_frame(object(), sid, .6, 'camera', low_confidence, 'http://testserver', 'ai-secret', client) == []
    assert client.get('/api/emoji/history', headers=teacher).json()['data'] == []
