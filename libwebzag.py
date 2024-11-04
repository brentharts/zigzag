JS_DECOMP = '''
var $d=async(u,t)=>{
	var d=new DecompressionStream('gzip')
	var r=await fetch('data:application/octet-stream;base64,'+u)
	var b=await r.blob()
	var s=b.stream().pipeThrough(d)
	var o=await new Response(s).blob()
	if(t) return await o.text()
	else return await o.arrayBuffer()
}

$d($0,1).then((j)=>{
	$=eval(j)
	$d($1).then((r)=>{
		WebAssembly.instantiate(r,{env:$.proxy()}).then((c)=>{$.reset(c,"$",r)});
	});
});
'''

JS_API_HEADER = '''
function make_environment(e){
	return new Proxy(e,{
		get(t,p,r) {
			if(e[p]!==undefined){return e[p].bind(e)}
			return(...args)=>{throw p}
		}
	});
}

function cstrlen(m,p){
	var l=0;
	while(m[p]!=0){l++;p++}
	return l;
}

function cstr_by_ptr(m,p){
	const l=cstrlen(new Uint8Array(m),p);
	const b=new Uint8Array(m,p,l);
	return new TextDecoder().decode(b)
}
'''

JS_API_PROXY = '''
	proxy(){
		return make_environment(this)
	}
'''


def gen_webgl_api(user):
	o = [
		'class api{',
		JS_API_PROXY,
		user,
		DEFORM_ZAG,
		GL_ZAG,
		JS_ZAG,
	]

	o += [
	'}',
	'new api();'  ## used by $=eval
	]
	return '\n'.join(o)



JS_ZAG = '''
	js_sin(a){
		return Math.sin(a)
	}
	js_cos(a){
		return Math.cos(a)
	}
	js_rand(){
		return Math.random()
	}

'''

DEFORM_ZAG = '''
	mesh_deform(ptr,sz){
		var v=new Int8Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		//var v=new Int16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		this.mods.push({op:'mod_deform',value:v})
	}
	mod_deform(a,m){
		//Q=512
		for(var j=0;j<a.length;j++){
			a[j]+=m.value[j]/256
		}
		return a
	}

'''

GL_ZAG = '''
	gl_init(w,h) {
		this.canvas.width=w;
		this.canvas.height=h;
		this.gl.viewport(0,0,w,h);
		this.gl.enable(this.gl.DEPTH_TEST);
		//this.gl.clearColor(1,0,0, 1);
		//this.gl.clear(this.gl.COLOR_BUFFER_BIT)
	}

	//gl_enable(ptr){
	//	const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
	//	//console.log("gl enable:", key);
	//	this.gl.enable(this.gl[key])
	//}

	//gl_depth_func(ptr){
	//	const key = cstr_by_ptr(this.wasm.instance.exports.memory.buffer,ptr);
	//	//console.log("gl depthFunc:", key);
	//	this.gl.depthFunc(this.gl[key])
	//}

	gl_new_buffer(){
		var a=this.gl.createBuffer();
		a._={};
		return this.bufs.push(a)-1
	}

	gl_bind_buffer(i){
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.bufs[i]);
		this.vbuf=this.bufs[i]
	}
	gl_bind_buffer_element(i){
		this.gl.bindBuffer(this.gl.ELEMENT_ARRAY_BUFFER,this.bufs[i]);
		this.ibuf=this.bufs[i]
	}

	//gl_buffer_data(i, sz, ptr){
	//	const b=this.bufs[i];
	//	console.log("buffer data:", b);
	//	const arr = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
	//	this.gl.bufferData(this.gl.ARRAY_BUFFER, arr, this.gl.STATIC_DRAW)
	//}

	gl_material_translate(mi,vi, x,y,z){
		var v=this.bufs[mi]._arr_;
		var a=new Float32Array(this.bufs[vi]._arr_);
		for(var j=0;j<v.length;j++){
			var k=v[j]*3;
			//a[k]+=x;
			//a[k+1]+=y;
			//a[k+2]+=z;

			a[k+1]+=0.06 * Math.random();


		}
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.bufs[vi]);
		this.gl.bufferData(this.gl.ARRAY_BUFFER,a,this.gl.STATIC_DRAW)
	}
	gl_trans(i, x,y,z){
		// this should be an index buffer
		//console.log('trans:', i, x,y,z);
		this.bufs[i]._pos=[x,y,z];
		this.vbuf._[i]=this.bufs[i]
	}
	gl_trans_upload(i){
		var a=new Float32Array(this.bufs[i]._arr_);
		for (var k in this.bufs[i]._){
			//console.log('upload:', k);
			var [x,y,z]=this.bufs[i]._[k]._pos;
			//console.log('offset:', x,y,z);
			var v=this.bufs[i]._[k]._arr_;
			//console.log('indices:', v);
			for(var j=0;j<v.length;j++){
				var d=v[j]*3;
				a[d]+=x;
				a[d+1]+=y;
				a[d+2]+=z
			}
		}
		//console.log('vertex upload:', a);
		this.gl.bindBuffer(this.gl.ARRAY_BUFFER,this.bufs[i]);
		this.gl.bufferData(this.gl.ARRAY_BUFFER,a,this.gl.STATIC_DRAW)
	}

	gl_buffer_f16(i, sz, ptr){
		console.log('vertbuff flag:', i);
		var v=new Float16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log('vertex data:', v.length);
		//this.nverts=v.length;
		this.nverts=v.length/3;
		if(i){
			var a=new Array(...v);
			for(var j=0;j<v.length;j+=3){
				a.push(-v[j]);
				a.push(v[j+1]);
				a.push(v[j+2]);
			}
			console.log('vmirror:', a);
			v=a;
		}
		for(var j=0;j<this.mods.length;j++){
			var m=this.mods[j];
			v=this[m.op](v,m)
		}
		this.vbuf._arr_=new Float32Array(v);
		this.gl.bufferData(this.gl.ARRAY_BUFFER,this.vbuf._arr_,this.gl.STATIC_DRAW)
	}

	gl_buffer_f8(i,sz,ptr){
		var v=new Uint8Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log('new vcolors');
		console.log(v);
		if(i){
			v=new Array(...v).concat(new Array(...v));
			console.log('mirror vcolor:', v);
		}
		this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array(v), this.gl.STATIC_DRAW)
	}

	gl_buffer_element(i, sz, ptr){
		const v = new Uint16Array(this.wasm.instance.exports.memory.buffer,ptr,sz);
		console.log(v);
		var a=[];
		for(var j=0;j<v.length;j+=4){
			//a.push(v[j],v[j+1],v[j+2]);

			a.push(v[j]);
			a.push(v[j+1]);
			a.push(v[j+2]);

			if(v[j+3]==65000)continue;
			//if(!v[j+3])continue;

			//a.push(v[j+2],v[j+3],v[j+0]);

			a.push(v[j+2]);
			a.push(v[j+3]);
			a.push(v[j]);

		}
		if(i){
			var b=[];
			// mirror indices: copy and offset by length of input vector
			//for(var j=0;j<a.length;j++)b.push(a[j]+a.length);  //OOPS
			for(var j=0;j<a.length;j++)b.push(a[j]+this.nverts);
			console.log('mirror b:',b);
			a=a.concat(b);
			console.log('mirror a+b:', a);		
		}
		this.ibuf._arr_=new Uint16Array(a);
		this.gl.bufferData(this.gl.ELEMENT_ARRAY_BUFFER,this.ibuf._arr_,this.gl.STATIC_DRAW)
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
		this.loc_tint=this.gl.getUniformLocation(this.progs[a], 'T');
		this.gl.useProgram(this.progs[a])
	}

	gl_clear(r,g,b,a,z){
		this.gl.clearColor(r,g,b,a);
		this.gl.clearDepth(z);
		this.gl.clear(this.gl.COLOR_BUFFER_BIT|this.gl.DEPTH_BUFFER_BIT)
	}

	//gl_viewport(x,y,w,h){
	//	this.gl.viewport(x,y,w,h)
	//}

	gl_uniform_mat4fv(a,ptr){
		const mat = new Float32Array(this.wasm.instance.exports.memory.buffer,ptr,16);
		this.gl.uniformMatrix4fv(this.locs[a], false, mat)
	}
	gl_draw_triangles(n){
		//console.log('draw triangles:', n);
		this.gl.drawElements(this.gl.TRIANGLES,n,this.gl.UNSIGNED_SHORT,0);
		//this.gl.uniform3fv(this.loc_tint, new Float32Array([Math.random(),Math.random(),Math.random()]));
		//this.gl.drawElements(this.gl.TRIANGLES,32,this.gl.UNSIGNED_SHORT,0);
		//this.gl.uniform3fv(this.loc_tint, new Float32Array([0,0,0]));
		//this.gl.drawElements(this.gl.TRIANGLES,n-64,this.gl.UNSIGNED_SHORT,6*16)
	}

	gl_draw_tris_tint(n, r,g,b){
		//console.log('draw triangles:', n);
		this.gl.uniform3fv(this.loc_tint, new Float32Array([r,g,b]));
		this.gl.drawElements(this.gl.TRIANGLES,n,this.gl.UNSIGNED_SHORT,0)
	}

'''