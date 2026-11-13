"""Sample a DirectShow camera and write binary frames to a local pipe."""
import argparse
import queue
import struct
import subprocess
import sys
import time


def read_frame(stream):
    import numpy as np

    header = stream.read(8)
    if len(header) != 8:
        return False, None
    height, width = struct.unpack('<II', header)
    size = height * width * 3
    if not 0 < size <= 64 * 1024 * 1024:
        raise ValueError('Invalid camera frame dimensions')
    data = stream.read(size)
    if len(data) != size:
        return False, None
    return True, np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)


def main():
    from pygrabber.dshow_graph import FilterGraph

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=int, default=0)
    parser.add_argument('--interval', type=float, default=3)
    parser.add_argument('--verify-with', help='AI Python executable for the isolated acceptance test')
    parser.add_argument('--duration', type=float, default=20)
    args = parser.parse_args()
    if args.interval <= 0 or args.duration <= 0:
        parser.error('Interval and duration must be positive')
    frames = queue.Queue()
    graph = FilterGraph()
    graph.add_video_input_device(args.source)
    graph.add_sample_grabber(frames.put)
    graph.add_null_render()
    graph.prepare_preview_graph()
    graph.run()
    verifier = None
    try:
        if args.verify_with:
            verifier = subprocess.Popen(
                [args.verify_with, '-m', 'scripts.verify_ai_camera', '--capture-stdin',
                 '--duration', str(args.duration)], stdin=subprocess.PIPE,
            )
        output = verifier.stdin if verifier else sys.stdout.buffer
        while verifier is None or verifier.poll() is None:
            graph.grab_frame()
            frame = frames.get(timeout=5)
            height, width, channels = frame.shape
            if channels != 3:
                raise ValueError('Expected a three-channel camera frame')
            output.write(struct.pack('<II', height, width))
            output.write(frame.tobytes())
            output.flush()
            time.sleep(args.interval)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        graph.stop()
        if verifier is not None:
            try:
                verifier.stdin.close()
            except BrokenPipeError:
                pass
    return verifier.wait() if verifier else 0


if __name__ == '__main__':
    raise SystemExit(main())
