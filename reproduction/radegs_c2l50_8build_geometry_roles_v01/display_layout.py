from env import *
def native_canvas(image,width,height):
 h,w=image.shape[:2]
 if w>width or h>height:raise ValueError('Native image would be cropped')
 out=np.ones((height,width,3),dtype=image.dtype);x=(width-w)//2;y=(height-h)//2;out[y:y+h,x:x+w]=image;return out
