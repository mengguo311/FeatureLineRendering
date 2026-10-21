"""Explicit engineering recovery; retain initial INVALID and rc1 untouched."""
from common import *
from radegs_camera_compat import read_cameras,SOURCE,SOURCE_SHA
import math,time
from PIL import Image
U=OUT.parent/'unit_006'


def main():
    start=time.monotonic();lock=json.loads((U/'RECOVERY_LOCK.json').read_text())
    for row in lock['files']:assert sha(row['path'])==row['sha256'],row['path']
    old=json.loads((U/'INDEPENDENT_VALIDATION.json').read_text())
    failed=[k for k,v in old['checks'].items() if not v['passed']]
    assert failed==['official_RaDeGS_camera_reader'],failed
    assert len(old['frame_metrics'])==120
    generation=json.loads((U/'GENERATION.json').read_text())
    maximum=dict(rotation=0.,translation=0.,focal=0.,projection_px=0.)
    mesh=np.load(U/'oracle_only/lamp_mesh.npz',allow_pickle=False)['vertices']
    parts={};all_rgb_exact=True;all_official_cast_bytes_exact=True;unchanged=0
    for split in ('train','dev','test'):
        d=U/'dataset'/('train' if split=='train' else f'evaluation/{split}')
        assert sha(d/'cameras.json')==generation['splits'][split]['camera_sha256']
        frames=json.loads((d/'cameras.json').read_text())['frames']
        cameras=read_cameras(d,f'transforms_{split}.json');assert len(cameras)==len(frames)
        for c,f in zip(cameras,frames):
            prior=next(x for x in old['frame_metrics'] if x['id']==f['id'])
            assert sha(d/f['rgb_path'])==prior['rgb_sha256']
            assert sha(U/'oracle_only'/split/f"{f['id']}.npz")==prior['oracle_sha256'];unchanged+=1
            assert c.image_name==f['id'] and c.mask is None and c.depth is None
            R,t=np.asarray(f['R_w2c']),np.asarray(f['t_w2c'])
            xc=mesh@R.T+t;oc=mesh@c.R+c.T
            canonical=xc[:,:2]/xc[:,2:]*f['focal_px']+f['principal_point']
            ndc=oc[:,:2]/oc[:,2:]/[math.tan(c.FovX/2),math.tan(c.FovY/2)]
            official=((ndc+1)*[c.width,c.height]-1)*.5
            errors=dict(rotation=float(np.max(abs(c.R.T-R))),translation=float(np.max(abs(c.T-t))),focal=max(abs(c.width/(2*math.tan(c.FovX/2))-f['focal_px']),abs(c.height/(2*math.tan(c.FovY/2))-f['focal_px'])),projection_px=float(np.max(abs(canonical-official))))
            for k,x in errors.items():maximum[k]=max(maximum[k],x)
            with Image.open(d/f['rgb_path']) as im:
                all_rgb_exact &= np.array_equal(np.asarray(im),np.asarray(c.image))
                norm=np.array(im.convert('RGBA'))/255.
                arr=norm[:,:,:3]*norm[:,:,3:4]+np.array([1,1,1])*(1-norm[:,:,3:4])
                signed_bytes=np.array(arr*255.,dtype=np.byte).view(np.uint8)
                all_official_cast_bytes_exact &= np.array_equal(signed_bytes,np.asarray(c.image))
            c.image.close()
        parts[split]=len(cameras)
    assert max(maximum.values())<1e-9 and all_rgb_exact and all_official_cast_bytes_exact
    assert read_cameras(U/'dataset/train','transforms_test.json')==[]
    assert sha(SOURCE)==SOURCE_SHA
    result=dict(verdict='RECOVERED_WITH_LOCAL_UINT8_CAMERA_ADAPTER',original_validation_sha256=sha(U/'INDEPENDENT_VALIDATION.json'),original_validation_verdict=old['verdict'],original_returncode=1,original_unmodified_official_reader='NO_GO_PILLOW_SIGNED_RGB_TYPE',unchanged_frames_and_oracles=unchanged,unchanged_camera_metadata=True,all_other_original_checks_passed=True,adapter_source_sha256=sha(WORK/'experiments/partwise_sketch_hatching_v02/radegs_camera_compat.py'),official_source_unchanged=True,adapted_reader_counts=parts,adapted_RGB_pixels_exact=bool(all_rgb_exact),maximum_absolute_errors=maximum,training_test_list_empty=True,full_scene_loader_called=False,training_called=False,seconds=time.monotonic()-start,scope='Input/coordinate compatibility using a disclosed local one-dtype adapter; unmodified official loader failure remains and must not be reported as passing.')
    result['original_signed_cast_underlying_bytes_exact']=bool(all_official_cast_bytes_exact)
    write_json(U/'VALIDATION_RECOVERY.json',result);print(json.dumps(native(result)))
if __name__=='__main__':main()
