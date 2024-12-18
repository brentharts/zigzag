#!/usr/bin/python3
import os, sys, subprocess, base64, webbrowser, zipfile
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path:
	## fixes importing of our fork of mesh_auto_mirror.py for Blender 3.6
	sys.path.insert(0, _thisdir)
import zigzag, libwebzag, libgenzag, libzader
from zigzag import is_mesh_sym
from c3d import *

HELP='''
run: python c3zag.py [.blend]

options:
	--test runs simple WASM test without blender
	--Oz optimize for size
	--icolor use indexed vertex colors

'''

USE_CPU_XFORM = '--cpu-xform' in sys.argv
C3 = '/usr/local/bin/c3c'
GZIP = 'gzip'
FIREFOX = '/usr/bin/firefox'
islinux=iswindows=isapple=c3gz=c3zip=None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	if not os.path.isfile(BLENDER):
		BLENDER = 'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe'

	c3zip = 'https://github.com/c3lang/c3c/releases/download/v0.6.3/c3-windows.zip'
	C3 = os.path.join(_thisdir,'c3/c3c.exe')
	GZIP = os.path.abspath(os.path.join(_thisdir,'gzip.exe'))
	FIREFOX = '/Program Files/Mozilla Firefox/firefox.exe'
	iswindows=True
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-macos.zip'
	isapple=True
else:
	BLENDER = 'blender'
	if os.path.isfile(os.path.expanduser('~/Downloads/blender-4.2.1-linux-x64/blender')):
		BLENDER = os.path.expanduser('~/Downloads/blender-4.2.1-linux-x64/blender')
	c3gz = 'https://github.com/c3lang/c3c/releases/download/latest/c3-ubuntu-20.tar.gz'
	islinux=True

if not os.path.isfile(C3):
	C3 = '/opt/c3/c3c'
	if not os.path.isfile(C3):
		if not os.path.isdir('./c3'):
			if c3gz:
				if not os.path.isfile('c3-ubuntu-20.tar.gz'):
					cmd = 'wget -c %s' % c3gz
					print(cmd)
					subprocess.check_call(cmd.split())
				cmd = 'tar -xvf c3-ubuntu-20.tar.gz'
				print(cmd)
				subprocess.check_call(cmd.split())
			elif c3zip and iswindows:
				if os.path.isfile('c3-windows.zip') and len(open('c3-windows.zip','rb').read())==0:
					os.unlink('c3-windows.zip')
				if not os.path.isfile('c3-windows.zip'):
					cmd = ['C:/Windows/System32/curl.exe', '-L', '-o', 'c3-windows.zip', c3zip]
					print(' '.join(cmd))
					subprocess.check_call(cmd)
				with zipfile.ZipFile('c3-windows.zip', 'r') as zip_ref:
					zip_ref.extractall(_thisdir)
			elif c3zip:
				if not os.path.isfile('c3-macos.zip'):
					cmd = ['curl', '-L', '-o', 'c3-macos.zip', c3zip]
					print(cmd)
					subprocess.check_call(cmd)
				with zipfile.ZipFile('c3-macos.zip', 'r') as zip_ref:
					zip_ref.extractall(_thisdir)

		if iswindows:
			C3 = os.path.abspath('./c3-windows-Release/c3c.exe')
		else:
			C3 = os.path.abspath('./c3/c3c')

print('c3c:', C3)
assert os.path.isfile(C3)

def c3_compile(c3, name='test-c3'):
	tmp = '/tmp/%s.c3' % name
	open(tmp,'w').write(c3)
	cmd = [
		C3, '--target', 'wasm32', 'compile',
		'--output-dir', '/tmp',
		'--obj-out', '/tmp',
		'--build-dir', '/tmp',
		#'--print-output',
		'--link-libc=no', '--use-stdlib=no', '--no-entry', '--reloc=none', '-z', '--export-table',
		'-Oz',
		'-o', name,
		tmp
	]
	print(cmd)
	subprocess.check_call(cmd)
	wasm = '/tmp/%s.wasm' % name
	return wasm


def test_wasm():
	wasm = c3_compile(WASM_MINI_GL + WASM_TEST)

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'

	#open(jtmp,'w').write(zigzag.JS_API_HEADER + JS_MINI_GL)
	open(jtmp,'w').write(libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(C3_ZAG_INIT) )

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', jtmp]
	print(cmd)
	subprocess.check_call(cmd)
	js = open(jtmp+'.gz','rb').read()
	jsb = base64.b64encode(js).decode('utf-8')


	o = [
		'<html>',
		'<body>',
		'<canvas id="$"></canvas>',
		'<script>', 
		'var $0="%s"' % jsb,
		'var $1="%s"' % b,
		libwebzag.JS_DECOMP,
		'</script>',
	]

	out = 'c3zag-preview.html'
	open(out,'w').write('\n'.join(o))
	webbrowser.open(out)

try:
	import bpy
except:
	bpy = None



if __name__=='__main__':
	if '--help' in sys.argv:
		print(HELP)
		subprocess.check_call([C3, '--version'])
		sys.exit()
	elif bpy:
		pass
	elif '--test' in sys.argv:
		test_wasm()
	elif (iswindows and os.path.isfile(BLENDER)) or (isapple and os.path.isfile(BLENDER)) or islinux:
		cmd = [BLENDER]
		for arg in sys.argv:
			if arg.endswith('.blend'):
				cmd.append(arg)
				break
		cmd +=['--python-exit-code', '1', '--python', __file__]
		exargs = []
		for arg in sys.argv:
			if arg.startswith('--'):
				exargs.append(arg)
		if exargs:
			cmd.append('--')
			cmd += exargs
		print(cmd)
		subprocess.check_call(cmd)
		sys.exit()

	else:
		print(HELP)
		print('WARN: could not find blender')
		test_wasm()
		sys.exit()

## in blender ##
assert bpy
import math, mathutils
from random import random, uniform, choice

for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
	setattr(
		bpy.types.Object,
		"c3_script" + str(i),
		bpy.props.PointerProperty(name="script%s" % i, type=bpy.types.Text),
	)
	setattr(
		bpy.types.Material,
		"c3_script" + str(i),
		bpy.props.PointerProperty(name="script%s" % i, type=bpy.types.Text),
	)
	setattr(
		bpy.types.Object,
		"c3_script%s_disable" %i,
		bpy.props.BoolProperty(name="disable"),
	)
	setattr(
		bpy.types.Material,
		"c3_script%s_disable" %i,
		bpy.props.BoolProperty(name="disable"),
	)


bpy.types.Object.c3_hide = bpy.props.BoolProperty( name="hidden on spawn")

@bpy.utils.register_class
class C3MaterialPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Material_Panel"
	bl_label = "C3 Materials"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "material"

	def draw(self, context):
		if not context.active_object: return
		ob = context.active_object

		self.layout.label(text="C3 Material Scripts")
		for mat in ob.data.materials:
			if not mat: continue
			box = self.layout.box()
			row = box.row()
			row.prop(mat, 'diffuse_color', text=mat.name.upper())
			row.prop(mat, 'zigzag_object_type')

			foundUnassignedScript = False
			for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
				hasProperty = (
					getattr(mat, "c3_script" + str(i)) != None
				)
				if hasProperty or not foundUnassignedScript:
					row = box.row()
					row.prop(mat, "c3_script" + str(i))
					if hasProperty:
						row.prop(mat, "c3_script%s_disable"%i)
				if not foundUnassignedScript:
					foundUnassignedScript = not hasProperty


@bpy.utils.register_class
class C3ObjectPanel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_C3_Object_Panel"
	bl_label = "C3 Object Options"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "object"

	def draw(self, context):
		if not context.active_object: return
		ob = context.active_object

		#self.layout.prop(ob, 'c3_hide')  ## TODO
		self.layout.prop(ob, 'noise')
		self.layout.prop(ob, 'anim_noise')

		self.layout.label(text="C3 Object Scripts")
		self.layout.prop(ob, 'c3_script')

		foundUnassignedScript = False
		for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
			hasProperty = (
				getattr(ob, "c3_script" + str(i)) != None
			)
			if hasProperty or not foundUnassignedScript:
				row = self.layout.row()
				row.prop(ob, "c3_script" + str(i))
				if hasProperty:
					row.prop(ob, "c3_script%s_disable"%i)
			if not foundUnassignedScript:
				foundUnassignedScript = not hasProperty

@bpy.utils.register_class
class C3Export(bpy.types.Operator):
	bl_idname = "c3.export_wasm"
	bl_label = "C3 Export WASM"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		build_wasm(context.world)
		return {"FINISHED"}


@bpy.utils.register_class
class C3WorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_C3World_Panel"
	bl_label = "C3 Export"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"
	def draw(self, context):
		self.layout.prop(context.world, 'c3_script')
		self.layout.prop(context.world, 'javascript_script')
		self.layout.prop(context.world, 'after_export_script')
		self.layout.operator("c3.export_wasm", icon="CONSOLE")


@bpy.utils.register_class
class C3ZagMainOperator(bpy.types.Operator):
	"c3zag main loop"
	bl_idname = "c3zag.run"
	bl_label = "c3zag_run"
	bl_options = {'REGISTER'}
	def modal(self, context, event):
		if event.type == "TIMER":
			sys.stdout.flush()
		return {'PASS_THROUGH'} # will not supress event bubbles

	def invoke (self, context, event):
		global _timer
		if _timer is None:
			_timer = self._timer = context.window_manager.event_timer_add(
				time_step=0.05,
				window=context.window
			)
			context.window_manager.modal_handler_add(self)
			return {'RUNNING_MODAL'}
		return {'FINISHED'}

	def execute (self, context):
		return self.invoke(context, None)

_timer=None

mini_gl_const = {
	'UNSIGNED_SHORT':5123,
	'TRIANGLES':4,
	'DEPTH_BUFFER_BIT':256, 
	'COLOR_BUFFER_BIT':16384, 
	'FLOAT':5126, 
	'FRAGMENT_SHADER':35632, 
	'VERTEX_SHADER':35633, 
	'ARRAY_BUFFER':34962,
	'STATIC_DRAW':35044,
	'ELEMENT_ARRAY_BUFFER':34963,
	'DEPTH_TEST':2929,
}

def minjs(js):
	o = []
	for ln in js.splitlines():
		if '--debug' in sys.argv:
			if ln.strip().startswith('//'):
				continue
		elif ln.strip().startswith(('//', 'console.log')):
			continue

		o.append(ln)
	o = '\n'.join(o)
	for glcon in mini_gl_const:
		key = 'this.gl.%s' % glcon
		if key in o:
			o = o.replace(key, str(mini_gl_const[glcon]))

	return o.replace('\t', '').replace('\n', '')

def wasm_opt(wasm):
	'''
	this is caused by stripping sign+ext which is triggers by:
	`char a; if (a<128)`
	[wasm-validator error in function test_c3.onload] unexpected false: all used features should be allowed, on 
	(i32.extend8_s
	 (local.get $6)
	)
	Fatal: error validating input
	'''

	o = wasm.replace('.wasm', '.opt.wasm')
	cmd = ['wasm-opt', '-o',o, '-Oz', wasm]
	print(cmd)
	#try:
	subprocess.check_call(cmd)
	#except:
	#	print("WARN: wasm-opt error")
	#	return wasm
	return o

def c3_wasm_strip(wasm):
	a = b'\x00,\x0ftarget_features\x02+\x0fmutable-globals+\x08sign-ext'
	b = open(wasm,'rb').read()
	if b.endswith(a):
		c = b[:-len(a)]
		print('c3 wasm stripped bytes:', len(a) )
		open(wasm,'wb').write(c)

SERVER_PROC = None
def build_wasm( world, name='test-c3', preview=True, out=None ):
	global SERVER_PROC
	if SERVER_PROC: SERVER_PROC.kill()
	o = blender_to_c3(world)
	o = '\n'.join(o)
	if '--debug' in sys.argv: print(o)
	wasm = c3_compile(WASM_MINI_GL + o, name=name)
	c3_wasm_strip(wasm)
	if sys.platform != 'win32':
		wasm = wasm_opt(wasm)

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'
	#jsapi = zigzag.JS_API_HEADER + JS_MINI_GL
	methods = C3_ZAG_INIT
	if world.javascript_script:
		methods += '\n' + world.javascript_script.as_string()
	jsapi = libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(methods)
	jsapi = minjs(jsapi)
	open(jtmp,'w').write(jsapi)
	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', jtmp]
	print(cmd)
	subprocess.check_call(cmd)
	js = open(jtmp+'.gz','rb').read()
	jsb = base64.b64encode(js).decode('utf-8')

	o = [
		'<html>',
		'<body>',
		'<canvas id="$"></canvas>',
		'<script>', 
		'var $0="%s"' % jsb,
		'var $1="%s"' % b,
		libwebzag.JS_DECOMP,
		'</script>',
	]
	if out is None:  ## just saves into the current folder
		out = '%s.html' % name
	open(out,'w').write('\n'.join(o))

	if sys.platform != 'win32':
		os.system('ls -l %s' % out)
		os.system('ls -lh %s' % out)

		cmd = ['zip', '-9', out+'.zip', out]
		print(cmd)
		subprocess.check_call(cmd)
		os.system('ls -l %s.zip' % out)
		os.system('ls -lh %s.zip' % out)

	py = ''
	if world.after_export_script:
		py = world.after_export_script.as_string()
	if 'after_export.py' in bpy.data.texts:
		py += '\n' + bpy.data.texts['after_export.py'].as_string()
	if py.strip():
		scope = {
			'zag':libgenzag, 'wasm':wa, 'out':out, 'js':jsapi, 'bpy':bpy, 'math':math, 
			'random':random, 'uniform':uniform, 'choice':choice,
			'genchar' : libgenzag.GenChar(wa),
		}
		exec(py, scope, scope)

	if preview:
		if os.path.isfile(FIREFOX):
			## FireFox has Float16Array support
			tmp = '/tmp'
			if sys.platform=='win32':
				tmp = 'C:\\tmp'
				out = out.replace('\\', '/')  ## os.path.expanduser on Windows returns backslashes? which confuse firefox
			proc = subprocess.Popen([FIREFOX, '--profile', tmp, '--new-instance', '-url', out])
		else:
			## on linux assume that firefox is default browser
			webbrowser.open(out)





def get_scripts(ob):
	scripts = []
	if ob.c3_script:
		scripts.append( ob.c3_script )
	for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "c3_script%s_disable" %i): continue
		txt = getattr(ob, "c3_script" + str(i))
		if txt: scripts.append(txt)
	return scripts

def has_scripts(ob):
	if ob.c3_script:
		return True
	for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "c3_script%s_disable" %i): continue
		txt = getattr(ob, "c3_script" + str(i))
		if txt: return True
	return False



def blender_to_c3(world, use_vertex_colors=False):
	data = [
		DEBUG_CAMERA,
	]

	if USE_CPU_XFORM:
		data += [
			SHADER_HEADER_CPU,
			libzader.gen_shaders(libzader.VSHADER_CPU_XFORM),
			CPU_HELPER_FUNCS,
		]
	else:
		data += [
			SHADER_HEADER_GPU,
			libzader.gen_shaders(mode='C3'),
		]

	has_onload = has_ondraw = False
	if world.c3_script:
		c = world.c3_script.as_string()
		data.append(c)
		if 'fn void onload(' in c:
			has_onload = True
		if 'fn void ondraw(' in c:
			has_ondraw = True

	setup = []
	draw = []
	for ob in bpy.data.objects:
		#if ob.hide_get(): continue
		sname = zigzag.safename(ob)
		if False and ob.name not in bpy.context.view_layer.objects:
			print('C3 export skip:', ob)  ## this can happen when linking a .blend and child is missing parent
			continue
		else:
			print('C3 export:', ob)

		if ob.type=='MESH':

			if has_scripts(ob):
				#draw.append('	self = objects[%s];' % idx)

				props = {}
				for prop in ob.keys():
					if prop.startswith( ('_', 'zig_', 'c3_') ): continue
					val = ob[prop]
					if type(val) is str:
						data.append('char* %s_%s = "%s";' %(prop,sname, val))
					else:
						data.append('float %s_%s = %s;' %(prop,sname, val))
					props[prop] = ob[prop]

				prop_updates = {}
				for txt in get_scripts(ob):
					s = txt.as_string()
					for prop in props:
						if 'self.'+prop in s:
							s = s.replace('self.'+prop, '%s_%s'%(prop,sname))
							prop_updates[prop]=True
					if 'self.matrix' in s:
						s = s.replace('self.matrix', '%s_mat' % sname)
					if 'self.rotation.x' in s:
						s = s.replace('self.rotation.x', '%s_rot[0]' % sname)
					if 'self.rotation.y' in s:
						s = s.replace('self.rotation.y', '%s_rot[1]' % sname)
					if 'self.rotation.z' in s:
						s = s.replace('self.rotation.z', '%s_rot[2]' % sname)

					if 'self.rotation' in s:
						s = s.replace('self.rotation', '%s_rot' % sname)

					draw.append( s )

			is_symmetric = False
			if '--disable-sym' in sys.argv or len(ob.data.vertices)<=8:
				pass
			else:
				is_symmetric = is_mesh_sym(ob)  ## TODO this should check for a user added mirror mod on x
			if is_symmetric:
				bpy.context.view_layer.objects.active = ob
				ob.select_set(True)
				bpy.ops.object.mode_set(mode="EDIT")
				bpy.ops.object.automirror()
				bpy.ops.object.mode_set(mode="OBJECT")
				ob.modifiers[0].use_mirror_merge=False

			if not is_symmetric and '--force-sym' in sys.argv:
				raise RuntimeError('mesh is not symmetric:%s' %ob.name)


			if ob.modifiers:
				has_mirror = False
				for mod in ob.modifiers:
					if mod.type=='MIRROR':
						#mod.show_viewport=False
						#mod.show_render=False
						has_mirror=True
				Q=256
				#Q=512
				#Q=1024
				#Q=8192
				dg = bpy.context.evaluated_depsgraph_get()
				oeval = ob.evaluated_get(dg)
				if len(oeval.data.vertices) == len(ob.data.vertices) or has_mirror:
					print('mesh modifiers are compatible for export')
					deltas = []
					qdeltas= []
					for idx,v in enumerate(oeval.data.vertices):
						if idx < len(ob.data.vertices):
							delta = v.co - ob.data.vertices[idx].co
						else:
							vmx,vmy,vmz = ob.data.vertices[idx-len(ob.data.vertices)].co
							vmx = -vmx
							delta = v.co - mathutils.Vector([vmx,vmy,vmz])

						x,y,z = delta
						deltas.append((x,y,z))
						x = int(x*Q)
						y = int(y*Q)
						z = int(z*Q)
						if Q==256:
							if x < -128: x = -128; print('WARN: vertex deform clip: %s' % idx)
							elif x > 127: x = 127; print('WARN: vertex deform clip: %s' % idx)
							if y < -128: y = -128; print('WARN: vertex deform clip: %s' % idx)
							elif y > 127: y = 127; print('WARN: vertex deform clip: %s' % idx)
							if z < -128: z = -128; print('WARN: vertex deform clip: %s' % idx)
							elif z > 127: z = 127; print('WARN: vertex deform clip: %s' % idx)
						qdeltas += [str(x),str(y),str(z)]
					data += [
						'ichar[%s] deform_%s={%s};' % (len(qdeltas),sname, ','.join(qdeltas))
						#'short[%s] deform_%s={%s};' % (len(qdeltas),sname, ','.join(qdeltas))
					]
					setup += [
						'mesh_deform(&deform_%s, deform_%s.len);' % (sname,sname)
					]
				else:
					for mod in ob.modifiers:
						print(mod)
						print(dir(mod))
					raise RuntimeError('incompatible modifiers')


			a,b,c = mesh_to_c3(ob, mirror=is_symmetric, use_vertex_colors=use_vertex_colors)
			data  += a
			setup += b
			if ob.hide_get(): continue  ## Cube is default hidden prim
			draw  += c

	main = [
		'fn void main() @extern("main") @wasm {',
		'	gl_init(800, 600);',
		#'	view_matrix[14] = view_matrix[14] -3.0;',
	]
	if USE_CPU_XFORM:
		main.append(SHADER_SETUP_CPU)
	else:
		main.append(SHADER_SETUP_GPU)

	for ln in setup:
		main.append('\t' + ln)
	main.append(SHADER_POST)
	#main.append('update();')
	#main.append('js_set_entry(&update);')
	if has_onload:
		main.append('	onload();')
	main.append('}')

	update = [
		'fn void update(float delta_time, float soft_sine_time) @extern("update") @wasm {',
		#'	gl_enable("DEPTH_TEST");',
		#'	gl_depth_func("LEQUAL");',
		#'	gl_viewport(0,0,800,600);',
		#'	gl_clear(0.5,0.5,0.5, 1.0, 1.0);',
		'	gl_uniform_mat4fv(ploc, proj_matrix);',
		'	gl_uniform_mat4fv(vloc, view_matrix);',
		'	if (js_rand() < 0.1f) {s_uni[0]=soft_sine_time+1.0f;}',
	]
	for ln in draw:
		update.append('\t'+ln)
	if has_ondraw:
		update.append('ondraw(delta_time);')
	update.append('}')

	return data + update + main

def mesh_to_c3(ob, as_quads=True, mirror=False, use_object_color=False, use_vertex_colors=False):
	if mirror: mirror = 1
	else: mirror = 0
	name = zigzag.safename(ob.data)
	sname = name.upper()
	data = []
	colors = []
	verts = []
	if len(ob.data.materials)==1:
		r,g,b,a = ob.data.materials[0].diffuse_color
	elif len(ob.data.materials) > 1:
		## TODO normals
		r=g=b=0.125
		a=1.0
	else:
		r,g,b,a = ob.color

	lightz = 0.5
	lighty = 0.3
	x,y,z = ob.data.vertices[0].co

	icolors_map = {}
	icolors = []
	for v in ob.data.vertices:
		verts.append(str(v.co.x))
		verts.append(str(v.co.y))
		verts.append(str(v.co.z))

		#shade = (v.normal.z+1) * 0.5
		shade = v.normal.z
		vr = r + (shade*lightz)
		vg = g + (shade*lightz)
		vb = b + (shade*lightz)

		shade = v.normal.y
		vr = r + (shade*lighty)
		vg = g + (shade*lighty)
		vb = b + (shade*lighty)


		if vr > 1: vr = 1
		elif vr < 0: vr = 0
		if vg > 1: vg = 1
		elif vg < 0: vg = 0
		if vb > 1: vb = 1
		elif vb < 0: vb = 0

		colors.append( str( int(vr*255)) )
		colors.append( str( int(vg*255)) )
		colors.append( str( int(vb*255)) )

		mag = 2
		key = (
			int(round(vr,mag)*255),
			int(round(vg,mag)*255),
			int(round(vb,mag)*255)
		)
		if key not in icolors_map:
			icolors_map[key] = len(icolors_map)

		icolors.append(str(icolors_map[key]))


	print(icolors)
	print(icolors_map)
	print('index colors map len=', len(icolors_map))

	if '--rand-colors' in sys.argv:
		#colors = [str(random()) for i in range(len(verts))]
		colors = [str( int(random()*255) ) for i in range(len(verts))]
		#colors = ['64' for i in range(len(verts))]

	data = [
		#'const float[]  VERTS_%s={%s};' %(sname, ','.join(verts)),
		#'const float[]  COLORS_%s={%s};' %(sname, ','.join(colors)),

		'const float16[]  VERTS_%s={%s};' %(sname, ','.join(verts)),  ## 16bit float verts
	]
	if mirror:
		data += [
		#'float16[%s] verts_mirror_%s;' %(len(verts),name),  ## 16bit float verts
		]

	if use_vertex_colors:
		if '--Oz' in sys.argv and '--icolor' in sys.argv:
			rgbs = []
			for key in icolors_map:
				rgbs.append( '%s,%s,%s' % key )

			data += [
			'',
			'char[%s]  colors_%s;' %(len(colors), name),  ## color map
			'const char[] ICOLORS_%s={%s};' %(sname, ','.join(icolors)),
			'const char[%s] COLOR_MAP_%s={%s};' %(len(icolors_map)*3, sname, ', '.join(rgbs)),
			'',
			]

		else:
			data += [
			'const char[]  COLORS_%s={%s};' %(sname, ','.join(colors)),  ## 8bit per-chan color
			'',
			]


	unpak = []
	indices = []
	indices_by_mat = {}
	num_i = 0
	i_off = 0
	if '--Oz' in sys.argv and len(ob.data.vertices) < 512 and len(ob.data.materials) <= 1:
		groups = {
			32  : [],
			64  : [],
			128 : [],
			256 : [],
			512 : [],

		}
		tris = []
		for p in ob.data.polygons:
			if len(p.vertices)==3:
				a,b,c = p.vertices
				#tris.append( (a,b,c,0) )
				tris.append( (a,b,c,65000) )
				num_i += 3
				indices += [a,b,c,65000]
			elif len(p.vertices)==4:
				a,b,c,d = p.vertices
				indices += [a,b,c,d]
				num_i += 6
				ok=False
				for mx in groups:
					if a < mx and b < mx and c < mx and d < mx:
						groups[mx].append( (a,b,c,d) )
						ok=True
						break
				if not ok:
					raise RuntimeError('oh')
		for mx in groups:
			print('bit group:%s len=%s'%(mx, len(groups[mx])))

		sub256 = []

		rem = []
		for vals in groups[512]:
			reloc = True
			for idx in vals:
				if idx < 256:
					reloc = False
					break
			if reloc:
				a,b,c,d = vals
				sub256.append((a-256,b-256,c-256,d-256))
				rem.append(vals)

		print('512-256 group:', len(sub256))
		for vals in rem:
			groups[512].remove(vals)
		print('512 group len=:', len(groups[512]))
		for mx in groups: groups[mx].sort()
		sub256.sort()

		arr = []
		for mx in groups:
			if mx==512: continue
			arr += [str(v).replace('(','').replace(')','').replace(' ','') for v in groups[mx]]
			#print(groups[mx])

		data.append('const char[] IPAK8_%s={%s};' %(sname, ','.join(arr)))

		g = groups.pop(512)
		arr = [str(v).replace('(','').replace(')','').replace(' ','') for v in g]

		if tris:
			for v in tris:
				arr.append(str(v).replace('(','\n').replace(')','').replace(' ',''))

		data.append('const ushort[] IPAK16_%s={%s};' % (sname, ','.join(arr)))


		arr = [str(v).replace('(','').replace(')','').replace(' ','') for v in sub256]
		data.append('const char[] IPAK8S_%s={%s};' % (sname, ','.join(arr)))


		unpak += [
			'int uidx=0;',
			'for (int i=0; i<IPAK8_%s.len; i++){' % sname,
			'	triangles_%s[uidx++] = IPAK8_%s[i];' % (name, sname),
			'}',
			'for (int i=0; i<IPAK16_%s.len; i++){' % sname,
			'	triangles_%s[uidx++] = IPAK16_%s[i];' % (name, sname),
			'}',
			'for (int i=0; i<IPAK8S_%s.len; i++){' % sname,
			'	triangles_%s[uidx++] = IPAK8S_%s[i]+256;' % (name, sname),
			'}',

		]

	elif as_quads:
		inc = 16
		for p in ob.data.polygons:
			if p.material_index not in indices_by_mat:
				indices_by_mat[p.material_index] = {'num':0, 'indices':[]}

			if len(p.vertices)==4:
				x,y,z,w = p.vertices
				indices_by_mat[p.material_index]['indices'].append((x,y,z,w))
				indices_by_mat[p.material_index]['num'] += 6

				dy = y-x
				dz = z-x
				dw = w-x

				dx = x-inc
				dy = y-inc
				dz = z-inc
				dw = w-inc

				ddy = dy - dx
				ddz = dz - dx
				ddw = dw - dx

				indices.append(str(x+i_off))
				if 1:
					indices.append(str(y+i_off))
					indices.append(str(z+i_off))

					###indices.append(str(p.vertices[2]))
					indices.append(str(w+i_off) + '//%s %s %s %s//%s %s %s\n'%(dx, dy,dz,dw, ddy, ddz, ddw) )
					###indices.append(str(p.vertices[0]))

				num_i += 6
			elif len(p.vertices)==3:
				x,y,z = p.vertices
				w = 65000
				indices_by_mat[p.material_index]['indices'].append((x,y,z,w))
				indices_by_mat[p.material_index]['num'] += 3

				indices.append(str(p.vertices[0]+i_off))
				indices.append(str(p.vertices[1]+i_off))
				indices.append(str(p.vertices[2]+i_off))

				#indices.append(str(p.vertices[2]))
				#num_i += 6

				indices.append(str(65000))
				#indices.append('0')
				num_i += 3

			else:
				raise RuntimeError('TODO polygon len verts: %s' % len(p.vertices))

			inc += 1

	else:
		raise RuntimeError('triangles are deprecated')
		for p in ob.data.polygons:
			indices.append(str(p.vertices[0]))
			indices.append(str(p.vertices[1]))
			indices.append(str(p.vertices[2]))
			num_i += 3
			if len(p.vertices)==4:
				indices.append(str(p.vertices[2]))
				indices.append(str(p.vertices[3]))
				indices.append(str(p.vertices[0]))
				num_i += 3

	if len(indices_by_mat) > 1:
		for midx in indices_by_mat:
			mi = [str(v).replace('(','').replace(')','').replace(' ', '') for v in indices_by_mat[midx]['indices']]
			data += [
				'const ushort[] INDICES_%s_%s={%s};' %(sname, midx, ', '.join(mi)),
			]

	elif unpak:
		data += [
		'ushort[%s] triangles_%s;' %(len(indices),name),
		]
	else:
		data += [
		'const ushort[] INDICES_%s={%s};' %(sname, ','.join(indices)),
		#'const short[] INDICES_%s={%s};' %(sname, ','.join(indices)),
		#'const ushort[%s] INDICES_%s;' %(len(indices),sname),
		]

	mat = []
	for vec in ob.matrix_local:
		mat += [str(v) for v in vec]

	if USE_CPU_XFORM:
		data += [
			'int %s_vbuff;' % name,
			'float[] %s_mat={%s};' %(name,','.join(mat)),
		]
	else:
		data += [
			'int %s_vbuff;' % name,
			'float[3] %s_pos = {%s};' %(name,','.join( [str(v) for v in ob.location] )),
			'float[3] %s_rot = {%s};' %(name,','.join( [str(v) for v in ob.rotation_euler] )),
			'float[3] %s_scl = {%s};' %(name,','.join( [str(v) for v in ob.scale] )),
		]

	if use_vertex_colors:
		data.append(
		'int %s_cbuff;' % name
		)

	if len(indices_by_mat) > 1:
		for midx in indices_by_mat:
			data.append('int %s_%s_ibuff;' % (name,midx))
	else:
		data.append('int %s_ibuff;' % name)

	if mirror:
		ob.scale.x = -ob.scale.x
		mat = []
		for vec in ob.matrix_local:
			mat += [str(v) for v in vec]

	setup = [
		'%s_vbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_vbuff);' % name,
		#'gl_buffer_data(%s_vbuff, VERTS_%s.len, VERTS_%s);' %(name, sname,sname),

		#'gl_buffer_f16(%s_vbuff, VERTS_%s.len, VERTS_%s);' %(name, sname,sname),
		'gl_buffer_f16(%s, VERTS_%s.len, VERTS_%s);' %(mirror, sname,sname),


		'gl_vertex_attr_pointer(posloc, 3);',
		'gl_enable_vertex_attr_array(posloc);',
	]

	if use_vertex_colors:
		setup += [

			'%s_cbuff = gl_new_buffer();' % name,
			'gl_bind_buffer(%s_cbuff);' % name,
			#'gl_buffer_data(%s_cbuff, COLORS_%s.len, COLORS_%s);' %(name, sname,sname),
			#'gl_buffer_f16(%s_cbuff, COLORS_%s.len, COLORS_%s);' %(name, sname,sname),
		]

	if use_vertex_colors:
		if '--Oz' in sys.argv and '--icolor' in sys.argv:
			setup += [
			'int ii=0;',
			'for (int i=0; i<ICOLORS_%s.len; i++){' %sname ,
			'	int clr_index = ICOLORS_%s[i]*3;' % sname,
			'	colors_%s[ii++] = COLOR_MAP_%s[clr_index];' %(name, sname),
			'	colors_%s[ii++] = COLOR_MAP_%s[clr_index+1];' %(name, sname),
			'	colors_%s[ii++] = COLOR_MAP_%s[clr_index+2];' %(name, sname),
			'}',
			'gl_buffer_f8(%s, colors_%s.len, &colors_%s);' %(mirror, name,name),
			]

		else:
			setup += [
			'gl_buffer_f8(%s, COLORS_%s.len, COLORS_%s);' %(mirror, sname,sname),

			]

		setup += [
			'gl_vertex_attr_pointer(clrloc, 3);',
			'gl_enable_vertex_attr_array(clrloc);',
		]

	if len(indices_by_mat) > 1:
		for midx in indices_by_mat:
			setup += [
				'%s_%s_ibuff = gl_new_buffer();' % (name,midx),
				'gl_bind_buffer_element(%s_%s_ibuff);' % (name,midx),
				'gl_buffer_element(%s, INDICES_%s_%s.len, INDICES_%s_%s);' %(mirror, sname,midx, sname,midx),
			]
	else:
		setup += [
		'%s_ibuff = gl_new_buffer();' % name,
		'gl_bind_buffer_element(%s_ibuff);' % name,
		]

		if unpak:
			setup += unpak
			setup.append(
			'gl_buffer_element(%s, triangles_%s.len, &triangles_%s);' %(mirror, name, name)
			)

		else:
			setup += [
				'gl_buffer_element(%s, INDICES_%s.len, INDICES_%s);' %(mirror, sname,sname),
			]
	if USE_CPU_XFORM:
		draw = [
			'gl_bind_buffer(%s_vbuff);' % name,
			'gl_uniform_mat4fv(mloc, %s_mat);' % name,  ## update object matrix uniform
		]
	else:
		draw = [
			'gl_bind_buffer(%s_vbuff);' % name,
			'gl_uniform_3fv(mploc, &%s_pos);' % name,  ## update object position
			'gl_uniform_3fv(msloc, &%s_scl);' % name,  ## update object scale
			'gl_uniform_3fv(mrloc, &%s_rot);' % name,  ## update object rotation

			'gl_uniform_3fv(sloc, &s_uni);',
			'gl_uniform_3fv(nloc, &n_uni);',

		]

	if len(indices_by_mat) > 1:
		needs_upload = False
		lower_eyelid = None
		for midx in indices_by_mat:
			mat = ob.data.materials[midx]
			if mat.zigzag_object_type == "LOWER_EYELID":
				lower_eyelid=midx
				break

		for midx in indices_by_mat:
			mat = ob.data.materials[midx]
			if mat.zigzag_object_type != "NONE":
				draw += [
					'bool needs_upload=false;'
				]

				data += [
					'float eyes_x=0.0;'
					'float eyes_y=0.0;'
					'bool blink=false;',
				]
				break


		for midx in indices_by_mat:
			mat = ob.data.materials[midx]
			if mat.zigzag_object_type != "NONE":
				if mat.zigzag_object_type=="LOWER_LIP":
					draw += [
						'if(js_rand() < 0.06){',
						#'	gl_trans(%s_%s_ibuff,0, (js_rand()-0.25)*0.1 ,0);' % (name,midx),
						'	gl_trans(%s_%s_ibuff,0, 0, (js_rand()-0.25)*0.1);' % (name,midx),
						'	needs_upload=true;',
						'}',
					]
				elif mat.zigzag_object_type=="EYES":
					draw += [
						'if(js_rand() < 0.03){',
						'	eyes_x=(js_rand()-0.5)*0.05;',
						'	eyes_y=(js_rand()-0.5)*0.01;',

						#'	rotateZ(%s_mat, eyes_x*2);' %name,

						#'	gl_trans(%s_%s_ibuff, (js_rand()-0.5)*0.05,(js_rand()-0.5)*0.01,0);' % (name,midx),
						#'	gl_trans(%s_%s_ibuff, eyes_x,eyes_y,0);' % (name,midx),
						'	gl_trans(%s_%s_ibuff, eyes_x,0,eyes_y);' % (name,midx),
						'	needs_upload=true;',
					]
					if lower_eyelid is not None:
						draw += [
						#'	gl_trans(%s_%s_ibuff, eyes_x*0.25,(eyes_y*0.4)+( (js_rand()-0.35) *0.07),0.025);' % (name,lower_eyelid),
						'	gl_trans(%s_%s_ibuff, eyes_x*0.25, -0.025, (eyes_y*0.4)+( (js_rand()-0.35) *0.07));' % (name,lower_eyelid),
						]

					draw.append('}')

				elif mat.zigzag_object_type=="UPPER_EYELID":
					draw += [
						'if(js_rand() < 0.06 || needs_upload){',
						#'	gl_trans(%s_%s_ibuff, eyes_x*0.2, ((js_rand()-0.7)*0.07)+(eyes_y*0.2) ,0.05);' % (name,midx),
						'	gl_trans(%s_%s_ibuff, eyes_x*0.2, -0.05, ((js_rand()-0.7)*0.07)+(eyes_y*0.2) );' % (name,midx),
						'	needs_upload=true;',
						'}',
					]

				needs_upload = True

		if needs_upload:
			draw.append(
				'if(needs_upload) { gl_trans_upload(%s_vbuff); }' % name
			)

		if use_vertex_colors:
			draw.append('gl_bind_buffer(%s_cbuff);' % name)

		for midx in indices_by_mat:
			num = indices_by_mat[midx]['num']
			draw.append('gl_bind_buffer_element(%s_%s_ibuff);' % (name,midx))
			mat = ob.data.materials[midx]
			r,g,b,a = mat.diffuse_color
			if mirror:
				draw.append('gl_draw_tris_tint( %s, %s,%s,%s );' % (num*2,r,g,b))
			else:
				draw.append('gl_draw_tris_tint( %s, %s,%s,%s );' % (num,r,g,b))

	else:
		if use_vertex_colors:
			draw.append('gl_bind_buffer(%s_cbuff);' % name)
		draw.append('gl_bind_buffer_element(%s_ibuff);' % name)

		if mirror:
			draw += [
			'gl_draw_triangles( %s );' % (num_i*2),
			]

		else:
			draw += [
			'gl_draw_triangles( %s );' % num_i,
			]


	return data, setup, draw

EXAMPLE1 = '''
rotateY( self.matrix, self.my_prop );
'''

def test_scene( test_materials=True, test_twist=False, spin_script=False ):
	cu = bpy.data.objects['Cube']
	cu.hide_set(True)
	ob = libgenzag.monkey(materials=test_materials)

	if spin_script:
		a = bpy.data.texts.new(name='example1.c3')
		a.from_string(EXAMPLE1)
		ob.c3_script0 = a
		ob['my_prop'] = 0.01
	ob.color = [.7,.5,.5, 1.0]

	if 0:
		bpy.ops.object.mode_set(mode="EDIT")
		#bpy.ops.mesh.sort_elements(type="MATERIAL", elements={"FACE"} )  ## bigger
		bpy.ops.mesh.sort_elements(type="MATERIAL", elements={"VERT"} )   ## smaller
		bpy.ops.object.mode_set(mode="OBJECT")

	#ob.rotation_euler.x = -math.pi/2
	#bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

	if test_twist:

		mod = ob.modifiers.new(name="twist-x", type="SIMPLE_DEFORM")
		mod.angle = math.pi * 0.5

		mod = ob.modifiers.new(name="twist-y", type="SIMPLE_DEFORM")
		mod.angle = -math.pi * 0.25
		mod.deform_axis="Y"

if __name__=='__main__':
	for arg in sys.argv:
		if arg.startswith('--test='):
			import libtestzag
			tname = arg.split('=')[-1]
			getattr(libtestzag, tname)()
			build_wasm(bpy.data.worlds[0], name='c3_'+tname, preview=False)
			sys.exit()
		elif arg.startswith('--import='):
			exec( open( arg.split('=')[-1] ).read() )

	for arg in sys.argv:
		if arg.startswith('--export='):
			path = arg.split('=')[-1]
			build_wasm(bpy.data.worlds[0], out=path)
			print('saved:', path)

	if '--pipe' in sys.argv:
		bpy.ops.c3zag.run()

	if '--test-wasm' in sys.argv:
		test_scene()
		build_wasm(bpy.data.worlds[0])
