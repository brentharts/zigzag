import os, sys, subprocess, atexit

_thisdir = os.path.split(os.path.abspath(__file__))[0]
zigzagpy = os.path.join(_thisdir, 'zigzag.py')

if sys.platform=='win32':
	UPBGE = 'upbge-0.36.1-windows-x86_64/blender.exe'
else:
	UPBGE = 'upbge-0.36.1-linux-x86_64/blender'


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



if sys.platform=='win32':
	try:
		import PySide6
	except:
		cmd=['python', '-m', 'pip', 'install', 
		#'PySide6'
		'PySide6-Essentials'
		]
		subprocess.check_call(cmd)

	from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
	from PySide6.QtCore import QTimer
elif sys.platform=='darwin':
	from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
	from PySide6.QtCore import QTimer
else:
	from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
	from PyQt6.QtCore import QTimer

class Window(QWidget):
	def thread(self):
		while self.proc:
			#print('waiting...')
			ln = self.proc.stdout.readline()
			#print(ln)
			if ln==b'':
				print('blender exit')
				break
			self.bstdout.append(ln)

	def clear_layout(self, layout):
		for i in reversed(range(layout.count())):
			widget = layout.itemAt(i).widget()
			if widget is not None: widget.setParent(None)

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
		self.clear_layout(self.sub_vbox)
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
	app = QApplication(sys.argv)
	window = Window()
	window.show()
	sys.exit( app.exec() )
