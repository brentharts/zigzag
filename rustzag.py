#!/usr/bin/env python3
import os, sys, subprocess, base64, webbrowser
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
import zigzag, libwebzag, libgenzag
from zigzag import GZIP, BLENDER, VSHADER, FSHADER, safename, is_mesh_sym

#sudo apt-get install wabt
def wasm_strip(wasm):
	o = wasm.replace('.wasm', '.strip.wasm')
	cmd = ['wasm-strip', '-o',o, wasm]
	print(cmd)
	subprocess.check_call(cmd)
	return o

def wasm_opt(wasm):
	o = wasm.replace('.wasm', '.opt.wasm')
	cmd = ['wasm-opt', '-o',o, '-Oz', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	return o

JS_ALERT = '''
	js_alert(ptr, len){
		const b=new Uint8Array(this.wasm.instance.exports.memory.buffer,ptr,len);
		window.alert(new TextDecoder().decode(b))
	}
'''


RUST_INIT = '''
	reset(wasm,id,bytes){
		this.wasm=wasm;
		this.canvas=document.getElementById(id);
		this.gl=this.canvas.getContext('webgl');
		this.gl.getExtension("OES_standard_derivatives");
		this.bufs=[];
		this.vs=[];
		this.fs=[];
		this.progs=[];
		this.locs=[];
		this.mods=[];
		this.entryFunction=this.wasm.instance.exports.update;
		this.wasm.instance.exports.main();
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

'''

def build(rs, name='rust_test', jsapi=None, preview=True, out=None):
	if not jsapi:
		jsapi=libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(
			RUST_INIT + JS_ALERT
		)

	tmp = '/tmp/%s.rs' % name
	wasm = '/tmp/%s.wasm' % name
	if type(rs) is list:
		open(tmp, 'w').write('\n'.join(rs))
	else:
		open(tmp, 'w').write(rs)
	cmd = [
		'rustc', '--target', 'wasm32-unknown-unknown',
		#'--edition', '2021',  ## c-string literals require Rust 2021 or later, but this makes a CStr
		'--crate-type', 'cdylib',
		#rustc-LLVM ERROR: Target does not support the tiny CodeModel
		#'-Ccode-model=tiny',
		'-Ccode-model=small',
		#'-opt-level=z',
		#'-opt-level=s',
		'--out-dir','/tmp',
		tmp
	]
	print(cmd)
	subprocess.check_call(cmd, cwd='/tmp')
	os.system('ls -lh /tmp/*.wasm')

	wasm = wasm_strip(wasm)
	wasm = wasm_opt(wasm)
	os.system('ls -lh /tmp/*.wasm')

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/rustapi.js'
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
	if out is None:
		out = '%s.html' % name
	open(out,'w').write('\n'.join(o))
	if preview:
		webbrowser.open(out)


NO_STD='''
#![no_std]
#[panic_handler]
fn handle_panic(_: &core::panic::PanicInfo) -> ! {
	loop {}
}

extern "C"{
	fn js_alert(s:*const u8, n:i32);
}

#[no_mangle]
pub fn add_one(x: i32) -> i32 {
	x + 1
}

#[no_mangle]
pub fn main() {
	unsafe{
		js_alert("hello world".as_ptr(), 11);
	}
}
'''

## https://cliffle.com/blog/bare-metal-wasm/
## https://rustwasm.github.io/book/reference/code-size.html
# "Rust's default allocator for WebAssembly is a port of dlmalloc to Rust. It weighs in somewhere around ten kilobytes."
## https://stackoverflow.com/questions/49203561/how-do-i-convert-a-str-to-a-const-u8
## https://doc.rust-lang.org/std/ffi/struct.CString.html
## https://dzfrias.dev/blog/rust-wasm-minimal-setup/
## https://blog.jfo.click/calling-a-c-function-from-rust/
## https://users.rust-lang.org/t/minimal-webassembly-without-std/18070

try:
	import bpy
except:
	bpy = None


if __name__=='__main__':
	if bpy:
		pass
	elif '--simple-test' in sys.argv:
		build(NO_STD)
		os.system('ls -lh /tmp/*.wasm')
		sys.exit()
	else:
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

assert bpy
import math, mathutils
from random import random, uniform, choice

@bpy.utils.register_class
class RustExportWebGL(bpy.types.Operator):
	bl_idname = "rust.export_3d"
	bl_label = "Rust Export WASM (WebGL)"
	@classmethod
	def poll(cls, context):
		return True
	def execute(self, context):
		build_webgl(context.world)
		return {"FINISHED"}

@bpy.utils.register_class
class RustWorldPanel(bpy.types.Panel):
	bl_idname = "WORLD_PT_RustWorld_Panel"
	bl_label = "Rust Export"
	bl_space_type = "PROPERTIES"
	bl_region_type = "WINDOW"
	bl_context = "world"

	def draw(self, context):
		self.layout.operator("rust.export_3d", icon="CONSOLE")

RUST_HEADER = '''
#![no_std]
#![feature(f16)]
#[panic_handler]
fn handle_panic(_: &core::panic::PanicInfo) -> ! {
	loop {}
}
'''

RUST_EXTERN = '''
extern "C"{
	fn js_alert(s:*const u8, n:i32);

	fn gl_init(w:i32, h:i32);
	fn gl_new_buffer() ->i32;
	fn gl_bind_buffer(idx:i32 );
	fn gl_bind_buffer_element(idx:i32);
	fn gl_buffer_f16(idx:i32, sz:i32, ptr : *const f16 );
	fn gl_buffer_element(idx:i32, sz:i32, ptr : *const u16 );

	fn gl_new_program() -> i32;
	fn gl_link_program(prog:i32);


	fn gl_attach_vshader(prog:i32, s:i32);
	fn gl_attach_fshader(prog:i32, s:i32);
	fn gl_new_vshader(c:*const u8) ->i32;
	fn gl_new_fshader(c:*const u8) ->i32;

	fn gl_get_uniform_location(a:i32, ptr:*const u8) ->i32;
	fn gl_get_attr_location(a:i32, ptr:*const u8) ->i32;

	fn gl_enable_vertex_attr_array(loc:i32);
	fn gl_vertex_attr_pointer(loc:i32, n:i32);

	fn gl_use_program(prog:i32);

	fn gl_draw_tris_tint(len:i32, r:f32, g:f32, b:f32);
	fn gl_uniform_mat4fv(loc:i32, mat:*const f32);

	fn gl_trans(matid:i32, x:f32, y:f32, z:f32);
	fn gl_trans_upload(vid:i32);

	fn js_rand() ->f32;
	fn js_sin(a:f32) ->f32;
	fn js_cos(a:f32) ->f32;

	//fn js_set_entry(ptr: unsafe extern "C" fn());


}


'''

RUST_SHADER_VARS = '''
static mut vs : i32 = 0;
static mut fs : i32 = 0;
static mut prog : i32 = 0;
static mut ploc : i32 = 0;
static mut vloc : i32 = 0;
static mut mloc : i32 = 0;
static mut posloc : i32 = 0;
'''

#https://internals.rust-lang.org/t/convenient-null-terminated-string-literals/14267
RUST_SHADER_SETUP = r'''
	vs = gl_new_vshader(VERTEX_SHADER.as_ptr());
	fs = gl_new_fshader(FRAGMENT_SHADER.as_ptr());

	prog = gl_new_program();
	gl_attach_vshader(prog, vs);
	gl_attach_fshader(prog, fs);
	gl_link_program( prog );

	ploc = gl_get_uniform_location(prog, "P\0".as_ptr());  // projection Pmat
	vloc = gl_get_uniform_location(prog, "V\0".as_ptr());  // view matrix
	mloc = gl_get_uniform_location(prog, "M\0".as_ptr());  // model matrix

	posloc = gl_get_attr_location(prog, "vp\0".as_ptr());  // vertex position

'''

## https://doc.rust-lang.org/reference/tokens.html#c-string-literals
def gen_shaders():
	assert '"' not in VSHADER
	assert '"' not in FSHADER

	o = [
		#'const VERTEX_SHADER:&str =r###"',
		#'const VERTEX_SHADER:&str = c"',
		'const VERTEX_SHADER:&str = "',
	]
	for ln in VSHADER.splitlines():
		ln = ln.strip()
		if not ln: continue
		if ln.startswith('//'): continue
		o.append(ln)
	#o.append(r'\0"###;')
	o.append('\0x00";')
	o.append('const FRAGMENT_SHADER:&str = "')
	for ln in FSHADER.splitlines():
		ln = ln.strip()
		if not ln: continue
		if ln.startswith('//'): continue
		o.append(ln)
	o.append('\0x00";')
	return '\n'.join(o)

DEBUG_CAMERA = '''
static mut proj_matrix : [f32;16] = [1.8106600046157837, 0.0, 0.0, 0.0, 0.0, 2.4142134189605713, 0.0, 0.0, 0.0, 0.0, -1.0202020406723022, -1.0, 0.0, 0.0, -2.0202019214630127, 0.0];
static mut view_matrix : [f32;16] = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -5.0, 1.0];
'''

#pub fn rotateY(mut m:[f32;16], angle:f32) {
#pub fn rotateY(m:&[f32;16], angle:f32) {

## help: consider using `wrapping_add` or `add` for indexing into raw pointer
#pub fn rotateY(m:*const f32, angle:f32) {

RUST_HELPER_FUNCS = '''
pub fn rotateY(m:*const f32, angle:f32) {
	unsafe{
		let c:f32 = js_cos(angle);
		let s:f32 = js_sin(angle);	

		let mv0:f32 = m[0];
		let mv4:f32 = m[4];
		let mv8:f32 = m[8];

		m[0] = c*m[0]+s*m[2];
		m[4] = c*m[4]+s*m[6];
		m[8] = c*m[8]+s*m[10];

		m[2] = c*m[2]-s*mv0;
		m[6] = c*m[6]-s*mv4;
		m[10] = c*m[10]-s*mv8;

	}
}

'''


RUST_HELPER_FUNCS = '''
pub fn rotateY(m:*mut f32, angle:f32) {
	unsafe{
		let c:f32 = js_cos(angle);
		let s:f32 = js_sin(angle);	

		let mv0:f32 = *m.wrapping_add(0);
		let mv4:f32 = *m.wrapping_add(4);
		let mv8:f32 = *m.wrapping_add(8);

		*m.wrapping_add(0) = c * (*m.wrapping_add(0)) + s * (*m.wrapping_add(2));
		*m.wrapping_add(4) = c * (*m.wrapping_add(4)) + s * (*m.wrapping_add(6));
		*m.wrapping_add(8) = c * (*m.wrapping_add(8)) + s * (*m.wrapping_add(10));

		*m.wrapping_add(2)  = c * (*m.wrapping_add(2)) - s * mv0;
		*m.wrapping_add(6)  = c * (*m.wrapping_add(6)) - s * mv4;
		*m.wrapping_add(10) = c * (*m.wrapping_add(10)) - s * mv8;

	}
}

'''


def blender_to_rust(world):
	header = [
		RUST_HEADER, 
		RUST_EXTERN,
		RUST_SHADER_VARS,
		gen_shaders(),
		DEBUG_CAMERA,
		RUST_HELPER_FUNCS,
	]
	data = []
	setup = []
	draw = []

	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		sname = safename(ob)
		if ob.type=='MESH':
			if not ob.data.materials: continue

			if '--disable-sym' in sys.argv:
				is_symmetric = False
			else:
				is_symmetric = is_mesh_sym(ob)
				if is_symmetric:
					bpy.context.view_layer.objects.active = ob
					ob.select_set(True)
					bpy.ops.object.mode_set(mode="EDIT")
					bpy.ops.object.automirror()
					bpy.ops.object.mode_set(mode="OBJECT")
					ob.modifiers[0].use_mirror_merge=False

			a,b,c = mesh_to_rust(ob, mirror=is_symmetric)
			data  += a
			setup += b
			draw  += c

	update = [
		'#[no_mangle]',
		'pub fn update() {',
		#'extern "C" fn update(){',
		'	unsafe{',
		'	gl_uniform_mat4fv(ploc, proj_matrix.as_ptr());',
		'	gl_uniform_mat4fv(vloc, view_matrix.as_ptr());',

	] + draw + [
		'	}',
		'}',
	]

	main = [
		'#[no_mangle]',
		'pub fn main() {',
		'	unsafe{',
		'	gl_init(800, 600);',
		#'	view_matrix[14] = view_matrix[14] - 3.0;',

		RUST_SHADER_SETUP,

	] + ['\t'+ln for ln in setup] + [
		'	gl_use_program(prog);',
		#'	js_set_entry(update);',  # expected "C" fn, found "Rust" fn
		'	}',
		'}'
	]

	return header + data + update + main

def mesh_to_rust(ob, mirror=False):
	if mirror: mirror = 1
	else: mirror = 0
	name = safename(ob.data)
	sname = name.upper()
	data = []
	setup = []
	draw = []

	verts = []
	for v in ob.data.vertices:
		verts.append(str(v.co.x))
		verts.append(str(v.co.y))
		verts.append(str(v.co.z))


	data = [
		'const VERTS_%s : [f16;%s] = [%s];' %(sname,len(verts), ','.join(verts)),  ## 16bit float verts
	]


	indices_by_mat = {}
	for p in ob.data.polygons:
		if p.material_index not in indices_by_mat:
			indices_by_mat[p.material_index] = {'num':0, 'indices':[]}

		if len(p.vertices)==4:
			x,y,z,w = p.vertices
			indices_by_mat[p.material_index]['indices'].append((x,y,z,w))
			indices_by_mat[p.material_index]['num'] += 6
		elif len(p.vertices)==3:
			x,y,z = p.vertices
			w = 65000
			indices_by_mat[p.material_index]['indices'].append((x,y,z,w))
			indices_by_mat[p.material_index]['num'] += 3
		else:
			raise RuntimeError('TODO polygon len verts: %s' % len(p.vertices))

	for midx in indices_by_mat:
		mi = [str(v).replace('(','').replace(')','').replace(' ', '') for v in indices_by_mat[midx]['indices']]
		data += [
			'const INDICES_%s_%s : [u16;%s] = [%s];' %(sname, midx, len(mi)*4, ', '.join(mi)),
			'static mut %s_%s_ibuff : i32 = 0;' % (name,midx),
		]

	mat = []
	for vec in ob.matrix_local:
		mat += [str(v) for v in vec]


	data += [
		'static mut %s_vbuff : i32 = 0;' % name,
		'static mut %s_mat : [f32;16] = [%s];' %(name,','.join(mat)),
	]


	setup = [
		'%s_vbuff = gl_new_buffer();' % name,
		'gl_bind_buffer(%s_vbuff);' % name,
		# note: 'core::convert::TryInto' is included in the prelude starting in Edition 2021
		#'gl_buffer_f16(%s, VERTS_%s.len().try_into().unwrap(), VERTS_%s.as_ptr());' %(mirror, sname,sname),
		'gl_buffer_f16(%s, VERTS_%s.len() as i32, VERTS_%s.as_ptr());' %(mirror, sname,sname),


		'gl_vertex_attr_pointer(posloc, 3);',
		'gl_enable_vertex_attr_array(posloc);',
	]

	for midx in indices_by_mat:
		setup += [
			'%s_%s_ibuff = gl_new_buffer();' % (name,midx),
			'gl_bind_buffer_element(%s_%s_ibuff);' % (name,midx),
			'gl_buffer_element(%s, INDICES_%s_%s.len() as i32, INDICES_%s_%s.as_ptr());' %(mirror, sname,midx, sname,midx),
		]

	draw += [
		'gl_bind_buffer(%s_vbuff);' % name,
		'gl_uniform_mat4fv(mloc, %s_mat.as_ptr());' % name,  ## update object matrix uniform
	]


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
				'let mut needs_upload=false;'
			]

			data += [
				'static mut eyes_x:f32=0.0;'
				'static mut eyes_y:f32=0.0;'

			]
			needs_upload = True
			break


	for midx in indices_by_mat:
		mat = ob.data.materials[midx]
		if mat.zigzag_object_type != "NONE":
			if mat.zigzag_object_type=="LOWER_LIP":
				draw += [
					'if(js_rand() < 0.06){',
					'	gl_trans(%s_%s_ibuff,0.0,0.0, (js_rand()-0.25)*0.1);' % (name,midx),
					'	needs_upload=true;',
					'}',
				]
			elif mat.zigzag_object_type=="EYES":
				draw += [
					'if(js_rand() < 0.03){',
					'	eyes_x=(js_rand()-0.5)*0.05;',
					'	eyes_y=(js_rand()-0.5)*0.01;',
					#'	rotateY(%s_mat.as_mut_ptr(), eyes_x*2.0);' %name,
					'	gl_trans(%s_%s_ibuff, eyes_x, 0.0, eyes_y);' % (name,midx),
					'	needs_upload=true;',
				]
				if lower_eyelid is not None:
					draw += [
					'	gl_trans(%s_%s_ibuff, eyes_x*0.25, -0.025, (eyes_y*0.4)+( (js_rand()-0.35)*0.07));' % (name,lower_eyelid),
					]

				draw.append('}')

			elif mat.zigzag_object_type=="UPPER_EYELID":
				draw += [
					'if(js_rand() < 0.06 || needs_upload){',
					'	gl_trans(%s_%s_ibuff, eyes_x*0.2, -0.05, ((js_rand()-0.7)*0.07)+(eyes_y*0.2));' % (name,midx),
					'	needs_upload=true;',
					'}',
				]


		if needs_upload:
			draw.append(
				'if(needs_upload) { gl_trans_upload(%s_vbuff); }' % name
			)


	for midx in indices_by_mat:
		num = indices_by_mat[midx]['num']
		draw.append('gl_bind_buffer_element(%s_%s_ibuff);' % (name,midx))
		mat = ob.data.materials[midx]
		r,g,b,a = mat.diffuse_color
		if mirror:
			draw.append('gl_draw_tris_tint( %s, %s,%s,%s );' % (num*2,r,g,b))
		else:
			draw.append('gl_draw_tris_tint( %s, %s,%s,%s );' % (num,r,g,b))


	return data, setup, draw


def build_webgl(world, name='rust_test', preview=True, out=None):
	rs = blender_to_rust(world)
	build(rs, name=name, preview=preview, out=None)

if __name__=='__main__':
	for arg in sys.argv:
		if arg.startswith('--test='):
			import libtestzag
			tname = arg.split('=')[-1]
			getattr(libtestzag, tname)()
			build_webgl(bpy.data.worlds[0], name='rust_'+tname, preview=False)
			sys.exit()

		elif arg.startswith('--import='):
			exec( open( arg.split('=')[-1] ).read() )

	for arg in sys.argv:
		if arg.startswith('--export='):
			path = arg.split('=')[-1]
			build_webgl(bpy.data.worlds[0], out=path)
			print('saved:', path)

	if '--test-wasm' in sys.argv:
		bpy.data.objects['Cube'].hide_set(True)
		ob = libgenzag.monkey()
		build_webgl(bpy.data.worlds[0])
