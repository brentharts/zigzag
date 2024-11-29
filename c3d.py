C3_EXTERNS = '''
extern fn float js_sin(float a);
extern fn float js_cos(float a);
extern fn float js_rand();
extern fn int   js_eval(char*ptr);
extern fn char genchar() @extern("genchar");
extern fn void console_log(int c) @extern("console_log");
'''

C3_VIRT_OBJ = '''
struct Vec3 {
	float x;
	float y;
	float z;
}

struct Object3D {
	Vec3 position;
	Vec3 rotation;
	Vec3 scale;
}

'''



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

DEBUG_CAMERA_Y_UP = '''
float[] proj_matrix = {1.3737387097273113,0,0,0,0,1.8316516129697482,0,0,0,0,-1.02020202020202,-1,0,0,-2.0202020202020203,0};
float[] view_matrix = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
'''

DEBUG_CAMERA = '''
float[] proj_matrix = {1.8106600046157837, 0.0, 0.0, 0.0, 0.0, 2.4142134189605713, 0.0, 0.0, 0.0, 0.0, -1.0202020406723022, -1.0, 0.0, 0.0, -2.0202019214630127, 0.0};
float[] view_matrix = {1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -5.0, 1.0};
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
extern fn char genchar() @extern("genchar");
extern fn void console_log(int c) @extern("console_log");

extern fn void mesh_deform(ichar *ptr, int sz);
//extern fn void mesh_deform(short *ptr, int sz);

//def Entry = fn void();
//extern fn void js_set_entry(Entry entry);


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
extern fn void gl_uniform_3fv(int loc, float *mat);

extern fn void gl_draw_triangles(int len);
extern fn void gl_draw_tris_tint(int len, float r, float g, float b);

extern fn void gl_material_translate(int matid, int vid, float x, float y, float z);

extern fn void gl_trans(int matid, float x, float y, float z);
extern fn void gl_trans_upload(int vid);


extern fn float js_sin(float a);
extern fn float js_cos(float a);
extern fn float js_rand();
extern fn int   js_eval(char*ptr);

'''

JS_MOD_API_TODO = '''
	mod_rand(a,m){
		for(var j=0;j<a.length;j++){
			if(a[j]){
				a[j]+=Math.random()*m.value
			} else {
				j+=2
			}
		}
		return a;
	}
'''

#JS_MINI_GL = 'class api {' + zigzag.JS_API_PROXY + '''

DEPRECATED = '''
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

'''

C3_ZAG_INIT = '''
	console_log(a){console.log(a)}

	reset(wasm,id,bytes){
		this.wasm=wasm;
		this.gby=new Uint8Array(bytes);
		this.gbi=0;
		this.canvas=document.getElementById(id);
		this.canvas.onclick=this.onclick.bind(this);
		this.gl=this.canvas.getContext('webgl');
		this.gl.getExtension("OES_standard_derivatives");
		this.bufs=[];
		this.vs=[];
		this.fs=[];
		this.progs=[];
		this.locs=[];
		//this.mods=[{op:"mod_rand",value:0.1}];
		this.mods=[];
		this.update=this.wasm.instance.exports.update;
		this.wasm.instance.exports.main();
		const f=(ts)=>{
			this.dt=(ts-this.prev)/1000;
			this.prev=ts;
			this.update(this.dt);
			window.requestAnimationFrame(f)
		};
		window.requestAnimationFrame((ts)=>{
			this.prev=ts;
			window.requestAnimationFrame(f)
		});
	}

	genchar(){
		if(this.gbi>=this.gby.length)this.gbi=0;
		return this.gby[this.gbi++]
	}

	onclick(e){
		console.log("onclick:", e);
		this.wasm.instance.exports.onclick(e.x,e.y)
	}

'''



SHADER_HEADER_CPU = '''
int vs;
int fs;
int prog;
int ploc;
int vloc;
int mloc;
int posloc;
int clrloc;
'''

SHADER_SETUP_CPU = '''
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

SHADER_HEADER_GPU = '''
int vs;
int fs;
int prog;
int ploc;
int vloc;
int mploc;
int msloc;
int mrloc;
int posloc;
int clrloc;
'''

SHADER_SETUP_GPU = '''
	vs = gl_new_vshader(VERTEX_SHADER);
	fs = gl_new_fshader(FRAGMENT_SHADER);

	prog = gl_new_program();
	gl_attach_vshader(prog, vs);
	gl_attach_fshader(prog, fs);
	gl_link_program( prog );

	ploc = gl_get_uniform_location(prog, "P");  // projection Pmat
	vloc = gl_get_uniform_location(prog, "V");  // view matrix
	mploc = gl_get_uniform_location(prog, "MP");
	msloc = gl_get_uniform_location(prog, "MS");
	mrloc = gl_get_uniform_location(prog, "MR");

	posloc = gl_get_attr_location(prog, "vp");  // vertex position
	clrloc = gl_get_attr_location(prog, "vc");  // vertex color

'''



SHADER_POST = '''
	gl_use_program(prog);

'''

CPU_HELPER_FUNCS = '''
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
