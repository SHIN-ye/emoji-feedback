"""Independent, explicitly launched camera/video worker. Never writes frames to disk."""
import argparse,logging,os,time,uuid,math
from datetime import datetime,timezone
import httpx
LOG=logging.getLogger('emoji.ai')
EMOTIONS={'happy','neutral','sad','angry','surprise','fear','disgust'}

def make_result(prediction,session_id,threshold=0.6,device_id='camera-1',timestamp=None):
    if prediction.get('face_confidence',0)<=0: return None
    scores=prediction.get('emotion',{})
    if not scores: return None
    emotion=max(scores,key=scores.get)
    confidence=float(scores[emotion])/100
    if emotion not in EMOTIONS or not math.isfinite(confidence) or not threshold<=confidence<=1: return None
    return {'session_id':session_id,'emoji':emotion,'confidence':confidence,'timestamp':timestamp or datetime.now(timezone.utc).isoformat(),'device_id':device_id,'event_id':str(uuid.uuid4())}

def send_result(url,token,payload,client=None,sleep=None):
    sleep=sleep or time.sleep
    if client is None:
        with httpx.Client(timeout=15) as own: return send_result(url,token,payload,own,sleep)
    for attempt in range(3):
        try:
            response=client.post(url.rstrip('/')+'/api/ai/emoji-results',headers={'X-AI-Token':token},json=payload)
            response.raise_for_status()
            return response.json()['data']
        except (httpx.TransportError,httpx.HTTPStatusError) as exc:
            if isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code<500 and exc.response.status_code!=429: raise
            if attempt==2: raise
            LOG.warning('Submission retry %s for event %s',attempt+1,payload['event_id'])
            sleep(2**attempt)

def main():
    parser=argparse.ArgumentParser(description='Explicitly analyze a camera or local video; frames stay in memory.')
    parser.add_argument('--source',default='0',help='Camera index or local video path')
    parser.add_argument('--session',required=True,type=int)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--interval',default=3.0,type=float)
    parser.add_argument('--threshold',default=0.6,type=float)
    parser.add_argument('--device',default='camera-1')
    args=parser.parse_args()
    if args.interval<=0 or not 0<=args.threshold<=1 or args.session<=0: parser.error('Invalid interval, threshold or session')
    token=os.getenv('AI_SERVICE_TOKEN','')
    if not token: parser.error('Set AI_SERVICE_TOKEN before starting')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    import cv2
    from deepface import DeepFace
    source=int(args.source) if args.source.isdigit() else args.source
    capture=cv2.VideoCapture(source)
    if not capture.isOpened(): raise RuntimeError('Unable to open the selected camera/video')
    last=-float('inf'); failures=0
    try:
        with httpx.Client(timeout=15) as client:
            while True:
                success,frame=capture.read()
                if not success:
                    if isinstance(source,str): break
                    failures+=1
                    if failures>3: raise RuntimeError('Camera disconnected after three retries')
                    capture.release();time.sleep(2);capture=cv2.VideoCapture(source);continue
                failures=0
                # Files sample by video timestamp; cameras by elapsed wall time.
                stamp=capture.get(cv2.CAP_PROP_POS_MSEC)/1000 if isinstance(source,str) else time.monotonic()
                if stamp-last<args.interval: continue
                last=stamp; recorded_at=datetime.now(timezone.utc).isoformat()
                try:
                    predictions=DeepFace.analyze(frame,actions=['emotion'],enforce_detection=True,detector_backend='opencv',silent=True)
                except ValueError:
                    LOG.info('No usable face in sampled frame');continue
                for prediction in predictions:
                    payload=make_result(prediction,args.session,args.threshold,args.device,recorded_at)
                    if payload:
                        try: LOG.info('Result: %s',send_result(args.url,token,payload,client))
                        except httpx.HTTPError as exc: LOG.error('Delivery failed for %s: %s',payload['event_id'],type(exc).__name__)
    finally: capture.release()

if __name__=='__main__': main()
