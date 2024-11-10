import os, sys, json, subprocess

def mesh_to_json(ob):
	verts = []
	faces = []
	dump = {
		'verts':verts,
		'faces':faces,
	}
	for v in ob.data.vertices:
		verts += list(v.co)
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
from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_FLOAT, GL_TRIANGLES, glClear, glClearColor, glDrawArrays

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

class Viewer(QOpenGLWidget):
	def __init__(self, width=256, height=256):
		super().__init__()
		self.setFixedSize(width, height)
		print('new gl viewer', self)

	def initializeGL(self):
		print('init gl')
		glClearColor(1, 0.5, 0.1, 1)

		vertShaderSrc = """
			attribute vec2 aPosition;
			void main()
			{
				gl_Position = vec4(aPosition, 0.0, 1.0);
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

		vertPositions = np.array([
			-0.5, -0.5,
			0.5, -0.5,
			0, 0.5], dtype=np.float32)
		self.vertPosBuffer = QOpenGLBuffer()
		self.vertPosBuffer.create()
		self.vertPosBuffer.bind()
		self.vertPosBuffer.allocate(vertPositions, len(vertPositions) * 4)

	def resizeGL(self, w, h):
		pass

	def paintGL(self):
		print('gl redraw')
		glClear(GL_COLOR_BUFFER_BIT)
		self.program.bind()
		self.vertPosBuffer.bind()
		self.program.setAttributeBuffer("aPosition", GL_FLOAT, 0, 2)
		self.program.enableAttributeArray("aPosition")
		glDrawArrays(GL_TRIANGLES, 0, 3)


	def view_blender_object(self, name, blend):
		cmd = [BLENDER, blend, '--background', '--python', __file__, '--', '--json=/tmp/__object__.json', '--dump=%s' % name]
		print(cmd)
		subprocess.check_call(cmd)
		ob = json.loads(open('/tmp/__object__.json').read())
		print('got json:', ob)


if __name__ == "__main__":
	QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
	app = QApplication(sys.argv)
	w = Viewer()
	for arg in sys.argv:
		if arg.endswith('.blend'):
			w.view_blender_object('Cube', arg)
	w.show()
	sys.exit(app.exec())
