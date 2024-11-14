import os, sys, subprocess, atexit, string

_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
try:
	import libglzag
	print(libglzag)
except ModuleNotFoundError as err:
	print('WARN: failed to import libglzag')
	print(err)
	libglzag = None
zigzagpy = os.path.join(_thisdir, 'zigzag.py')

if sys.platform=='win32':
	UPBGE = 'upbge-0.36.1-windows-x86_64/blender.exe'
else:
	UPBGE = 'upbge-0.36.1-linux-x86_64/blender'

try:
	import OpenGL
except:
	print("warn PyOpenGL not installed")
	OpenGL = None

MEGASOLID = os.path.join(_thisdir,'pyqt6-rich-text-editor')
if MEGASOLID not in sys.path: sys.path.append(MEGASOLID)

def ensure_megasolid():
	if not os.path.isdir(MEGASOLID):
		cmd = 'git clone --depth 1 https://github.com/brentharts/pyqt6-rich-text-editor.git'
		print(cmd)
		subprocess.check_call(cmd.split())
ensure_megasolid()


if os.path.isdir(MEGASOLID):
	import codeeditor
	print(codeeditor)
	from codeeditor import MegasolidCodeEditor
else:
	codeeditor = None
	MegasolidCodeEditor = object


try:
	import matplotlib
	import matplotlib.pyplot as plt
except:
	plt = None
if plt: matplotlib.use('QtAgg')

try:
	import py7zr
except:
	py7zr = None

if sys.platform=='win32' or sys.platform=='darwin':
	try:
		import PySide6
	except:
		cmd=['python', '-m', 'pip', 'install', 
		#'PySide6'
		'PySide6-Essentials'
		]
		subprocess.check_call(cmd)

	from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
	from PySide6.QtCore import QTimer, Qt
	from PySide6.QtGui import (
		QFont,
		QImage,
		QTextDocument,
		QPixmap,
	)

else:
	from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
	from PyQt6.QtCore import QTimer, Qt
	from PyQt6 import QtCore, QtGui, QtWidgets

	from PyQt6.QtGui import (
		QFont,
		QImage,
		QTextDocument,
		QPixmap,
	)

def clear_layout(layout):
	for i in reversed(range(layout.count())):
		widget = layout.itemAt(i).widget()
		if widget is not None: widget.setParent(None)


class ZigZagEditor( MegasolidCodeEditor ):
	def reset(self):
		alt_widget = None
		if libglzag:
			self.glview = libglzag.Viewer(width=300,height=300)

			layout = QVBoxLayout()
			alt_widget = QWidget()
			alt_widget.setLayout(layout)
			layout.addWidget(self.glview)
			layout.addStretch(1)

			self.materials_layout = QVBoxLayout()
			layout.addLayout(self.materials_layout)

		else:
			self.glview = None
			self.materials_layout = None

		super(ZigZagEditor,self).reset(alt_widget=alt_widget)

		## cyrillic
		self._msyms = 'Ѐ Ё Ђ Ѓ Є Ї Љ Њ Ћ Ќ Ѝ Ў Џ Б Д Ж И Й Л Ф Ц Ш Щ Ъ Э Ю Я'.split()
		self.mat_syms = {}
		self.shared_materials = {}

		self.com_timer = QTimer()
		self.com_timer.timeout.connect(self.com_loop)
		self.com_timer.start(2000)

	def com_loop(self):
		txt = self.editor.toPlainText()
		updates = 0
		for ln in txt.splitlines():
			for name in self.mat_syms:
				sym = self.mat_syms[name]
				if ln.count(sym)==1:
					#print(ln)
					cmd = ln.split(sym)[-1]
					if cmd.startswith('.color') and cmd.count(',')==2:
						if '=' in cmd: clr = cmd.split('=')[-1].strip()
						else:  clr = cmd.split('.color')[-1].strip()
						if clr.startswith( ('[', '(', '{') ): clr=clr[1:]
						elif clr.endswith( (']', ')', '}') ): clr=clr[:-1]
						ok = False
						try:
							clr = [float(c.strip()) for c in clr.split(',')]
							ok = True
						except:
							pass
						if ok:
							assert name in self.shared_materials
							self.shared_materials[name]['color']=clr
							r,g,b = clr
							r = int(r*255)
							g = int(g*255)
							b = int(b*255)
							self.shared_materials[name]['WIDGET'].setStyleSheet('background-color:rgb(%s,%s,%s)' %(r,g,b))
							updates += 1
		if updates:
			self.glview.update()

	def material_sym(self, name):
		if name not in self.mat_syms:
			self.mat_syms[name] = self._msyms.pop()
		return self.mat_syms[name]

	def blend_to_qt(self, dump):
		layout = QVBoxLayout()
		container = QWidget()
		container.setLayout(layout)
		url = dump['URL']

		qsym = QLabel(self.blend_syms[url])
		qsym.setStyleSheet('font-size:64px; color:cyan;')
		layout.addWidget(qsym)

		a,b = os.path.split(url)
		btn = QPushButton('open: '+b)
		btn.setStyleSheet('background-color:gray; color:white')
		btn.clicked.connect(lambda : self.open_blend(url))
		layout.addWidget(btn)

		if url not in self.blend_previews:
			cmd = [codeeditor.BLENDER, url, '--background', '--python', __file__, '--', '--render=/tmp/__blend__.png']
			print(cmd)
			subprocess.check_call(cmd)
			q = QImage('/tmp/__blend__.png')
			qpix = QPixmap.fromImage(q)
			self.blend_previews[url]=qpix

		qlab = QLabel()
		qlab.setPixmap(self.blend_previews[url])
		layout.addWidget(qlab)


		layout.addStretch(1)

		for name in dump['objects']:
			box = QHBoxLayout()
			layout.addLayout(box)
			btn = QPushButton(name)
			btn.setCheckable(True)
			if name in dump['selected']:
				btn.setChecked(True)

			btn.toggled.connect(
				lambda x,n=name: self.toggle_blend_object(x,n, dump)
			)
			box.addWidget(btn)
			pos = [str(round(v,1)) for v in dump['objects'][name]['pos']]
			box.addWidget(QLabel(','.join(pos)))
			box.addStretch(1)
			if name in dump['meshes']:
				#btn = QPushButton('🮶')  ## no font for this on Windows :(
				btn = QPushButton('▶')
				btn.setFixedWidth(32)
				box.addWidget(btn)
				btn.clicked.connect(
					lambda e,n=name: self.view_blender_object(n, url)
				)

		return container

	def view_blender_object(self, obname, blend):
		print('view_blender_object:', obname, blend)
		if self.glview:
			info = self.glview.view_blender_object(obname, blend)
			clear_layout(self.materials_layout)
			for mat in info['materials']:
				print(mat)
				self.shared_materials[mat['name']] = mat

				box = QHBoxLayout()
				con = QWidget()
				con.setLayout(box)
				mat['WIDGET'] = con
				self.materials_layout.addWidget(con)
				box.addWidget(QLabel(mat['name']))

				if 'class' in mat:
					btn = QPushButton(mat['class'])
					box.addWidget(btn)

				box.addStretch(1)

				msym = self.material_sym(mat['name'])
				btn = QPushButton( msym )
				box.addWidget(btn)
				btn.clicked.connect(lambda a,s=msym: self.insert_material(s))

				r,g,b,a = mat['color']
				brightness = (r+g+b)/3
				r = int(r*255)
				g = int(g*255)
				b = int(b*255)
				if brightness > 0.8:
					con.setStyleSheet('background-color:rgb(%s,%s,%s); color:black' % (r,g,b))
				else:
					con.setStyleSheet('background-color:rgb(%s,%s,%s)' % (r,g,b))

	def insert_material(self, sym):
		#https://doc.qt.io/qt-6/richtext-html-subset.html
		##tt = Typewrite font (same as <code>)
		cur = self.editor.textCursor()
		cur.insertHtml('<tt style="background-color:red; font-size:32px">%s</tt>' % sym)


	def load_blends(self, blends):
		user_vars = list(string.ascii_letters)
		user_vars.reverse()
		cur = self.editor.textCursor()
		for blend in blends:
			cur.insertText('%s = ' % user_vars.pop())
			self.on_new_blend(blend)
			cur.insertText('\n')


class Window(QWidget):
	def open_code_editor(self, *args):
		#window = codeeditor.MegasolidCodeEditor()
		#window.reset(alt_widget=QLabel('hello world'))
		window = ZigZagEditor()
		window.reset()
		window.show()
		self.megasolid = window

	def blendgen(self, sym):
		blender = self.blenders[-1]
		if sys.platform=='win32':
			out = 'C:\\tmp\\%s.blend' % sym
		else:
			out = '/tmp/%s.blend' % sym
		cmd = [blender, '--background', '--python-exit-code', '1', '--python', os.path.join(_thisdir,'libgenzag.py'), '--', '--generate=%s' % sym, '--out='+out]
		print(cmd)
		subprocess.check_call(cmd)

		window = ZigZagEditor()
		window.reset()
		window.load_blends([out])
		window.show()
		self.megasolid = window


	def thread(self):
		while self.proc:
			#print('waiting...')
			ln = self.proc.stdout.readline()
			#print(ln)
			if ln==b'':
				print('blender exit')
				break
			self.bstdout.append(ln)


	def loop(self):
		#if self.bstdout:
		#	if self.sub_vbox.count() > 64:
		#		self.clear_layout(self.sub_vbox)
		for ln in self.bstdout:
			ln = ln.decode('utf-8')
			if not ln.strip(): continue
			ln = ln.rstrip()
			if len(ln) > 80: ln = ln[:80] + '...'

			if self.sub_vbox.count() > 20:
				wid=self.sub_vbox.itemAt(1).widget()
				#self.sub_vbox.removeItem(wid)
				if wid:
					self.sub_vbox.removeWidget(wid)
					wid.setParent(None)
					wid.deleteLater()

			self.sub_vbox.addWidget(QLabel(ln))
		self.bstdout = []

	def run_blender(self):
		if self.tests_frame: self.tests_frame.hide()
		clear_layout(self.sub_vbox)
		self.move(10,64)  ## not working on linux?
		cmd = [self.blenders[-1]]
		for arg in sys.argv:
			if arg.endswith('.blend'):
				cmd.append(arg)
				break
		cmd +=['--window-geometry','640','100', '800','800', '--python-exit-code', '1', '--python', zigzagpy]
		exargs = []
		for arg in sys.argv:
			if arg.startswith('--'):
				exargs.append(arg)
		#if exargs:
		cmd.append('--')
		cmd += exargs
		cmd.append('--pipe')
		print(cmd)
		self.sub_vbox.addWidget(QLabel(cmd[0]))
		#subprocess.check_call(cmd)
		if self.proc:
			self.proc.kill()
			self.proc = None
		self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
		atexit.register(lambda:self.proc.kill())
		import threading
		threading._start_new_thread(self.thread, tuple([]))
		#self.thread()

	def run_test(self, name):
		plot = {}
		for lang in 'zig c3 rust'.split():
			if sys.platform=='win32' and lang=='rust': continue
			engine = lang+'zag.py'
			assert os.path.isfile(engine)
			cmd = [self.blenders[-1], '--background', '--python', engine, '--', '--test='+name]
			print(cmd)
			subprocess.check_call(cmd)

			wasm = '/tmp/%s_%s.wasm' % (lang, name)
			info = {
				'wasm' : len(open(wasm,'rb').read()),
				'html' : len( open('%s_%s.html'%(lang,name),'rb').read() ),
			}
			wopt = '/tmp/%s_%s.opt.wasm' % (lang, name)
			if os.path.isfile(wopt):
				info['wasm-opt'] = len(open(wopt,'rb').read())
			else:
				wopt = '/tmp/%s_%s.strip.opt.wasm' % (lang, name)
				if os.path.isfile(wopt):
					info['wasm-opt'] = len(open(wopt,'rb').read())
			plot[lang] = info

		print(plot)
		names = []
		values = []
		colors = []
		cmap = {'zig':'cyan', 'rust':'pink', 'c3':'orange'}
		for lang in plot:
			for ftype in plot[lang]:
				if lang=='rust' and ftype=='wasm': continue
				names.append('%s %s' % (lang, ftype))
				values.append(plot[lang][ftype])
				colors.append(cmap[lang])

		fig, ax = plt.subplots()
		ax.set_ylabel('bytes')
		ax.bar(names, values, color=colors)
		plt.show()

	def run_install(self, name, btn=None):
		if sys.platform=='linux':
			cmd = ['sudo', 'apt-get', 'install', 'python3-%s' %name]
			print(cmd)
			subprocess.check_call(cmd)
		else:
			py = 'python3'
			if sys.platform=='win32': py = 'python'
			cmd = [py, '-m', 'pip', 'install', name]
			print(cmd)
			subprocess.check_call(cmd)
		if btn: btn.hide()

	def install_upbge(self, btn=None):
		if sys.platform=='linux':
			if btn:
				btn.setText('installing...')
				btn.repaint()

			xz = 'https://github.com/UPBGE/upbge/releases/download/v0.36.1/upbge-0.36.1-linux-x86_64.tar.xz'
			if not os.path.isfile('upbge-0.36.1-linux-x86_64.tar.xz'):
				cmd = 'curl -L -o upbge-0.36.1-linux-x86_64.tar.xz %s' % xz
				print(cmd)
				subprocess.check_call(cmd.split())
			cmd = 'tar -xvf upbge-0.36.1-linux-x86_64.tar.xz'
			print(cmd)
			subprocess.check_call(cmd.split())
			if btn: btn.hide()

		elif sys.platform=='win32':
			if btn:
				btn.setText('installing...')
				btn.repaint()
			z = 'https://github.com/UPBGE/upbge/releases/download/v0.36.1/upbge-0.36.1-windows-x86_64.7z'
			if not os.path.isfile('upbge-0.36.1-windows-x86_64.7z'):
				cmd = 'curl -L -o upbge-0.36.1-windows-x86_64.7z %s' % z
				print(cmd)
				subprocess.check_call(cmd.split())

			with py7zr.SevenZipFile('upbge-0.36.1-windows-x86_64.7z', 'r') as archive:
				archive.extractall()

			if btn: btn.hide()

		else:
			webbrowser.open('https://upbge.org/#/download')


	def open_folder(self, path):
		if sys.platform=='win32':
			os.startfile(os.path.normpath(path))
		else:
			subprocess.check_call(['xdg-open', path])


	def __init__(self):
		super().__init__()
		self.setStyleSheet('background-color:rgb(42,42,42); color:lightgrey')

		self.bstdout = []
		self.timer = QTimer()
		self.timer.timeout.connect(self.loop)
		self.timer.start(100)
		self.proc = None
		self.blenders = []
		self.resize(250, 150)
		self.setWindowTitle('ZigZag')
		self.main_vbox = vbox = QVBoxLayout()

		self.tools = QHBoxLayout()
		vbox.addLayout(self.tools)

		if '--dev' in sys.argv:
			btn = QPushButton("/tmp")
			btn.clicked.connect(lambda:self.open_folder('/tmp') )
			self.tools.addWidget(btn)

		btn = QPushButton("🖹")
		btn.clicked.connect(self.open_code_editor)
		self.tools.addWidget(btn)

		btn = QPushButton("🐵")  ## monkey
		btn.clicked.connect( lambda: self.blendgen("🐵") )
		self.tools.addWidget(btn)

		btn = QPushButton("🐱")  ## cat
		btn.clicked.connect( lambda: self.blendgen("🐱") )
		self.tools.addWidget(btn)

		self.tools.addStretch(1)

		self.sub_vbox = vbox = QVBoxLayout()
		self.main_vbox.addLayout(vbox)

		self.tests_hbox = None

		if plt:
			self.tests_frame = QFrame()
			hbox = QHBoxLayout()
			self.tests_frame.setLayout(hbox)
			hbox.addWidget(QLabel('Plot WASM size tests:'))
			hbox.addStretch(1)
			#vbox.addLayout(hbox)
			vbox.addWidget(self.tests_frame)
			btn = QPushButton("test1")
			btn.clicked.connect(lambda : self.run_test("test1"))
			hbox.addWidget(btn)
		else:
			btn = QPushButton('install matplotlib')
			btn.clicked.connect(lambda b=btn:self.run_install('matplotlib',b))
			vbox.addWidget(btn)

		if not py7zr:
			btn = QPushButton('install py7zr')
			btn.clicked.connect(lambda b=btn:self.run_install('py7zr',b))
			vbox.addWidget(btn)

		if not OpenGL:
			btn = QPushButton('install pyopengl')
			btn.clicked.connect(lambda b=btn:self.run_install('pyopengl',b))
			vbox.addWidget(btn)

		if not os.path.isfile(UPBGE):
			btn = QPushButton('install UPBGE')
			btn.clicked.connect(lambda b=btn:self.install_upbge(b))
			vbox.addWidget(btn)

		vbox.addWidget(QLabel('Blender Versions:'))

		if sys.platform=='win32':
			pfiles = 'C:\\Program Files\\Blender Foundation'
			if os.path.isdir(pfiles):
				files = os.listdir(pfiles)
				files.sort()
				for name in files:
					if 'Blender' in name:
						bpath = os.path.join(pfiles,name)
						print(os.listdir(bpath))
						if 'blender.exe' in os.listdir(bpath):
							b=os.path.join(bpath,'blender.exe')
							self.blenders.append(b)
							vbox.addWidget(QLabel(b))
			if not self.blenders:
				vbox.addWidget(QLabel('ERROR: blender not installed'))
		else:
			pfiles = os.path.expanduser('~/Downloads')
			if os.path.isdir(pfiles):
				files = os.listdir(pfiles)
				files.sort()
				for name in files:
					if 'blender' in name:
						bpath = os.path.join(pfiles,name)
						if os.path.isdir(bpath):
							if 'blender' in os.listdir(bpath):
								b=os.path.join(bpath,'blender')
								self.blenders.append(b)
								vbox.addWidget(QLabel(b))
						else:
							#vbox.addWidget(QLabel(bpath))
							pass
			if not self.blenders:
				for bpath in '/usr/bin/blender /usr/local/bin/blender /Applications/Blender.app/Contents/MacOS/Blender'.split():
					if os.path.isfile(bpath):
						vbox.addWidget(QLabel(bpath))
						self.blenders.append(bpath)

		if os.path.isfile(UPBGE):
			vbox.addWidget(QLabel(os.path.abspath(UPBGE)))
			self.blenders.append(UPBGE)


		self.main_vbox.addStretch(1)

		button_ok = QPushButton("OK")
		button_ok.clicked.connect(self.run_blender)
		button_cancel = QPushButton("Cancel")
		button_cancel.clicked.connect(sys.exit)

		hbox = QHBoxLayout()
		hbox.addStretch(1)
		hbox.addWidget(button_ok)
		hbox.addWidget(button_cancel)

		self.main_vbox.addLayout(hbox)

		# Add vertical layout to window
		self.setLayout(self.main_vbox)

def main():
	QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit( app.exec() )


if __name__=='__main__':
	blends = []
	for arg in sys.argv:
		if arg.endswith('.blend'):
			blends.append(arg)

	if blends:
		QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
		app = QApplication(sys.argv)
		app.setApplicationName("Megasolid ZigZag")
		window = ZigZagEditor()
		window.reset()

		window.load_blends( blends )
		app.exec()


	elif '--megasolid' in sys.argv:
		app = QApplication(sys.argv)
		app.setApplicationName("Megasolid ZigZag")
		window = codeeditor.MegasolidCodeEditor()
		window.reset()
		app.exec()
	else:
		main()

