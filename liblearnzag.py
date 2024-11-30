
GEN_CHAR_TEST = """
.c3.script = '''
fn void onclick( int x, int y ) @extern("onclick") @wasm {
	js_eval(`
		window.alert("hello click")
	`);
	for (int i=0; i<100; i++){
		int c = genchar();
		console_log(c);
	}
}
'''
ƣ.c3.script = '''
self.rotation.z += 0.01;
'''
txt = bpy.data.texts.new(name='after_export.py')
txt.from_string('''
for i in range(100):
	c = genchar()
	print(c)
''')
"""


LEARN_C3 = [
"""🧱
.c3.script = '''
struct Brick{
	float[3] pos;
	float[3] scl;
	float[3] rot;
	char[3]  clr;
}

Brick[120] bricks;

fn void onload(){
	float n, px, py, sx,sy, x,y, brick_width, brick_height;
	char r=200;
	char g=20;
	char b=20;
	int brick_cols = 20;
	int brick_rows = 6;
	int rows = 0;
	x = -2;
	px = x;
	py = 0;
	brick_width=0.1;
	brick_height=0.04;
	for (int i=0; i<120; i++){
		char c = genchar();
		console_log(c);
		if (c >= 1){
			bricks[i].clr[0]=r;
			bricks[i].clr[1]=g;
			bricks[i].clr[2]=b;

			bricks[i].pos[0]=px;
			bricks[i].pos[2]=py;

			bricks[i].scl[0]=brick_width;
			bricks[i].scl[1]=brick_height;
			bricks[i].scl[2]=brick_height;

		}

		px += (brick_width*2) + (brick_height/6);
		n ++;

		if (n >= brick_cols){
			if ( rows % 2){
				px = x;
			} else {
				px = x+(brick_width/2);
			}
			py += (brick_height*2) + (brick_height/4);
			n = 0;
			rows +=1;
		}
	}
}

fn void ondraw(float dt){
	for (int i=0; i<120; i++){
		gl_bind_buffer(brick_vbuff);
		gl_uniform_3fv(mploc, &bricks[i].pos);
		gl_uniform_3fv(msloc, &bricks[i].scl);
		gl_uniform_3fv(mrloc, &bricks[i].rot);
		gl_bind_buffer_element(brick_ibuff);
		gl_draw_tris_tint( 36, 
			bricks[i].clr[0]/255.0f,
			bricks[i].clr[1]/255.0f,
			bricks[i].clr[2]/255.0f
		);
	}
}
'''

txt = bpy.data.texts.new(name='after_export.py')
txt.from_string('''
zag.bytes_to_bricks(wasm)
for i in range(100):
	c = genchar()
	print(c)
''')

""",

]

LEARN_ZIG = [
"""
.zig.script = r'''

export fn onclick( x:i32, y:i32 ) void {
	js_eval(
		"window.alert('hello click')"
	);
	// Zig is super strict, if x and y are not used in the function,
	// you will get: `Error: unused function parameter`
	// An ugly way to workaround this is to have this simple statement
	_=x+y;
	// note: the Zig compiler will optimize away `_=x+y`
}
'''
""",

]

LEARN_RUST = [
"""
.rust.script = r'''

#[no_mangle]
pub fn onclick( _x:i32, _y:i32 ) {
	unsafe{
		js_eval(
			"window.alert('hello click')\\0".as_ptr()
		);
	}
}
'''
""",

]

