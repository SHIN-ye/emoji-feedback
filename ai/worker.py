"""Independent, explicitly launched camera/video worker. Never writes frames to disk."""
import argparse,logging,os,time,uuid,math,sys
from pathlib import Path
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

def process_frame(frame,session_id,threshold,device_id,analyze,url,token,client):
    """Analyze one in-memory frame and deliver anonymous results."""
    recorded_at=datetime.now(timezone.utc).isoformat()
    try:
        predictions=analyze(frame,actions=['emotion'],enforce_detection=True,detector_backend='opencv',silent=True)
    except ValueError:
        LOG.info('No usable face in sampled frame')
        return []
    if isinstance(predictions,dict): predictions=[predictions]
    results=[]
    for prediction in predictions:
        payload=make_result(prediction,session_id,threshold,device_id,recorded_at)
        if payload:
            result=send_result(url,token,payload,client)
            results.append(result)
            LOG.info('Emotion=%s confidence=%.3f result=%s',payload['emoji'],payload['confidence'],result)
    return results

def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'): stream.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description='Explicitly analyze a camera or local video; frames stay in memory.')
    parser.add_argument('--source',default='0',help='Camera index or local video path')
    parser.add_argument('--capture-stdin',action='store_true',help='Read sampled camera frames from a local binary pipe')
    parser.add_argument('--session',required=True,type=int)
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--interval',default=3.0,type=float)
    parser.add_argument('--threshold',default=0.6,type=float)
    parser.add_argument('--device',default='camera-1')
    parser.add_argument('--duration',default=0.0,type=float,help='Stop after this many seconds; 0 runs continuously')
    args=parser.parse_args()
    if not all(math.isfinite(x) for x in (args.interval,args.threshold,args.duration)) or args.interval<=0 or args.duration<0 or not 0<=args.threshold<=1 or args.session<=0: parser.error('Invalid interval, threshold, duration or session')
    token=os.getenv('AI_SERVICE_TOKEN','')
    if not token: parser.error('Set AI_SERVICE_TOKEN before starting')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    import cv2
    cache=Path(__file__).resolve().parent.parent/'artifacts'/'ai-model-cache'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('DEEPFACE_HOME',str(cache))
    from deepface import DeepFace
    LOG.info('Loading emotion model before opening camera')
    DeepFace.build_model('Emotion',task='facial_attribute')
    detector=DeepFace.build_model('opencv',task='face_detector')
    # Some Windows OpenCV builds cannot open cascade files under Unicode paths.
    for key,filename in (('face_detector','haarcascade_frontalface_default.xml'),
                         ('eye_detector','haarcascade_eye.xml')):
        classifier=detector.model[key]
        if classifier.empty():
            xml=(Path(cv2.data.haarcascades)/filename).read_text(encoding='utf-8')
            storage=cv2.FileStorage(xml,cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            try:
                if not classifier.read(storage.getFirstTopLevelNode()) or classifier.empty():
                    raise RuntimeError(f'Cannot load OpenCV cascade {filename}')
            finally:
                storage.release()
    source=int(args.source) if args.source.isdigit() else args.source
    def open_capture():
        capture=cv2.VideoCapture(source)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError('Unable to open the selected camera/video')
        return capture
    capture=None if args.capture_stdin else open_capture()
    if args.capture_stdin:
        from ai.camera_pipe import read_frame
    last=-float('inf'); failures=0; started=time.monotonic(); sampled=0; accepted=0
    try:
        with httpx.Client(timeout=15) as client:
            while True:
                if args.duration and time.monotonic()-started>=args.duration: break
                success,frame=read_frame(sys.stdin.buffer) if args.capture_stdin else capture.read()
                if not success:
                    if args.capture_stdin: raise RuntimeError('Camera frame pipe closed')
                    if isinstance(source,str): break
                    failures+=1
                    if failures>3: raise RuntimeError('Camera disconnected after three retries')
                    capture.release();time.sleep(2);capture=open_capture();continue
                failures=0
                # Files sample by video timestamp; cameras by elapsed wall time.
                stamp=capture.get(cv2.CAP_PROP_POS_MSEC)/1000 if not args.capture_stdin and isinstance(source,str) else time.monotonic()
                if not args.capture_stdin and stamp-last<args.interval: continue
                last=stamp; sampled+=1
                try:
                    results=process_frame(frame,args.session,args.threshold,args.device,DeepFace.analyze,args.url,token,client)
                    accepted+=sum(bool(r.get('accepted')) for r in results)
                except httpx.HTTPStatusError as exc:
                    LOG.error('Backend rejected result: HTTP %s',exc.response.status_code)
                    if exc.response.status_code in (400,401,403,404,422): raise
                except httpx.TransportError as exc:
                    LOG.error('Delivery failed: %s',type(exc).__name__)
    finally:
        if capture is not None: capture.release()
        LOG.info('Stopped: sampled_frames=%s accepted_results=%s',sampled,accepted)

if __name__=='__main__': main()
