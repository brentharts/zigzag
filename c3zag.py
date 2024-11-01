#!/usr/bin/python3
import os, sys, subprocess, base64, webbrowser, zipfile
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)
import zigzag

HELP='''
run: python c3zag.py [.blend]

options:
	--test runs simple WASM test without blender
	--Oz optimize for size
	--icolor use indexed vertex colors

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


float16[] cube_data = {
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

float16[] colors = {
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
	gl_buffer_f16(vbuff, cube_data.len, cube_data);

	int cbuff = gl_new_buffer();
	gl_bind_buffer(cbuff);
	gl_buffer_f16(cbuff, colors.len, colors);

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

//extern fn void gl_buffer_data(int idx, int sz, float *ptr);
//extern fn void gl_buffer_u16(int idx, int sz, ushort *ptr);
extern fn void gl_buffer_f16(int idx, int sz, float16 *ptr);
extern fn void gl_buffer_f8(int idx, int sz, char *ptr);

//extern fn void gl_buffer_f16_flip(int idx, int sz, float16 *ptr);

extern fn void gl_buffer_element(int idx, int sz, ushort *ptr);
//extern fn void gl_buffer_element(int idx, int sz, short *ptr);

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
		this.gl.viewport(0,0,w,h);
		this.gl.enable(this.gl.DEPTH_TEST);
		//this.gl.clearColor(1,0,0, 1);
		//this.gl.clear(this.gl.COLOR_BUFFER_BIT)
	}

	//gl_enable(ptr){
	//	const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
	//	//console.log("gl enable:", key);
	//	this.gl.enable(this.gl[key])
	//}

	//gl_depth_func(ptr){
	//	const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
	//	//console.log("gl depthFunc:", key);
	//	this.gl.depthFunc(this.gl[key])
	//}

	gl_new_buffer(){
		return this.bufs.push(this.gl.createBuffer())-1
	}

	gl_bind_buffer(i){
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.bufs[i])
	}
	gl_bind_buffer_element(i){
		this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER,this.bufs[i])
	}

	//gl_buffer_data(i, sz, ptr){
	//	const b=this.bufs[i];
	//	console.log("buffer data:", b);
	//	const arr = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
	//	this.gl.bufferData(this.gl.ARRAY_BUFFER, arr, this.gl.STATIC_DRAW)
	//}

	gl_buffer_f16(i, sz, ptr){
		var v=new Float16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log('vertex data:', v.length);
		//this.nverts=v.length;
		this.nverts=v.length/3;
		if(i){
			var a=new Array(...v);
			for(var j=0;j<v.length;j+=3){
				a.push(-v[j]);
				a.push(v[j+1]);
				a.push(v[j+2]);
			}
			console.log('vmirror:', a);
			v=a;
		}
		this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array(v), this.gl.STATIC_DRAW)
	}

	gl_buffer_f8(i,sz,ptr){
		var v=new Uint8Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log('new vcolors');
		console.log(v);
		if(i){
			v=new Array(...v).concat(new Array(...v));
			console.log('mirror vcolor:', v);
		}
		this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array(v), this.gl.STATIC_DRAW)
	}

	gl_buffer_element(i, sz, ptr){
		const v = new Uint16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log(v);
		var a=[];
		for(var j=0;j<v.length;j+=4){
			//a.push(v[j],v[j+1],v[j+2]);

			a.push(v[j]);
			a.push(v[j+1]);
			a.push(v[j+2]);

			if(v[j+3]==65000)continue;
			//if(!v[j+3])continue;

			//a.push(v[j+2],v[j+3],v[j+0]);

			a.push(v[j+2]);
			a.push(v[j+3]);
			a.push(v[j]);

		}
		if(i){
			var b=[];
			// mirror indices: copy and offset by length of input vector
			//for(var j=0;j<a.length;j++)b.push(a[j]+a.length);  //OOPS
			for(var j=0;j<a.length;j++)b.push(a[j]+this.nverts);
			console.log('mirror b:',b);
			a=a.concat(b);
			console.log('mirror a+b:', a);		
		}
		this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(a), this.gl.STATIC_DRAW)
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

	//gl_viewport(x,y,w,h){
	//	this.gl.viewport(x,y,w,h)
	//}

	gl_uniform_mat4fv(a,ptr){
		const mat = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,16);
		this.gl.uniformMatrix4fv(this.locs[a], false, mat)
	}
	gl_draw_triangles(n){
		//console.log('draw triangles:', n);
		this.gl.drawElements(this.gl.TRIANGLES,n,this.gl.UNSIGNED_SHORT,0)
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

## gone in default blender 4.2 :(
#bpy.ops.preferences.addon_enable(module="mesh_auto_mirror")
import mesh_auto_mirror
mesh_auto_mirror.register()


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
	o = wasm.replace('.wasm', '.opt.wasm')
	cmd = ['wasm-opt', '-o',o, '-Oz', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	return o

def c3_wasm_strip(wasm):
	a = b'\x00,\x0ftarget_features\x02+\x0fmutable-globals+\x08sign-ext'
	b = open(wasm,'rb').read()
	if b.endswith(a):
		c = b[:-len(a)]
		print('c3 wasm stripped bytes:', len(a) )
		open(wasm,'wb').write(c)

SERVER_PROC = None
def build_wasm( world ):
	global SERVER_PROC
	if SERVER_PROC: SERVER_PROC.kill()
	o = blender_to_c3(world)
	o = '\n'.join(o)
	if '--debug' in sys.argv: print(o)
	wasm = c3_compile(WASM_MINI_GL + o)
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
	jsapi = zigzag.JS_API_HEADER + JS_MINI_GL
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
		zigzag.JS_DECOMP,
		'</script>',
	]
	out = 'blender-c3zag-preview.html'
	open(out,'w').write('\n'.join(o))
	webbrowser.open(out)

	if sys.platform != 'win32':
		os.system('ls -l %s' % out)
		os.system('ls -lh %s' % out)

		cmd = ['zip', '-9', out+'.zip', out]
		print(cmd)
		subprocess.check_call(cmd)
		os.system('ls -l %s.zip' % out)
		os.system('ls -lh %s.zip' % out)


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

	ploc = gl_get_uniform_location(prog, "P");  // projection Pmat
	vloc = gl_get_uniform_location(prog, "V");  // view matrix
	mloc = gl_get_uniform_location(prog, "M");  // model matrix

	posloc = gl_get_attr_location(prog, "vp");  // vertex position
	clrloc = gl_get_attr_location(prog, "vc");  // vertex color

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

BLENDER_SHADER = '''
const char* VERTEX_SHADER = `
attribute vec3 vp;
uniform mat4 P;
uniform mat4 V;
uniform mat4 M;
attribute vec3 vc;
varying vec3 VC;
void main(void){
	gl_Position=P*V*M*vec4(vp,1.);
	VC=vc;
}
`;

const char* FRAGMENT_SHADER = `
precision mediump float;
varying vec3 VC;
void main(void){
	gl_FragColor=vec4(VC*(1.0/255.0),1.0);
}
`;

'''

def is_mesh_sym(ob):
	left  = []
	right = []
	mid   = []
	for v in ob.data.vertices:
		x,y,z = v.co
		if x==0:
			mid.append((x,y,z))
		elif x < 0:
			left.append( (abs(x),y,z) )
		else:
			right.append((x,y,z))

	left.sort()
	right.sort()
	mid.sort()
	print('left:',len(left))
	print('right:',len(right))
	print('mid:',len(mid))

	if len(left)==len(right) and len(mid):
		return (tuple(left)==tuple(right))

	return False

def blender_to_c3(world):
	data = [
		SHADER_HEADER,
		BLENDER_SHADER,
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

			is_symmetric = is_mesh_sym(ob)  ## TODO this should check for a user added mirror mod on x
			if is_symmetric:
				bpy.ops.object.mode_set(mode="EDIT")
				bpy.ops.object.automirror()
				bpy.ops.object.mode_set(mode="OBJECT")
			a,b,c = mesh_to_c3(ob, mirror=is_symmetric)
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
		#'	gl_enable("DEPTH_TEST");',
		#'	gl_depth_func("LEQUAL");',
		#'	gl_viewport(0,0,800,600);',
		#'	gl_clear(0.5,0.5,0.5, 1.0, 1.0);',
		'	gl_uniform_mat4fv(ploc, proj_matrix);',
		'	gl_uniform_mat4fv(vloc, view_matrix);',
	]
	for ln in draw:
		update.append('\t'+ln)
	update.append('}')

	return data + update + main

def mesh_to_c3(ob, as_quads=True, mirror=False):
	if mirror: mirror = 1
	else: mirror = 0

	name = zigzag.safename(ob.data)
	sname = name.upper()

	data = []
	colors = []
	verts = []
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
	num_i = 0
	i_off = 0
	if '--Oz' in sys.argv and len(ob.data.vertices) < 512:
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
			elif len(p.vertices)==4:
				a,b,c,d = p.vertices
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
			if len(p.vertices)==4:
				x,y,z,w = p.vertices
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

	if unpak:
		data += [
		'ushort[%s] triangles_%s;' %(num_i,name),
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


	data += [
		'int %s_vbuff;' % name,
		'int %s_ibuff;' % name,
		'int %s_cbuff;' % name,
		'float[] %s_mat={%s};' %(name,','.join(mat)),
	]

	if mirror:
		ob.scale.x = -ob.scale.x
		mat = []
		for vec in ob.matrix_local:
			mat += [str(v) for v in vec]

		data += [
		#'int %s_mirror_vbuff;' % name,
		#'float[] %s_mirror_mat={%s};' %(name,','.join(mat)),

		]

	setup = [
		'%s_vbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_vbuff);' % name,
		#'gl_buffer_data(%s_vbuff, VERTS_%s.len, VERTS_%s);' %(name, sname,sname),

		#'gl_buffer_f16(%s_vbuff, VERTS_%s.len, VERTS_%s);' %(name, sname,sname),
		'gl_buffer_f16(%s, VERTS_%s.len, VERTS_%s);' %(mirror, sname,sname),


		'gl_vertex_attr_pointer(posloc, 3);',
		'gl_enable_vertex_attr_array(posloc);',


		'%s_cbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_cbuff);' % name,
		#'gl_buffer_data(%s_cbuff, COLORS_%s.len, COLORS_%s);' %(name, sname,sname),
		#'gl_buffer_f16(%s_cbuff, COLORS_%s.len, COLORS_%s);' %(name, sname,sname),
	]

	if mirror and 0:
		#wasm-ld: error: /tmp/test-c3.o: undefined symbol: __extendhfsf2
		#wasm-ld: error: /tmp/test-c3.o: undefined symbol: __truncsfhf2
		if False:
			## TODO how big is it to link with stdlib and the float16 funcs?
			setup += [
			'%s_mirror_vbuff = gl_new_buffer();' % name,
			'gl_bind_buffer(%s_mirror_vbuff);' % name,
			'for (int i=0; i<VERTS_%s.len; i+=3){' %sname,
			'	verts_mirror_%s[i] = -VERTS_%s[i];' % (name,sname),
			'	verts_mirror_%s[i+1] = VERTS_%s[i+1];' % (name,sname),
			'	verts_mirror_%s[i+2] = VERTS_%s[i+2];' % (name,sname),
			'}',
			'gl_buffer_f16(%s_mirror_vbuff, verts_mirror_%s.len, &verts_mirror_%s);' %(name, name,name),

			]


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
		


	draw = [
		'gl_bind_buffer(%s_vbuff);' % name,

		#'gl_vertex_attr_pointer(posloc, 3);',
		#'gl_enable_vertex_attr_array(posloc);',


		'gl_bind_buffer(%s_cbuff);' % name,

		#'rotateZ(%s_mat, 15.0);' % name,

		'gl_uniform_mat4fv(mloc, %s_mat);' % name,  ## update object matrix uniform
		'gl_bind_buffer_element(%s_ibuff);' % name,
		#'gl_draw_triangles( INDICES_%s.len );' % sname,
		#'gl_draw_triangles( %s );' % num_i,
	]

	if mirror:
		print(num_i)
		#raise RuntimeError(num_i*2)
		draw += [
		'gl_draw_triangles( %s );' % (num_i*2),
		#'gl_draw_triangles( %s );' % (num_i+128),

		]

	else:
		draw += [
		'gl_draw_triangles( %s );' % num_i,

		]

	if mirror and 0:
		if False:  ## TODO this should be an option
			##TODO this is the simple way, but with a mesh copy we animate each side on its own,
			## and support switching to a different vertex color buffer.
			draw += [
			'%s_mat[0] = -%s_mat[0];' % (name,name),    ## flip x
			'%s_mat[4] = -%s_mat[4];' % (name,name),    ## flip x
			'gl_uniform_mat4fv(mloc, %s_mat);' % name,  ## update object matrix uniform
			'gl_draw_triangles( %s );' % num_i,
			'%s_mat[0] = -%s_mat[0];' % (name,name),    ## flip x back
			'%s_mat[4] = -%s_mat[4];' % (name,name),    ## flip x back
			]
		else:
			draw += [
			'gl_bind_buffer(%s_mirror_vbuff);' % name,

			#'gl_vertex_attr_pointer(posloc, 3);',
			#'gl_enable_vertex_attr_array(posloc);',

			#'gl_bind_buffer(%s_cbuff);' % name,


			#'gl_uniform_mat4fv(mloc, %s_mat);' % name,  ## update object matrix uniform
			#'gl_bind_buffer_element(%s_ibuff);' % name,
			'gl_draw_triangles( %s );' % num_i,

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
	ob.color = [.7,.5,.5, 1.0]

	ob.rotation_euler.x = -math.pi/2
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)



if __name__=='__main__':
	test_scene()
	build_wasm(bpy.data.worlds[0])
