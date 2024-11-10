import sys
import numpy as np
from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_FLOAT, GL_TRIANGLES, glClear, glClearColor, glDrawArrays
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

if __name__ == "__main__":
	QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
	app = QApplication(sys.argv)
	w = OpenGLWindow()
	w.show()
	sys.exit(app.exec())