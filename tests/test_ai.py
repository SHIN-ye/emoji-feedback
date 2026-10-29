import httpx
from ai.worker import make_result,send_result

def test_confidence_mapping_and_no_face():
    pred={'emotion':{'happy':85,'sad':15},'face_confidence':0.99}
    row=make_result(pred,3,0.6)
    assert row['emoji']=='happy' and row['confidence']==0.85 and row['session_id']==3
    assert row['event_id'] and row['timestamp'] and 'image' not in row
    assert make_result(pred,3,0.9) is None
    assert make_result({'emotion':{'happy':99},'face_confidence':0},3) is None
    assert make_result({'emotion':{}},3) is None

def test_retry_reuses_event_identifier():
    attempts=[]
    def handler(request):
        attempts.append(request.content)
        return httpx.Response(503 if len(attempts)<3 else 200,json={'code':0,'data':{'accepted':True}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=send_result('http://test','secret',{'event_id':'fixed'},client=client,sleep=lambda _:None)
    assert result=={'accepted':True}
    assert len(attempts)==3 and len(set(attempts))==1

def test_bad_token_is_not_retried():
    calls=[]
    def handler(request):
        calls.append(1); return httpx.Response(401,json={'message':'bad token'})
    import pytest
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError): send_result('http://test','bad',{},client=client,sleep=lambda _:None)
    assert len(calls)==1
