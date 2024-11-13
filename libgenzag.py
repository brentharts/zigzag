import os, sys
from random import random, uniform, choice
try:
	import bpy, mathutils
except:
	bpy=None

if bpy:
	bpy.types.Material.zigzag_object_type = bpy.props.EnumProperty(
		name='type',
		items=[
			("NONE", "none", "no type"), 
			("UPPER_LIP", "upper lip", "material is upper lip of mouth"), 
			("LOWER_LIP", "lower lip", "material is lower lip of mouth"), 
			("UPPER_EYELID", "upper eyelid", "material is upper lid of eyes"), 
			("LOWER_EYELID", "lower eyelid", "material is lower lid of eyes"), 
			("EYES", "pupil", "material is pulil of eyes"), 
		]
	)

def monkey(materials=True):
	bpy.ops.mesh.primitive_cube_add()
	cu = bpy.context.active_object
	cu.scale *= 0.04
	#cu.location = [-0.144, -0.69, -0.66]
	cu.location = [-0.144, -0.62, -0.66]
	mod = cu.modifiers.new(name='array',type='ARRAY')
	mod.relative_offset_displace[0] = 1.2
	mod.count=4
	bpy.ops.object.modifier_apply(modifier='array')
	mod = cu.modifiers.new(name='array',type='ARRAY')
	mod.relative_offset_displace[0] = 0
	mod.relative_offset_displace[2] = -1.9
	bpy.ops.object.modifier_apply(modifier='array')

	bpy.ops.mesh.primitive_monkey_add()
	ob = bpy.context.active_object

	monkey_mod = {0: (0.002, 0.07, -0.004), 1: (-0.002, 0.07, -0.004), 2: (-0.013, 0.065, 0.015), 3: (0.013, 0.065, 0.015), 4: (-0.027, 0.041, 0.025), 5: (0.027, 0.041, 0.025), 6: (0.0, 0.048, 0.035), 7: (0.0, 0.048, 0.035), 8: (0.0, 0.069, 0.021), 9: (0.0, 0.069, 0.021), 10: (0.001, 0.068, -0.007), 11: (-0.001, 0.068, -0.007), 12: (-0.004, 0.069, -0.004), 13: (0.004, 0.069, -0.004), 14: (0.014, 0.071, 0.015), 15: (-0.014, 0.071, 0.015), 16: (0.027, 0.052, 0.025), 17: (-0.027, 0.052, 0.025), 18: (0.036, 0.052, 0.001), 19: (-0.036, 0.052, 0.001), 20: (0.021, 0.067, 0.0), 21: (-0.021, 0.067, 0.0), 22: (-0.007, 0.067, 0.001), 23: (0.007, 0.067, 0.001), 24: (-0.004, 0.069, 0.002), 25: (0.004, 0.069, 0.002), 26: (0.014, 0.071, -0.013), 27: (-0.014, 0.071, -0.013), 28: (0.027, 0.052, -0.027), 29: (-0.027, 0.052, -0.027), 30: (0.0, 0.048, -0.036), 31: (0.0, 0.048, -0.036), 32: (0.0, 0.069, -0.02), 33: (0.0, 0.069, -0.02), 34: (0.001, 0.068, 0.006), 35: (-0.001, 0.068, 0.006), 36: (0.002, 0.07, 0.002), 37: (-0.002, 0.07, 0.002), 38: (-0.013, 0.065, -0.013), 39: (0.013, 0.065, -0.013), 40: (-0.027, 0.041, -0.027), 41: (0.027, 0.041, -0.027), 42: (-0.036, 0.04, 0.001), 43: (0.036, 0.04, 0.001), 44: (-0.02, 0.062, 0.0), 45: (0.02, 0.062, 0.0), 46: (0.005, 0.07, 0.001), 47: (-0.005, 0.07, 0.001), 48: (-0.024, 0.056, 0.001), 49: (0.024, 0.056, 0.001), 50: (-0.021, 0.057, -0.02), 51: (0.021, 0.057, -0.02), 52: (0.001, 0.064, -0.028), 53: (-0.001, 0.064, -0.028), 54: (0.018, 0.067, -0.02), 55: (-0.018, 0.067, -0.02), 56: (0.027, 0.065, 0.001), 57: (-0.027, 0.065, 0.001), 58: (0.018, 0.067, 0.018), 59: (-0.018, 0.067, 0.018), 60: (0.001, 0.077, 0.001), 61: (-0.001, 0.077, 0.001), 62: (0.001, 0.064, 0.027), 63: (-0.001, 0.064, 0.027), 64: (-0.021, 0.057, 0.018), 65: (0.021, 0.057, 0.018), 68: (0.0, -0.056, 0.135), 71: (0.0, 0.0, 0.136), 113: (0.0, 0.0, -0.064), 114: (0.0, 0.0, -0.064), 115: (0.0, 0.0, -0.036), 116: (0.0, 0.0, -0.036), 129: (0.0, -0.067, 0.136), 130: (0.119, -0.067, 0.084), 131: (-0.119, -0.067, 0.084), 132: (0.127, 0.0, 0.084), 133: (-0.127, 0.0, 0.084), 134: (0.123, -0.041, 0.0), 135: (-0.123, -0.041, 0.0), 136: (0.0, -0.041, 0.0), 145: (0.0, 0.0, -0.036), 146: (0.0, 0.0, -0.036), 167: (0.039, 0.0, 0.135), 168: (-0.039, 0.0, 0.135), 169: (0.041, 0.0, 0.0), 170: (-0.041, 0.0, 0.0), 171: (0.036, 0.0, 0.0), 172: (-0.036, 0.0, 0.0), 184: (0.035, -0.056, 0.135), 185: (-0.035, -0.056, 0.135), 216: (0.0, -0.001, 0.055), 217: (0.092, -0.001, 0.055), 218: (-0.092, -0.001, 0.055), 219: (0.102, 0.0, 0.087), 220: (-0.102, 0.0, 0.087), 221: (0.102, 0.0, 0.084), 222: (-0.102, 0.0, 0.084), 223: (0.0, 0.178, 0.243), 224: (0.104, 0.175, 0.186), 225: (-0.104, 0.175, 0.186), 226: (0.102, 0.0, 0.087), 227: (-0.102, 0.0, 0.087), 228: (0.135, 0.185, 0.044), 229: (-0.135, 0.185, 0.044), 230: (0.0, 0.185, 0.042), 257: (0.0, 0.055, 0.0), 258: (0.0, 0.055, 0.0), 259: (0.0, 0.055, 0.0), 260: (0.0, 0.055, 0.0), 261: (0.0, 0.055, 0.0), 262: (0.0, 0.055, 0.0), 263: (0.0, 0.055, 0.0), 264: (0.0, 0.055, 0.0), 265: (0.0, 0.055, 0.0), 266: (0.0, 0.055, 0.0), 267: (0.0, 0.055, 0.0), 268: (0.0, 0.055, 0.0), 269: (0.0, 0.055, 0.0), 270: (0.0, 0.055, 0.0), 271: (0.0, 0.055, 0.0), 272: (0.0, 0.055, 0.0), 273: (0.0, 0.055, 0.0), 274: (0.0, 0.055, 0.0), 275: (0.0, 0.055, 0.0), 276: (0.0, 0.055, 0.0), 277: (0.0, 0.055, 0.0), 278: (0.0, 0.055, 0.0), 279: (0.0, 0.055, 0.0), 280: (0.0, 0.055, 0.0), 281: (0.0, 0.055, 0.0), 282: (0.0, 0.055, 0.0)}
	#{68: (0.0, -0.056, 0.135), 71: (0.0, 0.0, 0.136), 113: (0.0, 0.0, -0.064), 114: (0.0, 0.0, -0.064), 115: (0.0, 0.0, -0.036), 116: (0.0, 0.0, -0.036), 129: (0.0, -0.067, 0.136), 130: (0.119, -0.067, 0.084), 131: (-0.119, -0.067, 0.084), 132: (0.127, 0.0, 0.084), 133: (-0.127, 0.0, 0.084), 134: (0.123, -0.041, 0.0), 135: (-0.123, -0.041, 0.0), 136: (0.0, -0.041, 0.0), 145: (0.0, 0.0, -0.036), 146: (0.0, 0.0, -0.036), 167: (0.039, 0.0, 0.135), 168: (-0.039, 0.0, 0.135), 169: (0.041, 0.0, 0.0), 170: (-0.041, 0.0, 0.0), 171: (0.036, 0.0, 0.0), 172: (-0.036, 0.0, 0.0), 184: (0.035, -0.056, 0.135), 185: (-0.035, -0.056, 0.135), 216: (0.0, -0.001, 0.055), 217: (0.092, -0.001, 0.055), 218: (-0.092, -0.001, 0.055), 219: (0.102, 0.0, 0.087), 220: (-0.102, 0.0, 0.087), 221: (0.102, 0.0, 0.084), 222: (-0.102, 0.0, 0.084), 223: (0.0, 0.178, 0.243), 224: (0.104, 0.175, 0.186), 225: (-0.104, 0.175, 0.186), 226: (0.102, 0.0, 0.087), 227: (-0.102, 0.0, 0.087), 228: (0.135, 0.185, 0.044), 229: (-0.135, 0.185, 0.044), 230: (0.0, 0.185, 0.042)}
	for vidx in monkey_mod:
		ob.data.vertices[vidx].co += mathutils.Vector(monkey_mod[vidx])

	cu.select_set(True)
	bpy.ops.object.join()

	if materials:
		mat = bpy.data.materials.new(name='skin')
		mat.diffuse_color = [uniform(0.4,0.8), uniform(0.2,0.5), uniform(0.3,0.6), 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='pupil')
		mat.diffuse_color = [uniform(0,0.3), uniform(0,0.3), uniform(0,0.5), 1]
		ob.data.materials.append(mat)
		mat.zigzag_object_type = "EYES"

		mat = bpy.data.materials.new(name='eye')
		mat.diffuse_color = [uniform(0.8,1), uniform(0.8,1), uniform(0.8,1), 1]
		ob.data.materials.append(mat)


		mat = bpy.data.materials.new(name='lower-theeth')
		mat.diffuse_color = [uniform(0.8,1), uniform(0.8,1), uniform(0.8,1), 1]
		ob.data.materials.append(mat)


		mat = bpy.data.materials.new(name='hair')
		mat.diffuse_color = [uniform(0.4,0.8), uniform(0.2,0.5), uniform(0.3,0.6), 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='mouth')
		mat.diffuse_color = [uniform(0.3,0.8), uniform(0,0.1), uniform(0.1,0.3), 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='black')
		mat.diffuse_color = [0,0,0, 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='upper-theeth')
		s = 0.5
		mat.diffuse_color = [uniform(0.8,1)*s, uniform(0.8,1)*s, uniform(0.8,1)*s, 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='lower-lip')
		mat.diffuse_color = [uniform(0.5,0.9), uniform(0.1,0.3), uniform(0.2,0.5), 1]
		ob.data.materials.append(mat)
		mat.zigzag_object_type = "LOWER_LIP"

		mat = bpy.data.materials.new(name='eye-lids')
		mat.diffuse_color = [uniform(0.4,0.8), uniform(0.2,0.5), uniform(0.3,0.6), 1]
		ob.data.materials.append(mat)

		mat = bpy.data.materials.new(name='eye-lids-upper')
		mat.diffuse_color = [uniform(0.1,0.3), uniform(0,0.1), uniform(0,0.1), 1]
		ob.data.materials.append(mat)
		mat.zigzag_object_type = "UPPER_EYELID"

		mat = bpy.data.materials.new(name='eye-lids-lower')
		mat.diffuse_color = [uniform(0.2,0.5), uniform(0,0.3), uniform(0,0.3), 1]
		ob.data.materials.append(mat)
		mat.zigzag_object_type = "LOWER_EYELID"


		## eyes
		for poly in ob.data.polygons[0:64]:
			poly.material_index=1
		for poly in ob.data.polygons[0:32]:
			poly.material_index=2

		## head
		for poly in ob.data.polygons[-300:]:
			poly.material_index=4

		## ears
		#for poly in ob.data.polygons[-100:]:
		#	poly.material_index=5
		#for poly in ob.data.polygons[150:200]:

		## mouth
		for poly in ob.data.polygons[170:194]:
			poly.material_index=5

		## upper lip
		#for poly in ob.data.polygons[170:178]:
		#	poly.material_index=6
		## lower lip
		for poly in ob.data.polygons[178:182]:
			poly.material_index=8


		## back of mouth - black
		ob.data.polygons[190].material_index=6
		ob.data.polygons[191].material_index=6

		## fixes side of nose
		for poly in ob.data.polygons[170:174]:
			poly.material_index=0


		## upper theeth
		for poly in ob.data.polygons[-48:]:
			poly.material_index=7

		## lower theeth
		for poly in ob.data.polygons[-24:]:
			poly.material_index=3

		## eye lids
		for poly in ob.data.polygons[192:246]:
			poly.material_index=9

		## uppe eye lids
		for poly in ob.data.polygons[220:230]:
			poly.material_index=10
		#ob.data.polygons[240].material_index=6

		for poly in ob.data.polygons[202:206]:
			poly.material_index=11

	return ob

sym_gen = {
	'🐵' : monkey,
}

if __name__=='__main__':
	out = None
	for arg in sys.argv:
		if arg.startswith('--out='):
			out = arg.split('=')[-1]
		elif arg.startswith('--generate='):
			sym = arg.split('=')[-1]
			if sym in sym_gen:
				sym_gen[sym]()
			else:
				globals()[sym]()
	if out:
		bpy.ops.wm.save_as_mainfile(filepath=out)
