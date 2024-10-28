#!/usr/bin/python3
import os, sys, subprocess, base64, webbrowser
_thisdir = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(_thisdir)
import zigzag


C3 = '/usr/local/bin/c3c'

islinux=iswindows=c3gz=c3zip=None
if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-windows.zip'
	C3 = os.path.join(_thisdir,'c3/c3c.exe')
	iswindows=True
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
	c3zip = 'https://github.com/c3lang/c3c/releases/download/latest/c3-macos.zip'
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
				if not os.path.isfile('c3-windows.zip'):
					cmd = ['C:/Windows/System32/curl.exe', '-o', 'c3-windows.zip', c3zip]
					print(cmd)
					subprocess.check_call(cmd)
			elif c3zip:
				if not os.path.isfile('c3-macos.zip'):
					cmd = ['curl', '-o', 'c3-macos.zip', c3zip]
					print(cmd)
					subprocess.check_call(cmd)

		if islinux:
			C3 = os.path.abspath('./c3/c3c')
		elif iswindows:
			C3 = os.path.abspath('./c3/c3c.exe')

print('c3c:', C3)
assert os.path.isfile(C3)


WASM_TEST = '''
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

float[] proj_matrix = {1.3737387097273113,0,0,0,0,1.8316516129697482,0,0,0,0,-1.02020202020202,-1,0,0,-2.0202020202020203,0};
float[] mov_matrix = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
float[] view_matrix = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};

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
'''

JS_MINI_GL = 'class api {' + zigzag.JS_API_PROXY + '''

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

	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', wasm]
	print(cmd)
	subprocess.check_call(cmd)
	wa = open(wasm,'rb').read()
	w = open(wasm+'.gz','rb').read()
	b = base64.b64encode(w).decode('utf-8')

	jtmp = '/tmp/c3api.js'
	open(jtmp,'w').write(zigzag.JS_API_HEADER + JS_MINI_GL)
	cmd = ['gzip', '--keep', '--force', '--verbose', '--best', jtmp]
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


if __name__=='__main__':
	test_wasm()
