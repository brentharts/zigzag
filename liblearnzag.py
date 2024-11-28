

LEARN_C3 = [
"""
.c3.script = '''

fn void onclick( int x, int y ) @extern("onclick") @wasm {
	js_eval(`
		window.alert("hello click")
	`);
}

'''
ƣ.c3.script = '''
self.rotation.z += 0.01;
'''

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

