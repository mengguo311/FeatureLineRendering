"""Calibrated native800 event mixtures on the canonical 400px grid."""
import ctypes
from pathlib import Path
import numpy as np
from .multiscene_probe import NativeLayers

ROOT=Path(__file__).resolve().parents[1]

class AreaLayers(NativeLayers):
    def __init__(self,state,height=800,width=800):
        native=NativeLayers(state,height,width)
        result=self.from_native_arrays(native.offsets,native.depth,native.weight,height,width)
        self.__dict__.update(result.__dict__)

    def bind(self):
        self.lib=ctypes.CDLL(str(ROOT/'out/multiscene_foundation/setup/layers.so'))
        self.lib.multiscene_layer_query.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*5+[ctypes.c_double]+[ctypes.c_void_p]*2
        self.lib.multiscene_layer_query.restype=None
        self.area_lib=ctypes.CDLL(str(ROOT/'out/multiscene_foundation_corrected/setup/area_layers.so'))
        self.area_lib.area_layers.argtypes=[ctypes.c_int]*2+[ctypes.c_void_p]*7
        self.area_lib.area_layers.restype=None
        self.area_lib.area_quantiles.argtypes=[ctypes.c_int]+[ctypes.c_void_p]*4
        self.area_lib.area_quantiles.restype=None

    @classmethod
    def from_native_arrays(cls,offsets,depth,weight,height,width):
        if height%2 or width%2:raise ValueError('even native dimensions required')
        result=object.__new__(cls);result.height=height//2;result.width=width//2;result.bind()
        offsets=np.ascontiguousarray(offsets,'i8');depth=np.ascontiguousarray(depth,'f4');weight=np.ascontiguousarray(weight,'f4')
        if len(offsets)!=height*width+1 or offsets[-1]!=len(depth) or len(depth)!=len(weight):raise ValueError('event shape mismatch')
        result.offsets=np.zeros(result.height*result.width+1,'i8')
        ptrs=[offsets.ctypes.data,depth.ctypes.data,weight.ctypes.data,result.offsets.ctypes.data]
        result.area_lib.area_layers(height,width,*ptrs,None,None,None)
        result.depth=np.empty(result.offsets[-1],'f4');result.weight=np.empty_like(result.depth);result.transmittance=np.empty_like(result.depth)
        result.area_lib.area_layers(height,width,*ptrs,result.depth.ctypes.data,result.weight.ctypes.data,result.transmittance.ctypes.data)
        return result

    def quantiles(self):
        out=np.zeros((self.height,self.width,3),'f4')
        self.area_lib.area_quantiles(self.height*self.width,self.offsets.ctypes.data,self.depth.ctypes.data,self.weight.ctypes.data,out.ctypes.data)
        return out

    def alpha(self):
        end=self.offsets[1:];valid=end>self.offsets[:-1];a=np.zeros(self.height*self.width,'f4')
        a[valid]=1-self.transmittance[end[valid]-1]
        return a.reshape(self.height,self.width)

    def save(self,path):
        with Path(path).open('xb') as stream:
            np.savez_compressed(stream,height=self.height,width=self.width,offsets=self.offsets,depth=self.depth,weight=self.weight,transmittance=self.transmittance)

    @classmethod
    def load(cls,path):
        result=object.__new__(cls)
        with np.load(path) as data:
            for k in ['offsets','depth','weight','transmittance']:setattr(result,k,data[k])
            result.height=int(data['height']);result.width=int(data['width'])
        result.bind();return result


def bind_fast_query(layer):
    """Same independent per-query arithmetic; parallelize only large batches."""
    layer.lib=ctypes.CDLL(str(ROOT/'out/multiscene_foundation_corrected/setup/fast_query.so'))
    layer.lib.multiscene_layer_query.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*5+[ctypes.c_double]+[ctypes.c_void_p]*2
    layer.lib.multiscene_layer_query.restype=None
    return layer
