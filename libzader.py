_GLSL_XFORM_ = '''
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

GLSL_XFORM = '''
mat3 rot3(vec3 r){
	float a=cos(r.x),b=sin(r.x),c=cos(r.y),d=sin(r.y),e=cos(r.z),f=sin(r.z);
	return mat3(c*e,a*f+b*d*e,b*f-a*d*e,-c*f,a*e-b*d*f,b*e+a*d*f,d,-b*c,a*c);
}
mat4 xform(vec3 t,vec3 sc,vec3 r){
	mat3 s=mat3(sc.x,.0,.0,.0,sc.y,.0,.0,.0,sc.z),x=rot3(r)*s;
	return mat4(x[0],.0,x[1],.0,x[2],.0,t,1.0);
}
'''

## MP = model position, MS = model scale, MR = model rotation
## T = tint, S = noise seeds
## N = noise scale x,y,z
#float PHI=1.61803398874989484820459; 

VSHADER_GPU_XFORM = '''
attribute vec3 vp;
uniform mat4 P,V;
uniform vec3 MP,MS,MR,T,S,N;
varying vec3 VVS;
varying vec3 VC;

float phi=13.0/7.0-0.239;
float rand(vec3 v,float s){
	return fract(tan(distance(v.xy*phi,v.xz)*s)*v.x);
}
void main(){
	mat4 x=xform(MP,MS,MR);
	vec3 v=vec3(
		vp.x+(rand(vp,S.x)*N.x),
		vp.y+(rand(vp,S.x)*N.y),
		vp.z+(rand(vp,S.x)*N.z)
	);
	gl_Position=P*V*x*vec4(v,1.0);
	VVS=(x*V*vec4(vp,1.0)).xyz;
	VC=T;
}
'''

## MP = model position, MS = model scale, MR = model rotation
VSHADER_GPU_XFORM_SIMPLE = '''
attribute vec3 vp;
uniform mat4 P,V;
uniform vec3 MP,MS,MR,T;
varying vec3 VVS;
varying vec3 VC;
void main(){
	mat4 x=xform(MP,MS,MR);
	gl_Position=P*V*x*vec4(vp,1.0);
	VVS=(x*V*vec4(vp,1.0)).xyz;
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
		if 'precision mediump float;' not in fshader:
			fshader = 'precision mediump float;\n' + fshader
		if '#extension GL_OES_standard_derivatives:enable' not in fshader:
			fshader = '#extension GL_OES_standard_derivatives:enable\n' + fshader

	if 'xform(' in vshader:
		vshader = GLSL_XFORM + vshader

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
