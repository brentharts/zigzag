import os, sys, json, subprocess, math
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
from random import random, uniform
import libzader

def mesh_to_json(ob):
	import bpy
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
		'pos': list(ob.location),  ## not used in viewer
		'rotation': [math.degrees(r) for r in ob.rotation_euler],
		'scale': list(ob.scale),
		'parent':None,
		'camera':None,
	}
	if ob.parent:
		dump['parent']=ob.parent.name

	if 'Camera' in bpy.data.objects:
		cam = bpy.data.objects['Camera']
		mat = []
		for vec in cam.matrix_local:
			mat += [v for v in vec]
		dump['camera'] = mat

	for v in ob.data.vertices:
		verts += list(v.co)

	indices_by_mat = faces
	for p in ob.data.polygons:
		if p.material_index not in indices_by_mat:
			indices_by_mat[p.material_index] = {'num':0, 'indices':[], 'color':None}
			if p.material_index < len(ob.data.materials):
				mat = ob.data.materials[p.material_index]
				r,g,b,a = mat.diffuse_color
				indices_by_mat[p.material_index]['color']=(r,g,b)
				if mat.zigzag_object_type != 'NONE':
					indices_by_mat[p.material_index]['class'] = mat.zigzag_object_type

			else:
				r,g,b,a = ob.color
				indices_by_mat[p.material_index]['color']=(r,g,b)

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
		minfo = {'name':mat.name, 'color':list(mat.diffuse_color)}
		materials.append(minfo)
		if mat.zigzag_object_type != 'NONE':
			minfo['class'] = mat.zigzag_object_type

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
	import bpy
	import libgenzag
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
from OpenGL.GL import GL_UNSIGNED_INT, GL_UNSIGNED_SHORT, GL_DEPTH_TEST
from OpenGL.GL import glClear, glClearColor, glDrawArrays, glGenBuffers, glBindBuffer, glDrawElements, glViewport, glGetError
from OpenGL.GL import glBufferData, glEnableVertexAttribArray, glVertexAttribPointer, glUniformMatrix4fv, glUniform3fv, glEnable

import OpenGL.GL as gl

try:
	import PySide6
except:
	PySide6=None

if PySide6:
	from PySide6.QtCore import Qt
	from PySide6.QtGui import QMatrix4x4, QVector3D
	from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
	from PySide6.QtOpenGLWidgets import QOpenGLWidget
	from PySide6.QtWidgets import QApplication
else:
	from PyQt6.QtCore import Qt
	from PyQt6.QtGui import QMatrix4x4, QVector3D
	from PyQt6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram
	from PyQt6.QtOpenGLWidgets import QOpenGLWidget
	from PyQt6.QtWidgets import QApplication
	#from PyQt6.QtOpenGL import QOpenGLFunctions_4_1_Core as QOpenGLFunctions
	#from PyQt6.QtOpenGL import QOpenGLFunctions_2_1_Core as QOpenGLFunctions

USE_CPU_XFORM = '--cpu-xform' in sys.argv


#TypeError: could not convert 'Viewer' to 'QOpenGLFunctions_4_1_Core'
#class Viewer(QOpenGLWidget, QOpenGLFunctions):
class Viewer(QOpenGLWidget):
	def __init__(self, width=256, height=256):
		super().__init__()
		self.setMouseTracking(True) 
		self._width=width
		self._height=height
		self.setFixedSize(width, height)
		print('new gl viewer', self)
		self.buffers = {}
		self.debug_draw = True
		self.active_object = None
		self.projection = None
		self.spin_up = 0
		self.spin_side = 0
		self.cam_zoom = 5

	def mouseMoveEvent(self, event):
		pos = event.pos()
		x = pos.x() / self._width
		y = pos.y() / self._height
		x -= 0.5
		y -= 0.5
		#print(x,y)
		#print(event.buttons())
		if event.buttons() == Qt.MouseButton.LeftButton:
			pass
		elif event.buttons() == Qt.MouseButton.RightButton:
			self.cam_zoom = 5 + (y * 5)
		else:
			self.spin_side = x * 2
			self.spin_up = y * 3
		self.update()


	def initializeGL(self):
		print('init gl')
		#self.initializeOpenGLFunctions()
		glClearColor(0.25, 0.25, 0.25, 1)
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
		print('resizeGL:', w,h)
		self._width = w
		self._height = h
		glViewport(0,0,self._width,self._height)

	def debug_paintGL(self):
		#print('gl redraw debug')
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


	def paintGL(self):
		if self.debug_draw:
			self.debug_paintGL()
			return
		if not self.active_object:
			print('no active_object')
			return
		if '--debug' in sys.argv:
			print('redraw:', self.active_object)

		gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
		glEnable(GL_DEPTH_TEST)

		ob = self.buffers[self.active_object]
		self.prog.bind()
		#ob['VBUFF'].bind()
		vbo = ob['VBUFF']
		glBindBuffer(GL_ARRAY_BUFFER, vbo)
		needs_upload = False
		for matid in ob['faces']:
			f = ob['faces'][matid]
			moffset = []
			if int(matid) < len(ob['materials']):
				mat = ob['materials'][ int(matid) ]
				if 'POSITION' in mat:
					moffset = mat['POSITION']
				if 'SCALE' in mat:
					moffset += mat['SCALE']
			if tuple(f['TRANS']+moffset) != f['TRANS_PREV']:
				f['TRANS_PREV'] = tuple(f['TRANS']+moffset)
				needs_upload = True

		if needs_upload:
			#print('doing vert upload')
			arr = list(ob['verts'])  ## copy verts
			for matid in ob['faces']:
				f = ob['faces'][matid]
				x,y,z = f['TRANS']
				sx = sy = sz = 1.0

				if int(matid) < len(ob['materials']):
					mat = ob['materials'][ int(matid) ]
					if 'POSITION' in mat:
						x += mat['POSITION'][0]
						y += mat['POSITION'][1]
						z += mat['POSITION'][2]
					if 'SCALE' in mat:
						sx,sy,sz = mat['SCALE']

				for quad in f['indices']:
					for vidx in quad:
						if vidx==65000: continue
						i = vidx * 3
						arr[i] += x
						arr[i+1] += y
						arr[i+2] += z

						arr[i] *= sx
						arr[i+1] *= sy
						arr[i+2] *= sz

			vertices = np.array(arr, dtype=np.float32)
			glBufferData(GL_ARRAY_BUFFER, vertices, GL_STATIC_DRAW)			


		P = [1.3737387097273113,0.0,0.0,0.0,0.0, 1.8316516129697482,0.0,0.0,0.0,0.0, -1.02020202020202,-1.0,0.0,0.0,-2.0202020202020203,0.0];
		V = [1.0,0.0,0.0,0.0, 0.0,1.0,0.0,0.0, 0.0,0.0,1.0,0.0, 0.0,0.0,0.0,1.0];
		V[14] -= 3.0


		if self.projection:
			P = list(self.projection)
		else:
			view = QMatrix4x4()
			cx = math.sin(self.spin_side + math.radians(180) ) * self.cam_zoom
			cy = math.cos(self.spin_side + math.radians(180) ) * self.cam_zoom
			view.lookAt(
				#QVector3D(0,-5,0), # camera pos
				QVector3D(cx,cy,self.spin_up), # camera pos
				QVector3D(0,0,0),    # look at pos
				QVector3D(0,0,1),    # up vector
			)
			#print('view:', view)
			V = list(view.data())
			proj = QMatrix4x4()
			proj.perspective(45.0, self._width / self._height, 1.0, 100.0)
			#print('proj:', proj)
			#pv = proj * view
			P = list(proj.data())
			#print(P)

		#print(dir(self.program))  ## .programId() to get int ID
		#self.program.setUniformValueArray(0, np.array(P,dtype=np.float32))

		loc = self.prog.uniformLocation("P")
		#print('P loc:', loc)
		glUniformMatrix4fv(loc,1,GL_FALSE, np.array(P,dtype=np.float32))

		loc = self.prog.uniformLocation("V")
		#print('V loc:', loc)
		glUniformMatrix4fv(loc,1,GL_FALSE, np.array(V,dtype=np.float32))

		if USE_CPU_XFORM:
			loc = self.prog.uniformLocation("M")
			#print('M loc:', loc)
			#if 'POS' in ob:
			#M = ob['matrix']
			m = QMatrix4x4()
			x,y,z = ob['rotation']
			m.rotate(x, 1,0,0)  ## in degrees not radians
			m.rotate(y, 0,1,0)
			m.rotate(z, 0,0,1)

			x,y,z = ob['scale']
			m.scale(x,y,z)

			#x,y,z = ob['pos']
			#m.translate(x,y,z)
			M = m.data()
			glUniformMatrix4fv(loc,1,GL_FALSE, np.array(M,dtype=np.float32))
		else:
			loc = self.prog.uniformLocation("MP")
			#print('MP loc:', loc)
			glUniform3fv(loc,1,np.array([0,0,0],dtype=np.float32))

			loc = self.prog.uniformLocation("MS")
			#print('MS loc:', loc)
			glUniform3fv(loc,1,np.array(ob['scale'],dtype=np.float32))

			loc = self.prog.uniformLocation("MR")
			#print('MR loc:', loc)
			rot = [math.radians(r) for r in ob['rotation']]
			glUniform3fv(loc,1,np.array(rot,dtype=np.float32))

		loc = self.prog.uniformLocation("T")
		#print('T loc:', loc)

		self.prog.setAttributeBuffer("vp", gl.GL_FLOAT, 0,3)
		self.prog.enableAttributeArray("vp")


		#self.program.setAttributeBuffer("aPosition", gl.GL_FLOAT, 0, 2)
		#self.program.enableAttributeArray("aPosition")
		#glDrawArrays( GL_TRIANGLES, 0, len(ob['verts']) )  ## draws a triangle

		for matid in ob['faces']:
			f = ob['faces'][matid]
			if int(matid) < len(ob['materials']):
				r,g,b = ob['materials'][ int(matid) ]['color'][:3]
				glUniform3fv(loc, 1, np.array([r,g,b], dtype=np.float32))
			else:
				glUniform3fv(loc, 1, np.array(f['color'], dtype=np.float32))
			ibo = f['IBUFF']
			glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,ibo)
			glDrawElements(GL_TRIANGLES, len(f['INDICES']), GL_UNSIGNED_SHORT, None)

	def view_blender_object(self, name, blend):
		if not self.prog:
			self.prog = QOpenGLShaderProgram(self)
			if USE_CPU_XFORM:
				self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, libzader.VSHADER_CPU_XFORM)
			else:
				self.prog.addShaderFromSourceCode(
					QOpenGLShader.ShaderTypeBit.Vertex, 
					libzader.GLSL_XFORM + libzader.VSHADER_GPU_XFORM
				)

			self.prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, libzader.FSHADER)
			self.prog.link()
		self.prog.bind()

		if name not in self.buffers:
			cmd = [BLENDER, blend, '--background', '--python', __file__, '--', '--json=/tmp/__object__.json', '--dump=%s' % name]
			print(cmd)
			subprocess.check_call(cmd)
			ob = json.loads(open('/tmp/__object__.json').read())
			#print('got json:', ob)

			#if ob['camera']:  ## TODO, for now just rotate meshes on export
			#	self.projection = ob['camera']

			vbo = glGenBuffers(1)
			print('vbo:', vbo)
			glBindBuffer(GL_ARRAY_BUFFER, vbo)
			vertices = np.array(ob['verts'], dtype=np.float32)
			print('verts:', vertices)
			glBufferData(GL_ARRAY_BUFFER, vertices, GL_STATIC_DRAW)			
			#posloc = self.prog.attributeLocation("vp")
			#print('posloc:', posloc)
			#glVertexAttribPointer(posloc,3, GL_FLOAT, GL_FALSE, 0,None)
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
				indices = quads_to_tris(f['indices'])
				f['INDICES'] = np.array(indices,dtype=np.uint16)
				ibo = glGenBuffers(1)
				glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ibo)
				glBufferData(GL_ELEMENT_ARRAY_BUFFER, f['INDICES'], GL_STATIC_DRAW)
				f['IBUFF'] = ibo
				f['TRANS'] = [0,0,0]
				f['TRANS_PREV'] = tuple([0,0,0])


		self.active_object = name
		self.debug_draw=False
		self.update()  ## calls paintGL
		return self.buffers[name]

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
