#!/usr/bin/python3
import os, sys, subprocess, base64, webbrowser, zipfile
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)
import zigzag

HELP='''
run: python c3zag.py [.blend]

options:
	--test runs simple WASM test without blender

'''

C3 = '/usr/local/bin/c3c'
GZIP = 'gzip'

islinux=iswindows=isapple=c3gz=c3zip=None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	if not os.path.isfile(BLENDER):
		BLENDER = 'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe'

	c3zip = 'https://github.com/c3lang/c3c/releases/download/v0.6.3/c3-windows.zip'
	C3 = os.path.join(_thisdir,'c3/c3c.exe')
	GZIP = os.path.abspath(os.path.join(_thisdir,'gzip.exe'))
	iswindows=True
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-macos.zip'
	isapple=True
else:
	BLENDER = 'blender'
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

DEBUG_SHADER = '''
const char* VERTEX_SHADER = `
attribute vec3 position;
uniform mat4 Pmat;
uniform mat4 Vmat;
uniform mat4 Mmat;
attribute vec3 color;
varying vec3 vColor;
void main(void){
	gl_Position = Pmat*Vmat*Mmat*vec4(position, 1.);
	vColor = color;
}
`;

const char* FRAGMENT_SHADER = `
precision mediump float;
varying vec3 vColor;
void main(void) {
	gl_FragColor = vec4(vColor, 1.0);
}
`;

'''

DEBUG_CAMERA = '''
float[] proj_matrix = {1.3737387097273113,0,0,0,0,1.8316516129697482,0,0,0,0,-1.02020202020202,-1,0,0,-2.0202020202020203,0};
float[] view_matrix = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
'''

WASM_TEST = DEBUG_SHADER + DEBUG_CAMERA + '''
float[] mov_matrix = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};


float[] cube_data = {
	-1,-1,-1, 1,-1,-1, 1, 1,-1, -1, 1,-1,
	-1,-1, 1, 1,-1, 1, 1, 1, 1, -1, 1, 1,
	-1,-1,-1, -1, 1,-1, -1, 1, 1, -1,-1, 1,
	1,-1,-1, 1, 1,-1, 1, 1, 1, 1,-1, 1,
	-1,-1,-1, -1,-1, 1, 1,-1, 1, 1,-1,-1,
	-1, 1,-1, -1, 1, 1, 1, 1, 1, 1, 1,-1, 
};

ushort[] indices = {
	0,1,2, 0,2,3, 4,5,6, 4,6,7,
	8,9,10, 8,10,11, 12,13,14, 12,14,15,
	16,17,18, 16,18,19, 20,21,22, 20,22,23 
};

float[] colors = {
	0.5,0.3,0.7, 0.5,0.3,0.7, 0.5,0.3,0.7, 0.5,0.3,0.7,
	1,1,0.3, 1,1,0.3, 1,1,0.3, 1,1,0.3,
	0,0,1, 0,0,1, 0,0,1, 0,0,1,
	1,0,0, 1,0,0, 1,0,0, 1,0,0,
	1,1,0, 1,1,0, 1,1,0, 1,1,0,
	0,1,0, 0,1,0, 0,1,0, 0,1,0
};


fn void main() @extern("main") @wasm {
	view_matrix[14] = view_matrix[14] -6.0;  //zoom 
	gl_init(800, 600);
	int vbuff = gl_new_buffer();
	gl_bind_buffer(vbuff);
	gl_buffer_data(vbuff, cube_data.len, cube_data);

	int cbuff = gl_new_buffer();
	gl_bind_buffer(cbuff);
	gl_buffer_data(cbuff, colors.len, colors);

	int ibuff = gl_new_buffer();
	gl_bind_buffer_element(ibuff);
	gl_buffer_element(ibuff, indices.len, indices);

	int vs = gl_new_vshader(VERTEX_SHADER);
	int fs = gl_new_fshader(FRAGMENT_SHADER);

	int prog = gl_new_program();
	gl_attach_vshader(prog, vs);
	gl_attach_fshader(prog, fs);
	gl_link_program( prog );

	int ploc = gl_get_uniform_location(prog, "Pmat");
	int vloc = gl_get_uniform_location(prog, "Vmat");
	int mloc = gl_get_uniform_location(prog, "Mmat");

	gl_bind_buffer(vbuff);
	int posloc = gl_get_attr_location(prog, "position");
	gl_vertex_attr_pointer(posloc, 3);
	gl_enable_vertex_attr_array(posloc);

	gl_bind_buffer(cbuff);
	int clrloc = gl_get_attr_location(prog, "color");
	gl_vertex_attr_pointer(clrloc, 3);
	gl_enable_vertex_attr_array(clrloc);

	gl_use_program(prog);


	gl_enable("DEPTH_TEST");
	gl_depth_func("LEQUAL");

	gl_viewport(0,0,800,600);
	gl_clear(0.5,0.5,0.5, 1.0, 1.0);

	gl_uniform_mat4fv(ploc, proj_matrix);
	gl_uniform_mat4fv(vloc, view_matrix);
	gl_uniform_mat4fv(mloc, mov_matrix);

	gl_bind_buffer_element(ibuff);
	gl_draw_triangles( indices.len );

}


'''

WASM_MINI_GL = '''
def Entry = fn void();
extern fn void js_set_entry(Entry entry);


extern fn void gl_init(int w, int h);
extern fn void gl_enable(char *ptr);
extern fn void gl_depth_func(char *ptr);
extern fn int  gl_new_buffer();

extern fn void gl_bind_buffer(int idx);
extern fn void gl_bind_buffer_element(int idx);

extern fn void gl_buffer_data(int idx, int sz, float *ptr);
extern fn void gl_buffer_u16(int idx, int sz, ushort *ptr);
extern fn void gl_buffer_element(int idx, int sz, ushort *ptr);

extern fn int gl_new_program();
extern fn void gl_link_program(int prog);

extern fn void gl_attach_vshader(int prog, int s);
extern fn void gl_attach_fshader(int prog, int s);
extern fn int  gl_new_vshader(char *c);
extern fn int  gl_new_fshader(char *c);

extern fn int gl_get_uniform_location(int a, char *ptr);
extern fn int gl_get_attr_location(int a, char *ptr);

extern fn void gl_enable_vertex_attr_array(int loc);
extern fn void gl_vertex_attr_pointer(int loc, int n);

extern fn void gl_use_program(int prog);

extern fn void gl_clear(float r, float g, float b, float a, float z);
extern fn void gl_viewport(int x, int y, int w, int h);

extern fn void gl_uniform_mat4fv(int loc, float *mat);
extern fn void gl_draw_triangles(int len);

extern fn float js_sin(float a);
extern fn float js_cos(float a);

'''

JS_MINI_GL = 'class api {' + zigzag.JS_API_PROXY + '''
	js_set_entry(a){
		this.entryFunction=this.wasm.instance.exports.__indirect_function_table.get(a);
		const f=(ts)=>{
			this.dt=(ts-this.prev)/1000;
			this.prev=ts;
			this.entryFunction();
			window.requestAnimationFrame(f)
		};
		window.requestAnimationFrame((ts)=>{
			this.prev=ts;
			window.requestAnimationFrame(f)
		});
	}

	reset(wasm,id,bytes){
		this.wasm=wasm;
		this.canvas=document.getElementById(id);
		this.gl=this.canvas.getContext('webgl');
		this.bufs=[];
		this.vs=[];
		this.fs=[];
		this.progs=[];
		this.locs=[];
		this.wasm.instance.exports.main();
	}

	gl_init(w,h) {
		this.canvas.width=w;
		this.canvas.height=h;
		this.gl.clearColor(1,0,0, 1);
		this.gl.clear(this.gl.COLOR_BUFFER_BIT)
	}

	gl_enable(ptr){
		const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log("gl enable:", key);
		this.gl.enable(this.gl[key])
	}

	gl_depth_func(ptr){
		const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log("gl depthFunc:", key);
		this.gl.depthFunc(this.gl[key])
	}
	gl_new_buffer(){
		return this.bufs.push(this.gl.createBuffer())-1
	}
	gl_bind_buffer(i){
		const b=this.bufs[i];
		console.log("bind buffer:", b);
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,b)
	}
	gl_bind_buffer_element(i){
		const b=this.bufs[i];
		console.log("bind buffer element:", b);
		this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER,b)
	}

	gl_buffer_data(i, sz, ptr){
		const b=this.bufs[i];
		console.log("buffer data:", b);
		const arr = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		this.gl.bufferData(this.gl.ARRAY_BUFFER, arr, this.gl.STATIC_DRAW)
	}
	gl_buffer_u16(i, sz, ptr){
		const b=this.bufs[i];
		console.log("buffer data:", b);
		const arr = new Uint16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		this.gl.bufferData(this.gl.ARRAY_BUFFER, arr, this.gl.STATIC_DRAW)
	}

	gl_buffer_element(i, sz, ptr){
		const b=this.bufs[i];
		console.log("element buffer data:", b);
		const arr = new Uint16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log(arr);
		this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, arr, this.gl.STATIC_DRAW)
	}

	gl_new_vshader(ptr){
		const c = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log('new vertex shader', c);
		const s = this.gl.createShader(this.gl.VERTEX_SHADER);
		this.gl.shaderSource(s,c);
		this.gl.compileShader(s);
		return this.vs.push(s)-1
	}
	gl_new_fshader(ptr){
		const c = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log('new fragment shader', c);
		const s = this.gl.createShader(this.gl.FRAGMENT_SHADER);
		this.gl.shaderSource(s,c);
		this.gl.compileShader(s);
		return this.fs.push(s)-1
	}
	gl_new_program(){
		return this.progs.push(this.gl.createProgram())-1
	}
	gl_attach_vshader(a,b){
		const prog = this.progs[a];
		this.gl.attachShader(prog, this.vs[b])
	}
	gl_attach_fshader(a,b){
		const prog = this.progs[a];
		this.gl.attachShader(prog, this.fs[b])
	}
	gl_link_program(a){
		this.gl.linkProgram(this.progs[a])
	}

	gl_get_uniform_location(a,b){
		const c = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,b);
		var loc = this.gl.getUniformLocation(this.progs[a], c);
		console.log('get uniform:', loc);
		return this.locs.push(loc)-1
	}
	gl_get_attr_location(a,b){
		const c = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,b);
		var loc = this.gl.getAttribLocation(this.progs[a], c);
		console.log('get attribute:', loc);
		return loc
	}
	gl_enable_vertex_attr_array(a){
		this.gl.enableVertexAttribArray(a)
	}
	gl_vertex_attr_pointer(a,n){
		this.gl.vertexAttribPointer(a, n, this.gl.FLOAT, false,0,0)
	}

	gl_use_program(a){
		this.gl.useProgram(this.progs[a])
	}

	gl_clear(r,g,b,a,z){
		this.gl.clearColor(r,g,b,a);
		this.gl.clearDepth(z);
		this.gl.clear(this.gl.COLOR_BUFFER_BIT|this.gl.DEPTH_BUFFER_BIT)
	}
	gl_viewport(x,y,w,h){
		this.gl.viewport(x,y,w,h)
	}

	gl_uniform_mat4fv(a,ptr){
		const mat = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,16);
		this.gl.uniformMatrix4fv(this.locs[a], false, mat)
	}
	gl_draw_triangles(n){
		console.log('draw triangles:', n);
		this.gl.drawElements(this.gl.TRIANGLES, n, this.gl.UNSIGNED_SHORT, 0)
	}

	js_sin(a){
		return Math.sin(a)
	}
	js_cos(a){
		return Math.cos(a)
	}

}
new api();
'''

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
	open(jtmp,'w').write(zigzag.JS_API_HEADER + JS_MINI_GL)
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
		zigzag.JS_DECOMP,
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
		bpy.types.Object,
		"c3_script%s_disable" %i,
		bpy.props.BoolProperty(name="disable"),
	)

bpy.types.Object.c3_hide = bpy.props.BoolProperty( name="hidden on spawn")

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

		self.layout.label(text="Attach C3 Scripts")
		foundUnassignedScript = False
		for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
			hasProperty = (
				getattr(ob, "c3_script" + str(i)) != None
			)
			if hasProperty or not foundUnassignedScript:
				row = self.layout.row()
				row.prop(ob, "c3_script" + str(i))
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
		self.layout.operator("c3.export_wasm", icon="CONSOLE")


SERVER_PROC = None
def build_wasm( world ):
	global SERVER_PROC
	if SERVER_PROC: SERVER_PROC.kill()
	o = blender_to_c3(world)
	o = '\n'.join(o)
	print(o)
	wasm = c3_compile(WASM_MINI_GL + o)

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'
	open(jtmp,'w').write(zigzag.JS_API_HEADER + JS_MINI_GL)
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
		zigzag.JS_DECOMP,
		'</script>',
	]
	out = 'blender-c3zag-preview.html'
	open(out,'w').write('\n'.join(o))
	webbrowser.open(out)

SHADER_HEADER = '''
int vs;
int fs;
int prog;

int ploc;
int vloc;
int mloc;

int posloc;
int clrloc;

'''

SHADER_SETUP = '''
	vs = gl_new_vshader(VERTEX_SHADER);
	fs = gl_new_fshader(FRAGMENT_SHADER);

	prog = gl_new_program();
	gl_attach_vshader(prog, vs);
	gl_attach_fshader(prog, fs);
	gl_link_program( prog );

	ploc = gl_get_uniform_location(prog, "Pmat");
	vloc = gl_get_uniform_location(prog, "Vmat");
	mloc = gl_get_uniform_location(prog, "Mmat");

	posloc = gl_get_attr_location(prog, "position");
	clrloc = gl_get_attr_location(prog, "color");

'''

SHADER_POST = '''
	gl_use_program(prog);

'''

HELPER_FUNCS = '''
fn void rotateZ(float *m, float angle) {
	float c = js_cos(angle);
	float s = js_sin(angle);
	float mv0 = m[0];
	float mv4 = m[4];
	float mv8 = m[8];

	m[0] = c*m[0]-s*m[1];
	m[4] = c*m[4]-s*m[5];
	m[8] = c*m[8]-s*m[9];

	m[1]=c*m[1]+s*mv0;
	m[5]=c*m[5]+s*mv4;
	m[9]=c*m[9]+s*mv8;
}
fn void rotateY(float *m, float angle) {
	float c = js_cos(angle);
	float s = js_sin(angle);
	float mv0 = m[0];
	float mv4 = m[4];
	float mv8 = m[8];

	m[0] = c*m[0]+s*m[2];
	m[4] = c*m[4]+s*m[6];
	m[8] = c*m[8]+s*m[10];

	m[2] = c*m[2]-s*mv0;
	m[6] = c*m[6]-s*mv4;
	m[10] = c*m[10]-s*mv8;
}
'''


def get_scripts(ob):
	scripts = []
	for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "c3_script%s_disable" %i): continue
		txt = getattr(ob, "c3_script" + str(i))
		if txt: scripts.append(txt)
	return scripts

def has_scripts(ob):
	for i in range(zigzag.MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "c3_script%s_disable" %i): continue
		txt = getattr(ob, "c3_script" + str(i))
		if txt: return True
	return False


def blender_to_c3(world):
	data = [
		SHADER_HEADER,
		DEBUG_SHADER,
		DEBUG_CAMERA,
		HELPER_FUNCS,
	]
	setup = []
	draw = []
	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		sname = zigzag.safename(ob)

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
					draw.append( s )


			a,b,c = mesh_to_c3(ob)
			data  += a
			setup += b
			draw  += c

	main = [
		'fn void main() @extern("main") @wasm {',
		'	gl_init(800, 600);',
		'	view_matrix[14] = view_matrix[14] -3.0;',
		SHADER_SETUP,
	]
	for ln in setup:
		main.append('\t' + ln)
	main.append(SHADER_POST)
	#main.append('update();')
	main.append('js_set_entry(&update);')
	main.append('}')

	update = [
		'fn void update() @extern("update") @wasm {',
		'	gl_enable("DEPTH_TEST");',
		'	gl_depth_func("LEQUAL");',
		'	gl_viewport(0,0,800,600);',
		'	gl_clear(0.5,0.5,0.5, 1.0, 1.0);',
		'	gl_uniform_mat4fv(ploc, proj_matrix);',
		'	gl_uniform_mat4fv(vloc, view_matrix);',
	]
	for ln in draw:
		update.append('\t'+ln)
	update.append('}')

	return data + update + main

def mesh_to_c3(ob):
	name = zigzag.safename(ob.data)
	sname = name.upper()

	verts = []
	for v in ob.data.vertices:
		verts.append(str(v.co.x))
		verts.append(str(v.co.y))
		verts.append(str(v.co.z))

	indices = []
	for p in ob.data.polygons:
		indices.append(str(p.vertices[0]))
		indices.append(str(p.vertices[1]))
		indices.append(str(p.vertices[2]))
		if len(p.vertices)==4:
			indices.append(str(p.vertices[2]))
			indices.append(str(p.vertices[3]))
			indices.append(str(p.vertices[0]))


	colors = [str(random()) for i in range(len(verts))]
	mat = []
	for vec in ob.matrix_local:
		mat += [str(v) for v in vec]
	data = [
		'const float[]  VERTS_%s={%s};' %(sname, ','.join(verts)),
		'const ushort[] INDICES_%s={%s};' %(sname, ','.join(indices)),
		'const float[]  COLORS_%s={%s};' %(sname, ','.join(colors)),
		'int %s_vbuff;' % name,
		'int %s_ibuff;' % name,
		'int %s_cbuff;' % name,
		'float[] %s_mat={%s};' %(name,','.join(mat)),
	]

	setup = [
		'%s_vbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_vbuff);' % name,
		'gl_buffer_data(%s_vbuff, VERTS_%s.len, VERTS_%s);' %(name, sname,sname),

		'gl_vertex_attr_pointer(posloc, 3);',
		'gl_enable_vertex_attr_array(posloc);',


		'%s_cbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_cbuff);' % name,
		'gl_buffer_data(%s_cbuff, COLORS_%s.len, COLORS_%s);' %(name, sname,sname),

		'gl_vertex_attr_pointer(clrloc, 3);',
		'gl_enable_vertex_attr_array(clrloc);',


		'%s_ibuff = gl_new_buffer();' % name,
		'gl_bind_buffer_element(%s_ibuff);' % name,
		'gl_buffer_element(%s_ibuff, INDICES_%s.len, INDICES_%s);' %(name, sname,sname),

	]

	draw = [
		'gl_bind_buffer(%s_vbuff);' % name,
		'gl_bind_buffer(%s_cbuff);' % name,

		#'rotateZ(%s_mat, 15.0);' % name,

		'gl_uniform_mat4fv(mloc, %s_mat);' % name,  ## update object matrix uniform
		'gl_bind_buffer_element(%s_ibuff);' % name,
		'gl_draw_triangles( INDICES_%s.len );' % sname,
	]

	return data, setup, draw

EXAMPLE1 = '''
rotateY( self.matrix, self.my_prop );
'''

def test_scene():
	a = bpy.data.texts.new(name='example1.zig')
	a.from_string(EXAMPLE1)

	ob = bpy.data.objects['Cube']
	ob.hide_set(True)

	bpy.ops.mesh.primitive_monkey_add()
	ob = bpy.context.active_object
	ob.c3_script0 = a
	ob['my_prop'] = 0.01

	ob.rotation_euler.x = -math.pi/2
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)



if __name__=='__main__':
	test_scene()
	build_wasm(bpy.data.worlds[0])
