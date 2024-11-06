#!/usr/bin/env python3
import os, sys, subprocess, base64, webbrowser
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
import zigzag, libwebzag, libgenzag
from zigzag import GZIP, BLENDER, VSHADER, FSHADER, safename

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

def build(rs, jsapi=None):
	if not jsapi:
		jsapi=libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(
			zigzag.ZIG_ZAG_INIT + JS_ALERT
		)

	name = 'test_rust'
	tmp = '/tmp/%s.rs' % name
	wasm = '/tmp/%s.wasm' % name
	if type(rs) is list:
		open(tmp, 'w').write('\n'.join(rs))
	else:
		open(tmp, 'w').write(rs)
	cmd = [
		'rustc', '--target', 'wasm32-unknown-unknown',
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

	out = 'rustzag-preview.html'
	open(out,'w').write('\n'.join(o))
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
	fn gl_uniform_mat4fv(loc:i32, mat:*mut f32);

	fn gl_trans(matid:i32, x:f32, y:f32, z:f32);
	fn gl_trans_upload(vid:i32);

	fn js_rand() ->f32;
	fn js_sin(a:f32) ->f32;
	fn js_cos(a:f32) ->f32;

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

def gen_shaders():
	o = [
		'const VERTEX_SHADER:&str =r###"',
	]
	for ln in VSHADER.splitlines():
		ln = ln.strip()
		if not ln: continue
		if ln.startswith('//'): continue
		o.append(ln)
	o.append(r'\0"###;')
	o.append('const FRAGMENT_SHADER:&str = r###"')
	for ln in FSHADER.splitlines():
		ln = ln.strip()
		if not ln: continue
		if ln.startswith('//'): continue
		o.append(ln)
	o.append(r'\0"###;')
	return '\n'.join(o)

def blender_to_rust(world):
	header = [
		RUST_HEADER, 
		RUST_EXTERN,
		RUST_SHADER_VARS,
		gen_shaders(),
	]
	data = []
	setup = []
	draw = []

	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		sname = safename(ob)
		if ob.type=='MESH':
			if not ob.data.materials: continue
			a,b,c = mesh_to_rust(ob)
			data  += a
			setup += b
			draw  += c

	update = [
		'#[no_mangle]',
		'pub fn update() {',
		'	unsafe{',
	] + draw + [
		'	}',
		'}',
	]

	main = [
		'#[no_mangle]',
		'pub fn main() {',

		'	unsafe{',

		'	gl_init(800, 600);',
		#'	prog = gl_new_program();',
		RUST_SHADER_SETUP,

	] + ['\t'+ln for ln in setup] + [
		'	gl_use_program(prog);',
		#'	js_set_entry(&update);',
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

	return data, setup, draw


def build_webgl(world):
	rs = blender_to_rust(world)
	build(rs)

if __name__=='__main__':
	bpy.data.objects['Cube'].hide_set(True)
	ob = libgenzag.monkey()
	ob.rotation_euler.x = -math.pi/2
	bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
	build_webgl(bpy.data.worlds[0])
