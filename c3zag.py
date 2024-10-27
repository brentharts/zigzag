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
	#version 410

	layout( location = 0 ) in vec3 vp;
	layout( location = 1 ) in vec3 vcolor;

	out vec3 theColor;

	void main () {
		theColor = vcolor;
		gl_Position = vec4(vp, 1.0);
	}
`;

const char* FRAGMENT_SHADER = `
	#version 410

	in vec3 theColor;
	out vec4 frag_colour;

	void main () {
		frag_colour = vec4(theColor, 1.0);
	}
`;


float[] cube_data = {
		-0.5, -0.5, 0.0, 1.0, 0.5, 1.0,
		 0.5, -0.5, 0.0, 1.0, 0.5, 1.0,
		 0.0,  0.5, 0.0, 1.0, 0.5, 1.0
};

float[] indices = {
	0, 1, 3,
	1, 2, 3	
};

fn void main() @extern("main") @wasm {
	gl_init();
	gl_enable("DEPTH_TEST");
	gl_depth_func("LESS");
	int buff = gl_new_buffer();
	gl_bind_buffer(buff);

	//int cube_size = cube_data.len * float.sizeof;
	gl_buffer_data(buff, cube_data.len, cube_data);
}


'''

WASM_MINI_GL = '''
extern fn void gl_init();
extern fn void gl_enable(char *ptr);
extern fn void gl_depth_func(char *ptr);
extern fn int  gl_new_buffer();
extern fn void gl_bind_buffer(int idx);
extern fn void gl_buffer_data(int idx, int sz, float *ptr);

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
		this.wasm.instance.exports.main();
	}

	gl_init() {
		this.gl.clearColor(1,0,0, 1);
		this.gl.clear(this.gl.COLOR_BUFFER_BIT);
	}

	gl_enable(ptr){
		const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log("gl enable:", key);
		this.gl.enable(this.gl[key]);
	}

	gl_depth_func(ptr){
		const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log("gl depthFunc:", key);
		this.gl.depthFunc(this.gl[key]);
	}
	gl_new_buffer(){
		return this.bufs.push(this.gl.createBuffer())-1;
	}
	gl_bind_buffer(i){
		const b=this.bufs[i];
		console.log("bind buffer:", b);
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,b);
	}
	gl_buffer_data(i, sz, ptr){
		const b=this.bufs[i];
		console.log("buffer data:", b);
		const arr = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		this.gl.bufferData(this.gl.ARRAY_BUFFER, arr, this.gl.STATIC_DRAW);
	}
	gl_new_vshader(ptr){
		const s = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log('new vertex shader', s);
		return this.vs.push(this.gl.createShader(this.gl.VERTEX_SHADER,s))-1;
	}
	gl_new_fshader(ptr){
		const s = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
		console.log('new fragment shader', s);
		return this.fs.push(this.gl.createShader(this.gl.FRAGMENT_SHADER,s))-1;
	}
	gl_new_program(){
		return this.progs.push(this.gl.createProgram())-1;
	}
	gl_attach_vshader(a,b){
		const prog = this.progs[a];
		this.gl.attachShader(prog, this.vs[b]);
	}
	gl_attach_fshader(a,b){
		const prog = this.progs[a];
		this.gl.attachShader(prog, this.fs[b]);
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
