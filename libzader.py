GLSL_XFORM = '''
mat3 rot3(vec3 r) {
	float cx = cos(r.x);
	float sx = sin(r.x);
	float cy = cos(r.y);
	float sy = sin(r.y);
	float cz = cos(r.z);
	float sz = sin(r.z);
	return mat3(cy * cz, 	cx * sz + sx * sy * cz, 	sx * sz - cx * sy * cz,
			-cy * sz,	cx * cz - sx * sy * sz,		sx * cz + cx * sy * sz,
			sy,			-sx * cy,					cx * cy);
}

mat4 xform(vec3 t, vec3 sc, vec3 r) {
	mat3 scale = mat3(sc.x, 0.0, 0.0,
	0.0, sc.y, 0.0,
	0.0, 0.0, sc.z);
	mat3 xfm = rot3(r)*scale;
	return mat4(
		xfm[0], 0.0,
		xfm[1], 0.0,
		xfm[2], 0.0,
		t, 1.0
	);
}
'''


## MP = model position, MS = model scale, MR = model rotation
VSHADER_GPU_XFORM = '''
attribute vec3 vp;
uniform mat4 P;
uniform mat4 V;
uniform vec3 MP;
uniform vec3 MS;
uniform vec3 MR;
uniform vec3 T;
varying vec3 VVS;
varying vec3 VC;

void main() {
	mat4 xfm=xform(MP,MS,MR);
	gl_Position=P*V*xfm*vec4(vp,1.0);
	VVS=(xfm*V*vec4(vp,1.0)).xyz;
	VC=T;
}
'''

# P = projection, V = view, M = model, T = tint
# VVS vertex view space
VSHADER_CPU_XFORM = '''
attribute vec3 vp;
uniform mat4 P;
uniform mat4 V;
uniform mat4 M;
uniform vec3 T;
varying vec3 VVS;
varying vec3 VC;
void main(void){
	VVS=(M*V*vec4(vp,1.0)).xyz;
	gl_Position=P*V*M*vec4(vp,1.);
	VC=T;
}
'''

FSHADER = '''
varying vec3 VVS;
varying vec3 VC;
void main(void){
	vec3 U=dFdx(VVS);
	vec3 V=dFdy(VVS);
	vec3 N=normalize(cross(U,V));
	vec3 f=vec3(1.1,1.1,1.1)*N.z;
	gl_FragColor=vec4( (VC+(N*0.2))*f ,1.0);
}
'''

FSHADER_FLAT = '''
varying vec3 VVS;
varying vec3 VC;
void main(void){
	vec3 U=dFdx(VVS);
	vec3 V=dFdy(VVS);
	vec3 N=normalize(cross(U,V));
	vec3 f=vec3(1.1,1.1,1.1)*N.z;
	gl_FragColor=vec4( VC,1.0);
}
'''

def gen_shaders(vshader=VSHADER_GPU_XFORM, fshader=FSHADER, mode='C3', webgl=True):
	if webgl:
		if '#extension GL_OES_standard_derivatives:enable' not in fshader:
			fshader = '#extension GL_OES_standard_derivatives:enable\n' + fshader
	if mode.upper()=='ZIG':
		o = [
			'const VERTEX_SHADER =',
		]
		for ln in vshader.splitlines():
			ln = ln.strip()
			if not ln: continue
			if ln.startswith('//'): continue
			o.append(r'\\' + ln)  ## yes, multi-line strings in zig start with \\
		o.append(';')
		o.append('const FRAGMENT_SHADER =')
		for ln in fshader.splitlines():
			ln = ln.strip()
			if not ln: continue
			if ln.startswith('//'): continue
			o.append(r'\\' + ln)  ## yes, multi-line strings in zig start with \\
		o.append(';')
		return '\n'.join(o)
	elif mode.upper()=='RUST':
		assert '"' not in vshader
		assert '"' not in fshader
		## https://doc.rust-lang.org/reference/tokens.html#c-string-literals
		o = [
			'const VERTEX_SHADER:&str = "',
		]
		for ln in vshader.splitlines():
			ln = ln.strip()
			if not ln: continue
			if ln.startswith('//'): continue
			o.append(ln)
		o.append('\0x00";')
		o.append('const FRAGMENT_SHADER:&str = "')
		for ln in fshader.splitlines():
			ln = ln.strip()
			if not ln: continue
			if ln.startswith('//'): continue
			o.append(ln)
		o.append('\0x00";')
		return '\n'.join(o)
	else:
		o = [
			'const char* VERTEX_SHADER = `%s`;' % vshader,
			'const char* FRAGMENT_SHADER = `%s`;' % fshader,
		]
		return '\n'.join(o)
