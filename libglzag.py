import os, sys, json, subprocess

def mesh_to_json(ob):
	verts = []
	faces = {}
	materials = []
	mat = []
	for vec in ob.matrix_local:
		mat += [v for v in vec]

	dump = {
		'name':ob.name,
		'data':ob.data.name,
		'verts':verts,
		'faces':faces,
		'materials':materials,
		'matrix': mat,
		'pos': list(ob.location),
		'rot': list(ob.rotation_euler),
		'scl': list(ob.scale),
		'parent':None,
	}
	if ob.parent:
		dump['parent']=ob.parent.name

	for v in ob.data.vertices:
		verts += list(v.co)

	indices_by_mat = faces
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

	for mat in ob.data.materials:
		materials.append({'name':mat.name, 'color':list(mat.diffuse_color)})


	return dump


def blend_to_json(name):
	import bpy
	assert name in bpy.data.objects
	dump = {}
	ob = bpy.data.objects[name]
	if ob.type=="MESH":
		dump.update( mesh_to_json(ob) )
	return dump

out = None
obj = None
for arg in sys.argv:
	if arg.startswith('--json='):
		out = arg.split('=')[-1]
	if arg.startswith('--dump='):
		obj = arg.split('=')[-1]

if out:
	assert obj
	dump = blend_to_json(obj)
	open(out,'wb').write(
		json.dumps(dump).encode('utf-8')
	)
	sys.exit()


if sys.platform == 'win32':
	BLENDER = 'C:/Program Files/Blender Foundation/Blender 4.2/blender.exe'
	if not os.path.isfile(BLENDER):
		BLENDER = 'C:/Program Files/Blender Foundation/Blender 3.6/blender.exe'
elif sys.platform == 'darwin':
	BLENDER = '/Applications/Blender.app/Contents/MacOS/Blender'
else:
	BLENDER = 'blender'
	if os.path.isfile(os.path.expanduser('~/Downloads/blender-4.2.1-linux-x64/blender')):
		BLENDER = os.path.expanduser('~/Downloads/blender-4.2.1-linux-x64/blender')


import numpy as np
from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_FLOAT, GL_TRIANGLES, GL_ARRAY_BUFFER, GL_STATIC_DRAW, GL_ELEMENT_ARRAY_BUFFER, GL_FALSE
from OpenGL.GL import GL_UNSIGNED_INT, GL_UNSIGNED_SHORT
from OpenGL.GL import glClear, glClearColor, glDrawArrays, glGenBuffers, glBindBuffer, glDrawElements, glViewport, glGetError
from OpenGL.GL import glBufferData, glEnableVertexAttribArray, glVertexAttribPointer, glUniformMatrix4fv, glUniform3fv

import OpenGL.GL as gl

try:
	import PySide6
except:
	PySide6=None

if PySide6:
	from PySide6.QtCore import Qt
	from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
	from PySide6.QtOpenGLWidgets import QOpenGLWidget
	from PySide6.QtWidgets import QApplication
else:
	from PyQt6.QtCore import Qt
	from PyQt6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
	from PyQt6.QtOpenGLWidgets import QOpenGLWidget
	from PyQt6.QtWidgets import QApplication
	#from PyQt6.QtOpenGL import QOpenGLFunctions_4_1_Core as QOpenGLFunctions
	#from PyQt6.QtOpenGL import QOpenGLFunctions_2_1_Core as QOpenGLFunctions



# VVS vertex view space
VSHADER = '''
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

#TypeError: could not convert 'Viewer' to 'QOpenGLFunctions_4_1_Core'
#class Viewer(QOpenGLWidget, QOpenGLFunctions):
class Viewer(QOpenGLWidget):
	def __init__(self, width=256, height=256):
		super().__init__()
		self._width=width
		self._height=height
		self.setFixedSize(width, height)
		print('new gl viewer', self)
		self.buffers = {}
		self.debug_draw = True
		self.active_object = None

	def initializeGL(self):
		print('init gl')
		#self.initializeOpenGLFunctions()
		glClearColor(1, 0.5, 0.1, 1)
		glViewport(0,0,self._width,self._height)

		vertShaderSrc = """
			attribute vec3 vp;
			void main()
			{
				gl_Position = vec4(vp, 1.0);
			}
		"""

		fragShaderSrc = """
			#ifdef GL_ES
			precision mediump float;
			#endif
			void main()
			{
				gl_FragColor = vec4(0.2, 0.7, 0.3, 1.0);
			}
		"""

		self.program = QOpenGLShaderProgram(self)
		self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, vertShaderSrc)
		self.program.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, fragShaderSrc)
		self.program.link()
		self.program.bind()

		self.prog=None

		vertPositions = np.array([
			-0.5, -0.5, 0,
			0.5, -0.5, 0,
			0, 0.5, 0], dtype=np.float32)

		vbo = glGenBuffers(1)
		print('vbo:', vbo)
		glBindBuffer(GL_ARRAY_BUFFER, vbo)
		glBufferData(GL_ARRAY_BUFFER, vertPositions, GL_STATIC_DRAW)
		self.vbo = vbo

		#indices = np.array([0,1,2], dtype=np.uint32)
		indices = np.array([0,1,2], dtype=np.uint16)

		ibo = glGenBuffers(1)
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
		print('gl error:', glGetError())

		#glBufferData(GL_ELEMENT_ARRAY_BUFFER, 3*4, indices, GL_STATIC_DRAW)
		glBufferData(GL_ELEMENT_ARRAY_BUFFER, 3*2, indices, GL_STATIC_DRAW)
		print('gl error:', glGetError())
		self.ibo = ibo


	def resizeGL(self, w, h):
		pass

	def paintGL(self):
		print('gl redraw')
		glClear(GL_COLOR_BUFFER_BIT)
		self.program.bind()

		glBindBuffer(GL_ARRAY_BUFFER, self.vbo)

		if '--draw-elements' in sys.argv:
			posloc = self.program.attributeLocation("vp")
			print('posloc:', posloc)
			glVertexAttribPointer(posloc,3, GL_FLOAT, GL_FALSE, 0,0)
			print('gl error:', glGetError())

			glEnableVertexAttribArray(posloc)
			print('gl error:', glGetError())

			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
			print('gl error:', glGetError())

			#indices = np.array([0,1,2], dtype=np.uint32)
			#glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices, GL_STATIC_DRAW)
			#print('gl error:', glGetError())

			#glDrawElements(GL_TRIANGLES, 3, GL_UNSIGNED_INT, 0)

			glDrawElements(GL_TRIANGLES, 3, GL_UNSIGNED_SHORT, None)  ## this must be None and not 0
			print('gl error:', glGetError())

		else:
			self.program.setAttributeBuffer("vp", GL_FLOAT, 0, 3)
			self.program.enableAttributeArray("vp")
			glDrawArrays(GL_TRIANGLES, 0, 3)



	def debug_paintGL_old(self):
		print('gl redraw')
		glClear(GL_COLOR_BUFFER_BIT)
		self.program.bind()
		self.vertPosBuffer.bind()
		self.program.setAttributeBuffer("vp", GL_FLOAT, 0, 3)
		self.program.enableAttributeArray("vp")
		glDrawArrays(GL_TRIANGLES, 0, 3)

		#self.iBuffer.bind()
		glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
		glDrawElements(GL_TRIANGLES, 1, GL_UNSIGNED_INT, 0)

	def paintGL_TODO(self):
		if self.debug_draw:
			self.debug_paintGL()
			return
		if not self.active_object:
			print('no active_object')
			return

		print('redraw:', self.active_object)
		gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
		ob = self.buffers[self.active_object]
		self.prog.bind()
		#ob['VBUFF'].bind()
		vbo = ob['VBUFF']
		glBindBuffer(GL_ARRAY_BUFFER, vbo)



		P = [1.3737387097273113,0.0,0.0,0.0,0.0, 1.8316516129697482,0.0,0.0,0.0,0.0, -1.02020202020202,-1.0,0.0,0.0,-2.0202020202020203,0.0];
		V = [1.0,0.0,0.0,0.0, 0.0,1.0,0.0,0.0, 0.0,0.0,1.0,0.0, 0.0,0.0,0.0,1.0];
		V[14] -= 3.0
		#print(dir(self.program))  ## .programId() to get int ID
		#self.program.setUniformValueArray(0, np.array(P,dtype=np.float32))

		loc = self.prog.uniformLocation("P")
		print('P loc:', loc)
		glUniformMatrix4fv(loc,1,GL_FALSE, np.array(P,dtype=np.float32))

		loc = self.prog.uniformLocation("V")
		print('V loc:', loc)
		glUniformMatrix4fv(loc,1,GL_FALSE, np.array(V,dtype=np.float32))

		loc = self.prog.uniformLocation("M")
		print('M loc:', loc)
		M = ob['matrix']
		glUniformMatrix4fv(loc,1,GL_FALSE, np.array(M,dtype=np.float32))

		loc = self.prog.uniformLocation("T")
		print('T loc:', loc)


		#posloc = self.prog.attributeLocation("vp")
		#print('posloc:', posloc)
		#glVertexAttribPointer(posloc,3, GL_FLOAT, GL_FALSE, 0,0)
		#glEnableVertexAttribArray(posloc)

		self.prog.setAttributeBuffer("vp", gl.GL_FLOAT, 0,3)
		self.prog.enableAttributeArray("vp")


		#self.program.setAttributeBuffer("aPosition", gl.GL_FLOAT, 0, 2)
		#self.program.enableAttributeArray("aPosition")

		#glDrawArrays( GL_TRIANGLES, 0, len(ob['verts']) )  ## draws a triangle

		for matid in ob['faces']:
			glUniform3fv(loc, 1, np.array([1,0.1,0.3], dtype=np.float32))
			f = ob['faces'][matid]
			ibo = f['IBUFF']
			print('bind ibo:', ibo)
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ibo)
			#glDrawElements(GL_TRIANGLES, len(f['INDICES']), GL_UNSIGNED_INT, 0)
			n = len(f['INDICES']) #//4
			print('draw tris:',n)
			n = f['num']
			print('numi', n)
			glDrawElements(GL_TRIANGLES, n, GL_UNSIGNED_INT, 0)
			#glDrawElements(GL_TRIANGLES, 4, GL_UNSIGNED_INT, 0)

	def view_blender_object(self, name, blend):
		if not self.prog:
			self.prog = QOpenGLShaderProgram(self)
			self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, VSHADER)
			self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, FSHADER)
			self.prog.link()
		self.prog.bind()

		if name not in self.buffers:
			cmd = [BLENDER, blend, '--background', '--python', __file__, '--', '--json=/tmp/__object__.json', '--dump=%s' % name]
			print(cmd)
			subprocess.check_call(cmd)
			ob = json.loads(open('/tmp/__object__.json').read())
			print('got json:', ob)

			#buff = QOpenGLBuffer()
			#print(name, buff)
			#buff.create()
			#buff.bind()
			#buff.allocate(np.array(ob['verts'], dtype=np.float32), len(ob['verts'])*4 )
			vbo = glGenBuffers(1)
			print('vbo:', vbo)
			glBindBuffer(GL_ARRAY_BUFFER, vbo)
			vertices = np.array(ob['verts'], dtype=np.float32)
			print('verts:', vertices)
			glBufferData(GL_ARRAY_BUFFER, vertices, GL_STATIC_DRAW)
			
			#posloc = self.prog.attributeLocation("vp")
			#print('posloc:', posloc)
			#glVertexAttribPointer(posloc,3, GL_FLOAT, GL_FALSE, 0,0)
			#glEnableVertexAttribArray(posloc)

			self.prog.setAttributeBuffer("vp", gl.GL_FLOAT, 0, 3)
			self.prog.enableAttributeArray("vp")


			a = {
				'VBUFF': vbo,
			}
			a.update(ob)
			self.buffers[name]=a
			for matid in a['faces']:
				f = a['faces'][matid]
				#indices = []
				#for quad in f['indices']:
				#	indices += quad
				#print(indices)
				indices = quads_to_tris(f['indices'])
				f['INDICES'] = np.array(indices,dtype=np.uint32)
				ibo = glGenBuffers(1)
				glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
				glBufferData(GL_ELEMENT_ARRAY_BUFFER, f['INDICES'], GL_STATIC_DRAW)
				f['IBUFF'] = ibo

				#glEnableVertexAttribArray(0)
				#self.program.glEnableVertexAttribArray(0)
				#glVertexAttribPointer(0,3, GL_FLOAT, GL_FALSE, 0,0)

		self.active_object = name
		self.debug_draw=False

def quads_to_tris(quads):
	tris = []
	for q in quads:
		a,b,c,d = q
		tris += [a,b,c]
		if d == 65000: continue
		tris += [c,d,a]
	return tris

if __name__ == "__main__":
	QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
	app = QApplication(sys.argv)
	w = Viewer(800, 600)
	w.show()
	for arg in sys.argv:
		if arg.endswith('.blend'):
			w.view_blender_object('Cube', arg)
	sys.exit(app.exec())
