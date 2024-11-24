#!/usr/bin/env python3
import os, sys
from random import choice

if sys.platform=='win32' or sys.platform=='darwin':
	from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QToolTip, QLineEdit, QSlider, QSizePolicy, QLayout, QTextEdit
	from PySide6.QtCore import QTimer, Qt, QSize
	from PySide6.QtGui import (
		QFont,
		QImage,
		QTextDocument,
		QPixmap,
		QAction,
		QIcon,
	)
else:
	from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame, QToolTip, QLineEdit, QSlider, QSizePolicy, QLayout, QTextEdit
	from PyQt6.QtCore import QTimer, Qt, QSize
	from PyQt6 import QtCore, QtGui, QtWidgets

	from PyQt6.QtGui import (
		QFont,
		QImage,
		QTextDocument,
		QPixmap,
		QAction,
		QIcon,
	)

_thisdir = os.path.split(os.path.abspath(__file__))[0]
C3_LEARN = os.path.join(_thisdir,'c3-learn')
def ensure_c3_learn():
	if not os.path.isdir(C3_LEARN):
		cmd = 'git clone --depth 1 https://github.com/brentharts/c3-learn.git'
		print(cmd)
		subprocess.check_call(cmd.split())
ensure_c3_learn()

def clear_layout(layout):
	for i in reversed(range(layout.count())):
		widget = layout.itemAt(i).widget()
		if widget is not None: widget.setParent(None)



class LearnC3(QWidget):
	def __init__(self, zoomout=0):
		super().__init__()
		self.zoomout = zoomout
		self.resize(640, 700)
		self.setWindowTitle('Learn C3')
		self.main_vbox = vbox = QVBoxLayout()
		self.setLayout(self.main_vbox)
		self.mds = []
		path = os.path.join(C3_LEARN, 'old/content/Basics')
		for md in os.listdir(path):
			if md.endswith('.md'):
				self.mds.append( os.path.join(path, md) )
		path = os.path.join(C3_LEARN, 'old/content/More')
		for md in os.listdir(path):
			if md.endswith('.md'):
				self.mds.append( os.path.join(path, md) )
		path = os.path.join(C3_LEARN, 'old/content/Try')
		for md in os.listdir(path):
			if md.endswith('.md'):
				self.mds.append( os.path.join(path, md) )

		self.load_random()
		self.show()

	def load_random(self):
		clear_layout(self.main_vbox)
		md = choice(self.mds)
		print('loading:', md)
		self.setWindowTitle(md)
		md = open(md).read()
		html = self.parse_md(md)
		self.edit = edit = QTextEdit()
		edit.setHtml(html)
		if self.zoomout:
			edit.zoomOut(self.zoomout)
		self.main_vbox.addWidget(edit)

		btn = QPushButton('next', self.edit)
		btn.clicked.connect(lambda b: self.load_random())

	def load(self, tag):
		tag = os.path.sep + tag
		clear_layout(self.main_vbox)
		ok = None
		for md in self.mds:
			if md.endswith(tag):
				ok = md
				break
		if ok:
			self.setWindowTitle(md)
			md = open(md).read()
			html = self.parse_md(md)
			self.edit = edit = QTextEdit()
			edit.setHtml(html)
			if self.zoomout:
				edit.zoomOut(self.zoomout)
			self.main_vbox.addWidget(edit)

			btn = QPushButton('next', self.edit)
			btn.clicked.connect(lambda b: self.load_random())

	def parse_md(self, md):
		o = []
		in_backticks = False
		for ln in md.splitlines():
			print(ln)
			if ln.startswith('title:'):
				title = ln.split('title:')[-1].strip()
				o.append('<h2>Example: %s</h2>' % title)
				continue
			elif ln.strip()=='---':
				o.append('<hr/>')
				continue
			elif ln.strip()=='```':
				if in_backticks:
					in_backticks = False
					o.append('</pre>')
				else:
					in_backticks = True
					o.append('<pre style="background-color:lightgray">')
				continue
			elif ln.startswith('- '):
				o.append('<span style="font-size:18px">•%s</span>' % ln)
				continue
			elif ln.startswith('weight:'):
				continue
			elif ln.startswith('{{<start>}}'):
				continue
			elif ln.startswith('{{<end'):
				n = int(ln.split('{{<end')[-1].split('>')[0])
				html = os.path.join(C3_LEARN, 'old/layouts/shortcodes/end%s.html' % n)
				assert os.path.isfile(html)
				for hl in open(html).read().splitlines():
					if hl.strip().startswith('let defcod'):
						code = hl[ hl.index('=')+1 : ].strip()
						code = code.replace('\\t', '\t').replace('\\n', '\n')
						if code.startswith('"') and code.endswith('";'):
							code = code[1:-2]
						code = code.replace('\\"', '"')
						code = code.replace('<', '&lt;').replace('>', '&gt;')
						o.append('<h3>C3 Code:</h3><pre>%s</pre>' % code)
				continue
			if in_backticks and ln.startswith('//'):
				o.append('<i style="font-size:16px; background-color:gray; color:white">%s</i>' % ln)
			elif in_backticks and ln.count('//')==1:
				a,b = ln.split('//')
				o.append('%s\t\t<i style="font-size:12px; background-color:gray; color:white">//%s</i>' % (a,b))
			else:
				o.append(ln)
		return '<br/>'.join(o)

if __name__=='__main__':
		app = QApplication(sys.argv)
		window = LearnC3()
		sys.exit( app.exec() )
