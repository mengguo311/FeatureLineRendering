import numpy as np
import json,struct

def glb_bytes(vertices, faces):
    v=np.ascontiguousarray(vertices,dtype='<f4');f=np.ascontiguousarray(faces,dtype='<u4')
    vb=v.tobytes();fb=f.tobytes();binary=vb+fb
    doc={'asset':{'version':'2.0','generator':'GAER fixed contour asset; original world coordinates'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0,'name':'fixed_world_contour_tubes'}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0,'mode':4}]}],'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[0.02,0.02,0.02,1.0],'metallicFactor':0.0,'roughnessFactor':1.0},'doubleSided':True,'extensions':{'KHR_materials_unlit':{}}}],'extensionsUsed':['KHR_materials_unlit'],'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},{'buffer':0,'byteOffset':len(vb),'byteLength':len(fb),'target':34963}],'accessors':[{'bufferView':0,'componentType':5126,'count':len(v),'type':'VEC3','min':v.min(0).tolist(),'max':v.max(0).tolist()},{'bufferView':1,'componentType':5125,'count':f.size,'type':'SCALAR'}],'extras':{'fixed_geometry':True,'surface_recovery_certified':False,'up_axis_original':'Z','camera_dependent_update':False}}
    jb=json.dumps(doc,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
    binary+=b'\0'*((-len(binary))%4)
    length=12+8+len(jb)+8+len(binary)
    return struct.pack('<III',0x46546c67,2,length)+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(binary),0x004e4942)+binary


def tube_mesh(curves, radius, sides=8):
    vertices=[];faces=[];offset=0
    for points in curves:
        p=np.asarray(points,dtype=np.float64)
        if len(p)<2:continue
        tangents=np.gradient(p,axis=0)
        for i,t in enumerate(tangents):
            norm=np.linalg.norm(t)
            if norm<1e-12:t=p[min(i+1,len(p)-1)]-p[max(0,i-1)]
            t=t/max(np.linalg.norm(t),1e-12)
            ref=np.eye(3)[np.argmin(np.abs(t))]
            a=np.cross(t,ref);a/=max(np.linalg.norm(a),1e-12);b=np.cross(t,a)
            theta=np.arange(sides)*2*np.pi/sides
            ring=p[i]+radius*(np.cos(theta)[:,None]*a+np.sin(theta)[:,None]*b)
            vertices.extend(ring)
            if i:
                for j in range(sides):
                    u=offset+(i-1)*sides+j;v=offset+(i-1)*sides+(j+1)%sides
                    x=offset+i*sides+j;y=offset+i*sides+(j+1)%sides
                    faces.extend([[u,v,y],[u,y,x]])
        for j in range(1,sides-1):
            faces.append([offset,offset+j+1,offset+j])
            z=offset+(len(p)-1)*sides;faces.append([z,z+j,z+j+1])
        offset+=len(p)*sides
    return np.asarray(vertices,dtype=np.float32).reshape(-1,3),np.asarray(faces,dtype=np.int32).reshape(-1,3)


def supported_depth(depths, weights, strengths):
    w=np.asarray(weights,dtype=np.float64)*np.asarray(strengths)
    unsupported=w.sum(1)<=1e-10
    w[unsupported]=np.asarray(weights)[unsupported]
    mass=w.sum(1)
    d=(np.asarray(depths)*w).sum(1)/np.maximum(mass,1e-20)
    d[mass<=1e-10]=np.nan
    return d

def ray_points(pixels_xy, depths, K, w2c):
    xy=np.asarray(pixels_xy,dtype=np.float64)
    rays=np.column_stack((xy,np.ones(len(xy)))) @ np.linalg.inv(K).T
    pc=rays*np.asarray(depths)[:,None]
    c2w=np.linalg.inv(w2c)
    return pc @ c2w[:3,:3].T+c2w[:3,3]
