import os, sys, bpy, math, mathutils
from random import random, uniform, choice
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
import libgenzag


def test1():
	bpy.data.objects['Cube'].hide_set(True)
	ob = libgenzag.monkey()
	ob.rotation_euler.x = -math.pi/2
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
