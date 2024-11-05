#!/usr/bin/python3
import os, sys, subprocess, base64, webbrowser, zipfile
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.append(_thisdir)
import libwebzag
import libgenzag

GZIP = 'gzip'

zigzip=zigxz=None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	if not os.path.isfile(BLENDER):
		BLENDER = 'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe'

	zigzip = 'https://ziglang.org/download/0.13.0/zig-windows-x86_64-0.13.0.zip'
	ZIG = os.path.join(_thisdir, 'zig-windows-x86_64-0.13.0/zig.exe')
	GZIP = os.path.abspath(os.path.join(_thisdir,'gzip.exe'))
	if not os.path.isdir('/tmp'): os.mkdir('/tmp')
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	zigxz = 'https://ziglang.org/download/0.13.0/zig-macos-aarch64-0.13.0.tar.xz'
	ZIG = os.path.join(_thisdir, 'zig-macos-aarch64-0.13.0/zig')
else:
	BLENDER = 'blender'
	zigxz = 'https://ziglang.org/download/0.13.0/zig-linux-x86_64-0.13.0.tar.xz'
	ZIG = os.path.join(_thisdir, 'zig-linux-x86_64-0.13.0/zig')

if __name__=='__main__':
	if not os.path.isfile(ZIG):
		if sys.platform=='win32':
			if not os.path.isfile('zig-windows-x86_64-0.13.0.zip'):
				cmd = 'curl -L -o zig-windows-x86_64-0.13.0.zip %s' % zigzip
				print(cmd)
				subprocess.check_call(cmd)
			with zipfile.ZipFile('zig-windows-x86_64-0.13.0.zip', 'r') as zip_ref:
				zip_ref.extractall(_thisdir)

		elif sys.platform=='darwin':
			if not os.path.isfile('zig-macos-aarch64-0.13.0.tar.xz'):
				cmd = 'curl -L -o zig-macos-aarch64-0.13.0.tar.xz %s' % zigxz
				print(cmd)
				subprocess.check_call(cmd)
			cmd = 'tar -xvf zig-macos-aarch64-0.13.0.tar.xz'
			print(cmd)
			subprocess.check_call(cmd.split())

		else:
			if not os.path.isfile('zig-linux-x86_64-0.13.0.tar.xz'):
				cmd = 'wget -c %s' % zigxz
				print(cmd)
				subprocess.check_call(cmd.split())
			cmd = 'tar -xvf zig-linux-x86_64-0.13.0.tar.xz'
			print(cmd)
			subprocess.check_call(cmd.split())

	ZIG_VER = subprocess.check_output([ZIG, 'version']).decode('utf-8')
	print('zig version:', ZIG_VER)


TEST = r'''
const std = @import("std");
pub fn main() !void {
	std.debug.print("Hello, World!\n", .{});
}
'''

def test_native():
	tmp = '/tmp/test-zig.zig'
	open(tmp, 'w').write(TEST)
	cmd = [ZIG, 'build-exe', tmp]
	print(cmd)
	subprocess.check_call(cmd, cwd='/tmp')
	cmd = ['/tmp/test-zig']
	print(cmd)
	subprocess.check_call(cmd)

TEST_WASM = r'''
extern fn foo() void;
pub fn main() !void {
	foo();
}
'''

## https://www.reddit.com/r/Zig/comments/1eony2f/wasm_build_size_is_huge/
def test_wasm( freestanding=True):
	cmd = [ZIG, 'build-exe']
	target = 'wasm32-wasi'
	tmp = '/tmp/test-wasm-zig.zig'
	if freestanding:
		target = 'wasm32-freestanding-musl'
		tmp = '/tmp/test-wasm-freestanding-zig.zig'

	open(tmp, 'w').write(TEST_WASM)
	cmd += [ '-O', 'ReleaseSmall', '-target', target,  tmp]
	print(cmd)
	subprocess.check_call(cmd, cwd='/tmp')
	if sys.platform!='win32':
		os.system('ls -l /tmp/*.wasm')



JS_API_RESET = '''
	reset(wasm,id,bytes){
		this.elts=[];
		this.wasm=wasm;
		this.bytes=new Uint8Array(bytes);
		this.canvas=document.getElementById(id);
		this.ctx=this.canvas.getContext('2d');
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

JS_API = libwebzag.JS_API_HEADER + 'class api {' + libwebzag.JS_API_PROXY + JS_API_RESET + '''

	rect(x,y,w,h, r,g,b,a){
		this.ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
		this.ctx.fillRect(x,y,w,h)
	}
	js_set_entry(f){
		this.entryFunction=this.wasm.instance.exports.__indirect_function_table.get(f)
	}

	html_canvas_resize(w,h){
		this.canvas.width=w;
		this.canvas.height=h
	}
	html_canvas_clear(){
		this.ctx.clearRect(0,0,this.canvas.width,this.canvas.height)
	}


	html_new_text(ptr,r,g,b,h,id){
		var e=document.createElement('pre');
		e.style='position:absolute;left:'+r+';top:'+g+';font-size:'+b;
		e.hidden=h;
		e.id=cstr_by_ptr(this.wasm.instance.exports.memory.buffer,id);
		document.body.append(e);
		e.append(cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr));
		return this.elts.push(e)-1
	}

	random(){
		return Math.random()
	}
	html_set_text(idx,ptr){
		this.elts[idx].firstChild.nodeValue=cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr)
	}
	html_set_hide(idx,f){
		this.elts[idx].hidden=f
	}

	html_draw_lines(ptr,l,t,fill,r,g,b,a){
		const buf=this.wasm.instance.exports.memory.buffer;
		const p=new Float32Array(buf,ptr,l);
		this.ctx.strokeStyle='black';
		if(fill)this.ctx.fillStyle='rgba('+r+','+g+','+b+','+a+')';
		this.ctx.lineWidth=t;
		this.ctx.beginPath();
		this.ctx.moveTo(p[0],p[1]);
		for(var i=2;i<p.length;i+=2)this.ctx.lineTo(p[i],p[i+1]);
		if(fill){
			this.ctx.closePath();
			this.ctx.fill()
		}
		this.ctx.stroke()
	}

}

new api();
'''




TEST_WASM_CANVAS = r'''
extern fn rect(x:c_int,y:c_int, w:c_int,h:c_int, r:u8,g:u8,b:u8, alpha:f32 ) void;

export fn main() void {
	for (0..8) |y| {
		for (0..8) |x| {
			rect( @intCast(x*64),@intCast(y*64), 32,32, 200,0,0, 1.0);
		}
	}
}
'''

def wasm_opt(wasm):
	o = wasm.replace('.wasm', '.opt.wasm')
	cmd = ['wasm-opt', '-o',o, '-Oz', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	return o


def build(zig, memsize=4, jsapi=JS_API):
	name = 'test-zig'
	tmp = '/tmp/%s.zig' % name
	if type(zig) is list:
		open(tmp, 'w').write('\n'.join(zig))
	else:
		open(tmp, 'w').write(zig)
	cmd = [
		ZIG, 'build-exe', 
		'-O', 'ReleaseSmall', 
		'-target', 'wasm32-freestanding-musl',
		'-fno-entry',
		'--export-table', '-rdynamic',
		'--initial-memory=%s' % (1024*1024*memsize),
		tmp
	]
	print(cmd)
	subprocess.check_call(cmd, cwd='/tmp')

	os.system('ls -l /tmp/*.wasm')

	wasm = '/tmp/%s.wasm' % name
	if sys.platform!='win32':
		wasm = wasm_opt(wasm)

	cmd = [GZIP, '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/zigapi.js'
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

	out = 'zigzag-preview.html'
	open(out,'w').write('\n'.join(o))
	webbrowser.open(out)

	if sys.platform!='win32':
		cmd = ['zip', '-9', 'zigzag-preview.zip', 'zigzag-preview.html']
		print(cmd)
		subprocess.check_call(cmd)
		os.system('ls -l zigzag-preview.*')
		os.system('ls -l /tmp/*.wasm')


try:
	import bpy
except:
	bpy = None


if __name__=='__main__':
	if '--help' in sys.argv:
		subprocess.check_call([ZIG, '--help'])
		subprocess.check_call([ZIG, 'build-exe', '--help'])
		targets = subprocess.check_output([ZIG, 'targets']).decode('utf-8')
		for ln in targets.splitlines():
			if 'wasm' in ln:
				print(ln)
			if 'freestanding' in ln:
				print(ln)
		sys.exit()

	elif '--test-native' in sys.argv:
		test_native()
		sys.exit()
	elif '--test-wasm' in sys.argv:
		test_wasm()
		sys.exit()
	elif '--test-wasm-canvas' in sys.argv:
		build(TEST_WASM_CANVAS)
		sys.exit()
	elif bpy:
		pass
	elif (sys.platform in ('win32','darwin') and os.path.isfile(BLENDER)) or sys.platform=='linux':
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
		print("WARN: blender not found")
		print("blender versions supported: 3.6 and 4.2")
		test_wasm()
		sys.exit()

## in blender ##
if bpy:
	import math, mathutils
	from random import random, uniform, choice

MAX_SCRIPTS_PER_OBJECT = 8

def register():
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		setattr(
			bpy.types.Object,
			"zig_script" + str(i),
			bpy.props.PointerProperty(name="script%s" % i, type=bpy.types.Text),
		)
		setattr(
			bpy.types.Object,
			"zig_script%s_disable" %i,
			bpy.props.BoolProperty(name="disable"),
		)

	bpy.types.Object.zig_hide = bpy.props.BoolProperty( name="hidden on spawn")


	@bpy.utils.register_class
	class ZigObjectPanel(bpy.types.Panel):
		bl_idname = "OBJECT_PT_Zig_Object_Panel"
		bl_label = "Zig Object Options"
		bl_space_type = "PROPERTIES"
		bl_region_type = "WINDOW"
		bl_context = "object"

		def draw(self, context):
			if not context.active_object: return
			ob = context.active_object

			self.layout.label(text="Attach Zig Scripts")
			foundUnassignedScript = False
			for i in range(MAX_SCRIPTS_PER_OBJECT):
				hasProperty = (
					getattr(ob, "zig_script" + str(i)) != None
				)
				if hasProperty or not foundUnassignedScript:
					row = self.layout.row()
					row.prop(ob, "zig_script" + str(i))
					row.prop(ob, "zig_script%s_disable"%i)
				if not foundUnassignedScript:
					foundUnassignedScript = not hasProperty



	@bpy.utils.register_class
	class ZigExport(bpy.types.Operator):
		bl_idname = "zig.export_2d"
		bl_label = "Zig Export WASM (Canvas 2D)"
		@classmethod
		def poll(cls, context):
			return True
		def execute(self, context):
			build_wasm(context.world)
			return {"FINISHED"}

	@bpy.utils.register_class
	class ZigExportWebGL(bpy.types.Operator):
		bl_idname = "zig.export_3d"
		bl_label = "Zig Export WASM (WebGL)"
		@classmethod
		def poll(cls, context):
			return True
		def execute(self, context):
			build_webgl(context.world)
			return {"FINISHED"}


	@bpy.utils.register_class
	class ZigWorldPanel(bpy.types.Panel):
		bl_idname = "WORLD_PT_ZigWorld_Panel"
		bl_label = "Zig Export"
		bl_space_type = "PROPERTIES"
		bl_region_type = "WINDOW"
		bl_context = "world"

		def draw(self, context):
			self.layout.operator("zig.export_2d", icon="CONSOLE")
			self.layout.operator("zig.export_3d", icon="CONSOLE")


def safename(ob):
	return ob.name.lower().replace('.', '_')

def get_scripts(ob):
	scripts = []
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "zig_script%s_disable" %i): continue
		txt = getattr(ob, "zig_script" + str(i))
		if txt: scripts.append(txt)
	return scripts

def has_scripts(ob):
	for i in range(MAX_SCRIPTS_PER_OBJECT):
		if getattr(ob, "zig_script%s_disable" %i): continue
		txt = getattr(ob, "zig_script" + str(i))
		if txt: return True
	return False

def calc_stroke_width(stroke):
	sw = 0.0
	for p in stroke.points:
		sw += p.pressure
		#sw += p.strength
	sw /= len(stroke.points)
	return sw * stroke.line_width * 0.05

ZIG_HEADER_WEBGL = '''
const EntryFunc = *const fn() callconv(.C) void;
extern fn js_set_entry(ptr:EntryFunc) void;

extern fn random() f32;
extern fn gl_init(w:c_int, h:c_int) void;

'''

ZIG_HEADER = '''
extern fn rect(x:c_int,y:c_int, w:c_int,h:c_int, r:u8,g:u8,b:u8, alpha:f32 ) void;
extern fn html_canvas_resize(x:c_int, y:c_int) void;
extern fn html_canvas_clear() void;


extern fn html_new_text(ptr: [*:0]const u8, x:f32,y:f32, sz:f32, hidden:u8, id: [*:0]const u8) u16;
extern fn html_set_text(id:u16, ptr: [*:0]const u8) void;
extern fn html_set_hide(id:u16, flag:u8) void;

//extern fn html_draw_lines (ptr: [*c]Vec2D, len:u16, thick:f32, use_fill:u8, r:u8,g:u8,b:u8, a:f32) void;
//extern fn test_draw_lines (ptr: [*]Vec2D ) void;
//extern fn test_draw_lines (ptr: [*]const f32 ) void;
extern fn html_draw_lines (ptr: [*]const f32, len:u16, thick:f32, use_fill:u8, r:u8,g:u8,b:u8, a:f32) void;


extern fn random() f32;

const EntryFunc = *const fn() callconv(.C) void;
extern fn js_set_entry(ptr:EntryFunc) void;

//const Vec2D = extern struct {
const Vec2D = struct {
	x: f32,
	y: f32,
};

const Color = struct {
	r: u8,
	g: u8,
	b: u8,
	a: f32,
};

const Object2D = struct {
	pos: Vec2D,
	scl: Vec2D,
	clr: Color,
	id : u16,
};

'''

SCALE = 100

def grease_to_zig(ob, datas, head, draw, setup, scripts, obj_index):
	sx,sy,sz = ob.scale * SCALE
	x,y,z = ob.location # * SCALE

	dname = safename(ob.data)

	if dname not in datas:
		datas[dname]={'orig-points':0, 'total-points':0, 'draw':[]}
		data = []
		for lidx, layer in enumerate( ob.data.layers ):
			for sidx, stroke in enumerate( layer.frames[0].strokes ):
				datas[dname]['orig-points'] += len(stroke.points)
				mat = ob.data.materials[stroke.material_index]
				use_fill = 0
				if mat.grease_pencil.show_fill: use_fill = 1
				points = stroke.points
				s = []
				for pnt in points:
					x1,y1,z1 = pnt.co * SCALE
					#x1 += 100
					z1 += z
					x1 += x
					#s.append('.{%s,%s}' % (x1,-z1))
					s.append('%s' % (x1))
					s.append('%s' % (-z1))

				## zig error: does not support array initialization syntax
				#data.append('const __%s__%s_%s : [%s]Vec2D = .{%s};' % (dname, lidx, sidx, len(points), ','.join(s) ))
				n = len(s)
				data.append('const __%s__%s_%s : [%s]f32 = .{%s};' % (dname, lidx, sidx, n, ','.join(s) ))

				r,g,b,a = mat.grease_pencil.fill_color
				swidth = calc_stroke_width(stroke)
				datas[dname]['draw'].append({'layer':lidx, 'index':sidx, 'length':n, 'width':swidth, 'fill':use_fill, 'color':[r,g,b,a]})

		head += data


	for a in datas[dname]['draw']:
		r,g,b,alpha = a['color']
		r = int(r*255)
		g = int(g*255)
		b = int(b*255)
		#draw.append('	test_draw_lines(&__%s__%s_%s);' % (dname, a['layer'], a['index']))
		draw.append('	html_draw_lines(&__%s__%s_%s, %s, %s, %s, %s,%s,%s,%s);' % (dname, a['layer'], a['index'], a['length'], a['width'], a['fill'], r,g,b,alpha))



def blender_to_zig(world, init_data_in_groups=True):
	head = [ZIG_HEADER]
	setup = [
		'export fn main() void {',
		'	html_canvas_resize(%s, %s);' % (800,600),
		'	js_set_entry(&game_frame);',


	]

	setup_pos = []
	setup_scl = []
	setup_clr = []

	datas = {}

	draw_header = [
		'export fn game_frame() void {',
		#'	var self:Object2D = undefined;',  ## only added when needed
		'	html_canvas_clear();',

	]
	draw = []

	meshes = []
	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		sname = safename(ob)
		idx = len(meshes)
		if ob.type=='GPENCIL':
			if has_scripts(ob):
				setup.append('	objects[%s].position={%s,%s};' % (idx, x,z))
				sx,sy,sz = ob.scale
				setup.append('	objects[%s].scale={%s,%s};' % (idx, sx,sz))

			scripts = []
			grease_to_zig(ob, datas, head, draw, setup, scripts, idx)

		elif ob.type=='FONT':
			meshes.append(ob)
			x,y,z = ob.location
			z = int(-z)
			x = int(x)
			if init_data_in_groups:
				setup_pos.append('objects[%s].pos=Vec2D{.x=%s,.y=%s};' % (idx,x,z))
			else:
				setup.append('objects[%s].pos=Vec2D{.x=%s,.y=%s};' % (idx,x,z))

			cscale = ob.data.size*SCALE
			hide = 0
			if ob.zig_hide:
				hide = 1
			dom_name = ob.name
			if dom_name.startswith('_'):
				dom_name = ''

			setup += [
				'	objects[%s].id = html_new_text("%s", %s,%s, %s, %s, "%s");' % (idx, ob.data.body, x,z, cscale, hide, dom_name),

			]

			if has_scripts(ob):
				draw.append('	self = objects[%s];' % idx)

				props = {}
				for prop in ob.keys():
					if prop.startswith( ('_', 'zig_', 'c3_') ): continue
					val = ob[prop]
					if type(val) is str:
						#head.append('const %s_%s : [*:0]const u8 = "%s";' %(prop,sname, val))  ## in c3 const was smaller, in zig var is smaller?
						head.append('var %s_%s : [*:0]const u8 = "%s";' %(prop,sname, val))
					else:
						head.append('var %s_%s : f32 = %s;' %(prop,sname, val))
					props[prop] = ob[prop]


				for txt in get_scripts(ob):
					s = txt.as_string()
					for prop in props:
						if 'self.'+prop in s:
							s = s.replace('self.'+prop, '%s_%s'%(prop,sname))
					draw.append( s )



		elif ob.type=='MESH':
			if len(ob.data.vertices)==4: ## assume plane
				meshes.append(ob)
				x,y,z = ob.location
				z = int(-z)
				x = int(x)

				sx,sy,sz = ob.scale
				w = int(sx*2)
				h = int(sy*2)

				r,g,b,a = ob.color
				r = int(r*255)
				g = int(g*255)
				b = int(b*255)


				if init_data_in_groups:
					setup_pos.append('objects[%s].pos=Vec2D{.x=%s,.y=%s};' % (idx,x,z))
					setup_scl.append('objects[%s].scl=Vec2D{.x=%s,.y=%s};' % (idx,w,h))
					setup_clr.append('objects[%s].clr=Color{.r=%s,.g=%s,.b=%s,.a=%s};' % (idx,r,g,b,a))
				else:
					setup += [
						'objects[%s].pos=Vec2D{.x=%s,.y=%s};' % (idx,x,z),
						'objects[%s].scl=Vec2D{.x=%s,.y=%s};' % (idx,w,h),
						'objects[%s].clr=Color{.r=%s,.g=%s,.b=%s,.a=%s};' % (idx,r,g,b,a),
					]


				if has_scripts(ob):
					draw.append('	self = objects[%s];' % idx)

					props = {}
					for prop in ob.keys():
						if prop.startswith( ('_', 'zig_', 'c3_') ): continue
						val = ob[prop]
						if type(val) is str:
							head.append('var %s_%s : [*:0]const u8 = "%s";' %(prop,sname, val))
						else:
							head.append('var %s_%s : f32 = %s;' %(prop,sname, val))
						props[prop] = ob[prop]


					for txt in get_scripts(ob):
						s = txt.as_string()
						for prop in props:
							if 'self.'+prop in s:
								s = s.replace('self.'+prop, '%s_%s'%(prop,sname))
						draw.append( s )

					draw += [
						'	rect(@intFromFloat(self.pos.x), @intFromFloat(self.pos.y), @intFromFloat(self.scl.x), @intFromFloat(self.scl.y), self.clr.r, self.clr.g, self.clr.b, self.clr.a);',
						'	objects[%s] = self;' % idx,
					]
				else:
					draw += [
						#'	rect( %s,%s, %s,%s, %s,%s,%s, %s);' %(x,z,w,h,r,g,b,a),
						'	self = objects[%s];' % idx,
						'	rect(@intFromFloat(self.pos.x), @intFromFloat(self.pos.y), @intFromFloat(self.scl.x), @intFromFloat(self.scl.y), self.clr.r, self.clr.g, self.clr.b, self.clr.a);',
					]

	head += [
		'var objects: [%s]Object2D = undefined;' % len(meshes),
	]

	if 'self' in '\n'.join(draw):
		draw_header.append('	var self:Object2D = undefined;')

	draw.append('}')

	if init_data_in_groups:
		setup += setup_scl + setup_clr + setup_pos

	setup.append('}')

	return '\n'.join( head + setup + draw_header + draw)


def build_wasm(world):
	zig = blender_to_zig(world)
	#print(zig)
	build(zig)

def blender_to_zig_webgl(world):
	header = [ZIG_HEADER_WEBGL]
	data = []
	setup = []
	draw = []


	for ob in bpy.data.objects:
		if ob.hide_get(): continue
		sname = safename(ob)
		if ob.type=='MESH':
			if not ob.data.materials: continue
			a,b,c = mesh_to_zig(ob)
			data  += a
			setup += b
			draw  += c

	update = [
		'export fn update() void {',
		#'	gl_uniform_mat4fv(ploc, proj_matrix);',
		#'	gl_uniform_mat4fv(vloc, view_matrix);',

	] + draw
	update.append('}')


	main = [
		'export fn main() void {',
		'	gl_init(800, 600);',
		#'	view_matrix[14] = view_matrix[14] -3.0;',
	] + setup

	main.append('js_set_entry(&update);')
	main.append('}')

	return header + data + update + main

def mesh_to_zig(ob, mirror=False):
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
		'const VERTS_%s : [%s]f16 = .{%s};' %(sname,len(verts), ','.join(verts)),  ## 16bit float verts
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
			'const INDICES_%s_%s : [%s]u16 = .{%s};' %(sname, midx, len(mi), ', '.join(mi)),
		]


	mat = []
	for vec in ob.matrix_local:
		mat += [str(v) for v in vec]


	data += [
		'var %s_vbuff : i32 = undefined;' % name,
		'var %s_mat : [16]f32 = .{%s};' %(name,','.join(mat)),
	]


	return data, setup, draw


ZIG_ZAG_INIT = '''
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
		this.gl.getExtension("OES_standard_derivatives");
		this.bufs=[];
		this.vs=[];
		this.fs=[];
		this.progs=[];
		this.locs=[];
		this.wasm.instance.exports.main();
	}

'''

def build_webgl(world):
	zig = blender_to_zig_webgl(world)
	build(zig, jsapi=libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(ZIG_ZAG_INIT))



EXAMPLE1 = '''
self.pos.x += 0.3;
if (self.pos.x > 800) {
	self.pos.x = 0;
}
'''

EXAMPLE2 = '''
self.pos.x += self.speed;
if (self.pos.x > 800) {
	self.pos.x = 0;
}
'''

EXAMPLE3 = '''
if (random() < 0.001) {
	html_set_text(self.id, self.mystring);
}
'''

EXAMPLE4 = '''
if (random() < 0.002) {
	html_set_hide(self.id, 0);
}
'''


def test_scene():
	a = bpy.data.texts.new(name='example1.zig')
	a.from_string(EXAMPLE1)
	b = bpy.data.texts.new(name='example2.zig')
	b.from_string(EXAMPLE2)
	c = bpy.data.texts.new(name='example3.zig')
	c.from_string(EXAMPLE3)
	d = bpy.data.texts.new(name='example4.zig')
	d.from_string(EXAMPLE4)

	for y in range(8):
		for x in range(8):
			bpy.ops.mesh.primitive_plane_add()
			ob = bpy.context.active_object
			ob.location.x = x*64
			ob.location.z = -y*64
			ob.scale = [16,16,0]
			ob.rotation_euler.x = math.pi/2
			ob.color = [1,0,y*0.1,1]
			if random() < 0.2:
				ob.zig_script0 = a
			elif random() < 0.2:
				ob.zig_script0 = b
				ob['speed'] = 0.5

	for y in range(6):
		for x in range(8):
			bpy.ops.object.text_add()
			ob = bpy.context.active_object
			ob.data.body = choice(['🌠', '⭐', '🍔', '🍟', '🍕', '🌭', '🥩', '🥓', '🌯', '🌮'])
			ob.data.size *= uniform(0.4, 0.8)
			ob.location.x = 32 + (x*42)
			ob.location.z = -(10 + (y*42))
			ob.location.x += uniform(-5,5)

			if ob.data.body != '⭐':
				ob.zig_script0 = c
				ob['mystring'] = '🌠' # choice(['⭐', '🚑'])

	for x,c in enumerate('hello zig'):
		bpy.ops.object.text_add()
		ob = bpy.context.active_object
		ob.data.body = c
		ob.location.x = 32 + (x*46)
		ob.location.z = -320
		ob.zig_hide = True
		ob.zig_script0 = d

	bpy.ops.object.gpencil_add(type='MONKEY')
	ob = bpy.context.active_object
	ob.location.x = 600
	ob.location.z = -150


if __name__=='__main__':
	register()
	if '--2d' in sys.argv:
		if '--monkey' in sys.argv:
			bpy.ops.object.gpencil_add(type='MONKEY')
			ob = bpy.context.active_object
			ob.location.x = 100
			ob.location.z = -150
		else:
			test_scene()

		build_wasm(bpy.data.worlds[0])
	else:
		bpy.data.objects['Cube'].hide_set(True)
		ob = libgenzag.monkey()
		ob.rotation_euler.x = -math.pi/2
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
		build_webgl(bpy.data.worlds[0])
		
