#!/usr/bin/env python3
import os, sys, subprocess, base64
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
import zigzag, libwebzag
from zigzag import GZIP


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


def build(rs, jsapi=None):
	if not jsapi:
		jsapi=libwebzag.JS_API_HEADER + libwebzag.gen_webgl_api(zigzag.ZIG_ZAG_INIT)

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

TEST1 = '''

use std::ffi::CString;
use std::os::raw::c_char;

extern "C"{
	//fn alert(s:&str);
	fn alert(s:*const u8);
}

#[no_mangle]
pub fn add_one(x: i32) -> i32 {
	x + 1
}

#[no_mangle]
pub fn main() {
	unsafe{
		//alert("hello world".as_ptr());
		alert(
			CString::new("hello world").unwrap().as_ptr()  as *const u8
		);
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
if __name__=='__main__':
	if '--no-std' in sys.argv:
		build(NO_STD)
	else:
		build(TEST1)
	os.system('ls -lh /tmp/*.wasm')