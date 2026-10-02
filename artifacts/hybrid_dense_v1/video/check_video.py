from pathlib import Path
import hashlib
import cv2
p=Path('artifacts/hybrid_dense_v1/video')
for file in sorted(p.glob('*.mp4')):
    cap=cv2.VideoCapture(str(file)); digests=[]; dimensions=set()
    while True:
        ok,frame=cap.read()
        if not ok:break
        dimensions.add((frame.shape[1],frame.shape[0]))
        digests.append(hashlib.sha256(frame.tobytes()).hexdigest())
    cap.release()
    print(file.name,'decoded',len(digests),'unique',len(set(digests)),'dimensions',sorted(dimensions),'sha256',hashlib.sha256(file.read_bytes()).hexdigest())
    assert len(digests)==33 and len(set(digests))==33
