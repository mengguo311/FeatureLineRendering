import * as THREE from 'three';
export function alignNativeCamera(camera,metadata,near=.001,far=1000){
 const K=metadata.native_K,w=metadata.native_width||800,h=metadata.native_height||800;
 const cv=new THREE.Matrix4().set(...metadata.w2c.flat()),flip=new THREE.Matrix4().makeScale(1,-1,-1),view=flip.multiply(cv);
 camera.matrixWorld.copy(view).invert();camera.matrixWorld.decompose(camera.position,camera.quaternion,camera.scale);camera.up.setFromMatrixColumn(camera.matrixWorld,1);camera.updateMatrixWorld(true);camera.matrixWorldInverse.copy(view);camera.near=near;camera.far=far;
 camera.projectionMatrix.set(2*K[0][0]/w,-2*K[0][1]/w,1-2*K[0][2]/w,0,0,2*K[1][1]/h,2*K[1][2]/h-1,0,0,0,-(far+near)/(far-near),-2*far*near/(far-near),0,0,-1,0);camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(h/(2*K[1][1])));
 return new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion).add(camera.position);
}
