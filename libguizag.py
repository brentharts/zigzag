import os, sys, subprocess, atexit, string, math, hashlib
import xml.dom.minidom
from random import random, uniform, choice
_thisdir = os.path.split(os.path.abspath(__file__))[0]
if _thisdir not in sys.path: sys.path.insert(0,_thisdir)
try:
	import libglzag
	print(libglzag)
except ModuleNotFoundError as err:
	print('WARN: failed to import libglzag')
	print(err)
	libglzag = None

rustzagpy = os.path.join(_thisdir, 'rustzag.py')
zigzagpy = os.path.join(_thisdir, 'zigzag.py')
c3zagpy = os.path.join(_thisdir, 'c3zag.py')

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

import learn_c3

if sys.platform == 'win32':
	C3 = os.path.join(_thisdir,'c3/c3c.exe')  ## latest unstable
	if not os.path.isfile(C3): C3 = os.path.abspath('./c3-windows-Release/c3c.exe')
	ZIG = os.path.join(_thisdir, 'zig-windows-x86_64-0.13.0/zig.exe')
elif sys.platform == 'darwin':
	C3 = os.path.abspath('./c3/c3c')
	ZIG = os.path.join(_thisdir, 'zig-macos-aarch64-0.13.0/zig')
else:
	C3 = os.path.abspath('./c3/c3c')
	ZIG = os.path.join(_thisdir, 'zig-linux-x86_64-0.13.0/zig')

if not os.path.isfile(C3):
	print("WARN: C3 compiler not installed")
	C3 = None
if not os.path.isfile(ZIG):
	print("WARN: ZIG compiler not installed")
	ZIG = None

def clear_layout(layout):
	for i in reversed(range(layout.count())):
		widget = layout.itemAt(i).widget()
		if widget is not None: widget.setParent(None)

class ClickLabel(QLabel):
	def mousePressEvent(self, ev):
		self.onclicked(ev)
class ObjectPopup(QWidget):
	def mousePressEvent(self, ev):
		self.hide()


C3_EXTERNS = '''
extern fn float js_sin(float a);
extern fn float js_cos(float a);
extern fn float js_rand();
extern fn int   js_eval(char*ptr);
'''

ZIG_EXTERNS = '''
extern fn js_rand() f32;
extern fn js_sin(a:f32) f32;
extern fn js_cos(a:f32) f32;
extern fn js_eval(c:[*:0] const u8) void;
'''

class ZigZagEditor( MegasolidCodeEditor ):
	LATIN = tuple([chr(i) for i in range(192, 420)])  #À to ƣ
	CYRILLIC = tuple('Ѐ Ё Ђ Ѓ Є Ї Љ Њ Ћ Ќ Ѝ Ў Џ Б Д Ж И Й Л Ф Ц Ш Щ Ъ Э Ю Я'.split())

	def close(self):
		self._parent.show()
		super().close()

	def update_title(self):
		self.setWindowTitle("%s - ZigZag" % (os.path.basename(self.path) if self.path else "Untitled"))

	def debug_chat(self, msg):
		if not self._debug_chat:
			self._debug_chat_bubble = lab = ClickLabel('🗨', self.glview)
			lab.onclicked=lambda e:lab.hide()
			lab.setStyleSheet('font-size:128px; background-color:rgba(0,0,0,0)')
			self._debug_chat = chat = QLabel('', lab)
			chat.setStyleSheet('font-size:20px; color:black')
			chat.move(16,66)
		if len(msg) > 32:
			msg = msg[:30] + '...'
		self._debug_chat.setText(msg)
		self._debug_chat.adjustSize()
		self._debug_chat_bubble.show()

	def hide_debug_chat(self):
		if self._debug_chat:
			self._debug_chat_bubble.hide()

	def reset(self, parent=None, use_learn_c3=True, use_learn_zig=False):
		self._c3_errors = {}
		self._zig_errors = {}
		self.c3_funcs = {}
		self.zig_funcs = {}
		self._parent=parent
		alt_widget = None
		self._debug_chat = None
		self._show_learn_c3 = True
		self.learn_c3_widget = self.learn_zig_widget = None
		if libglzag:
			self.glview = libglzag.Viewer(width=300,height=300)

			layout = QVBoxLayout()
			#layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

			alt_widget = QWidget()
			alt_widget.setLayout(layout)
			layout.addWidget(self.glview)
			#layout.addStretch(1)

			self.materials_layout = QVBoxLayout()
			## https://stackoverflow.com/questions/28660960/resize-qmainwindow-to-minimal-size-after-content-of-layout-changes
			#self.materials_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
			self.materials_container = QWidget()
			#self.materials_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
			self.materials_container.setLayout(self.materials_layout)
			layout.addWidget(self.materials_container)
			#layout.addLayout(self.materials_layout)

			if use_learn_c3:
				self.learn_c3_widget = learn_c3.LearnC3(zoomout=3)
				self.learn_c3_widget.setStyleSheet('background-color:white; color:black')
				layout.addWidget(self.learn_c3_widget)
			if use_learn_zig:
				self.learn_zig_widget = LearnZig()
				self.learn_zig_widget.setStyleSheet('background-color:white; color:black')
				layout.addWidget(self.learn_zig_widget)

		else:
			self.glview = None
			self.materials_layout = None

		width = 900
		if sys.platform=='linux': 
			width = 1150
		super(ZigZagEditor,self).reset(width=width, alt_widget=alt_widget)

		self.on_syntax_highlight_post = self.__syntax_highlight_post

		## cyrillic
		self._msyms = list(self.CYRILLIC)
		self.mat_syms = {}
		self.shared_materials = {}
		## latin: 
		self._osyms = list(self.LATIN)
		self.ob_syms = {}

		self.ob_syms_blends = {}
		self.mat_syms_blends = {}

		self.com_timer = QTimer()
		self.com_timer.timeout.connect(self.com_loop)
		self.com_timer.start(2000)

		self.active_object = None
		self.active_blend = None
		self.anim_timer = QTimer()
		self.anim_timer.timeout.connect(self.anim_loop)
		self.anim_timer.start(30)

		for sym in self._msyms + self._osyms:
			self.extra_syms[sym] = True

		self.editor.setCursorWidth(8)
		self.editor.zoomIn(4)

		self.popup = pop = ClickLabel(self)
		pop.setText("hello popup")
		pop.setStyleSheet('background-color:black; color:lightgreen; font-size:28px')
		pop.move(400,50)
		#pop.show()
		pop.onclicked = lambda evt: pop.hide()
		self._prev_err = None
		self._prev_test = None

		self.ob_popup = wid = ObjectPopup(self)
		wid.move(200,200)
		wid.resize(300, 80)
		wid.setStyleSheet('background-color:rgba(128,128,128,0.25); color: black')
		self.ob_popup_layout = layout = QHBoxLayout()
		wid.setLayout(layout)
		layout.addWidget(QLabel('hello object popup'))

		act = QAction("export", self)
		act.setToolTip("export html file")
		act.setStatusTip("export html (WEBGL+WASM) saves zigzag-preview.html to ~/Desktop")
		act.setShortcut("F10")
		act.triggered.connect( self.export_html )
		self.format_toolbar.addAction(act)

		spacer = QWidget()
		spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		self.format_toolbar.addWidget(spacer)

		self._is_fs = False  ## this is only required on Linux/Wayland?
		self.setFullscreen = QAction("❖", self)
		self.setFullscreen.setShortcut("F11")
		self.setFullscreen.setToolTip('toggle fullscreen mode')
		self.setFullscreen.setStatusTip("Change to fullscreen mode")
		self.setFullscreen.triggered.connect(self.toggle_fs)
		self.format_toolbar.addAction(self.setFullscreen)

		self.help_button = QPushButton("?")
		self.help_button.setFixedWidth(32)
		self.help_button.setToolTip('show/hide help')
		self.help_button.clicked.connect(self.toggle_help)
		self.format_toolbar.addWidget(self.help_button)


		self.exit_button = QPushButton("✖")
		self.exit_button.setToolTip('close window')
		self.exit_button.clicked.connect(lambda:self.close())
		self.format_toolbar.addWidget(self.exit_button)

	def toggle_help(self):
		if self._show_learn_c3:
			self.learn_c3_widget.hide()
			self._show_learn_c3 = False
		else:
			self._show_learn_c3 = True
			self.learn_c3_widget.show()

	def toggle_fs(self):
		if self.isFullScreen() or (sys.platform=='linux' and self._is_fs):
			self.editor.zoomOut(8)
			#self.exit_button.hide()
			self._is_fs = False

			self.popup.move(400,50)

			if self.glview:
				self.glview.setFixedWidth(300)
				self.glview.setFixedHeight(300)

			if self.active_object:
				self.update_active_materials()

			#self.adjustSize()
			#self.setGeometry(50,50,800,400)
			#print(dir(self))
			self.showNormal()
			## https://stackoverflow.com/questions/28660960/resize-qmainwindow-to-minimal-size-after-content-of-layout-changes
			for i in range(0, 10):
				QApplication.processEvents()
			#self.resize(self.minimumSizeHint())
			self.resize(1000,400)
			if sys.platform=='linux':
				self.resize(1150,600)
			else:
				self.resize(900,600)

		else:
			self.popup.move(400,350)
			self.editor.zoomIn(8)
			self.exit_button.show()
			self.showFullScreen()
			self._is_fs = True
			if self.glview:
				self.glview.setFixedWidth(700)
				self.glview.setFixedHeight(500)
			self.update_active_materials()

	def clear_object_popup(self):
		clear_layout(self.ob_popup_layout)
		return self.ob_popup_layout

	def _anim_loop(self):
		if not self.active_object: return
		ob = self.active_object
		needs_update = False
		for matid in ob['faces']:
			f = ob['faces'][matid]
			if int(matid) < len(ob['materials']):
				mat = ob['materials'][ int(matid) ]
				if 'class' in mat and mat['class'] != 'NONE':
					#print('animation class:', mat['class'])
					if mat['class']=='LOWER_LIP':
						if random() < 0.06:
							f['TRANS'][2] = (random()-0.25)*0.1
							needs_update = True
					if mat['class']=='EYES':
						if random() < 0.03:
							ob['EYES_X'] = (random()-0.5)*0.05
							ob['EYES_Y'] = (random()-0.5)*0.01
							f['TRANS'][0] = ob['EYES_X']
							f['TRANS'][2] = ob['EYES_Y']
							needs_update = True
					if mat['class']=='UPPER_EYELID':
						if random() < 0.06 or needs_update:
							f['TRANS'][0] = ob['EYES_X'] * 0.2
							f['TRANS'][2] = ((random()-0.7) * 0.07) + (ob['EYES_Y']*0.2)
							needs_update = True
					if mat['class']=='LOWER_EYELID':
						if needs_update:
							f['TRANS'][0] = ob['EYES_X'] * 0.25
							f['TRANS'][2] = ((random()-0.35) * 0.07) + (ob['EYES_Y']*0.4)

		if needs_update:
			self.glview.update()

	def anim_loop(self):
		try:
			self._anim_loop()
		except KeyboardInterrupt:
			print('Ctrl+C exit')
			sys.exit()


	def parse_zig(self, zig, world_script=None):
		if not ZIG: return
		if zig == self._prev_test: return
		self._prev_test = zig

		header = ZIG_EXTERNS
		if world_script:
			header += world_script
		header_lines = len(header.splitlines())

		tmp = '/tmp/__tmp__.zig'
		open(tmp,'wb').write( (header + zig).encode('utf-8'))
		cmd = [
			ZIG, 
			'ast-check',
			tmp
		]
		print(cmd)
		res = subprocess.run(cmd, capture_output=True, text=True)
		#print(res)
		if res.returncode != 0:
			print('ZIG COMPILE ERROR!')
			print(res.stdout)
			print(res.stderr)
			self.parse_zig_error(res.stderr + res.stdout, line_offset=header_lines)
		else:
			self.popup.setText('ZIG COMPILE 🆗')
			self.popup.adjustSize()

	def parse_zig_error(self, err, line_offset=0):
		o = []
		errors_raw = []
		for ln in err.splitlines():
			if '__tmp__.zig:':
				ln = ln.split('__tmp__.zig:')[-1]
				if ln.count(': error:')==1:
					e = ln.split(': error:')[-1]
					ln = '<b>Error:</b>' + e
					errors_raw.append(ln)
			o.append(ln)
		if self._prev_err != err:
			self._prev_err = err
			msg = '<br/>'.join(o)
			self.popup.setStyleSheet('background-color:black; color:lightgreen; font-size:28px')
			self.popup.setText(msg)
			self.popup.adjustSize()
			self.popup.show()
			if err not in self._zig_errors:
				self.zig_search_for_help(err, errors_raw)

	def zig_search_for_help(self, err, error_messages):
		print('zig help search:', error_messages)
		help = {}
		self._zig_errors[err] = help
		a = ' '.join(error_messages).lower()
		title = self.learn_zig_widget.search(a)
		if title:
			help[title]=a
		else:
			print('WARN: no search results')


	def check_c3(self, c3):
		for ln in c3.splitlines():
			ln = ln.strip()
			if ln.startswith('fn '):
				ln = ln[3:].strip()
				if '(' in ln:
					a = ln.split('(')[0].strip()
					if len(a.split()) == 2:
						rtype, fname = a.split()
						if fname not in self.c3_funcs:
							self.c3_funcs[fname] = rtype
							self.debug_chat('new function:\n'+fname)


	def parse_c3(self, c3, world_script=None):
		if not C3: return -2
		if c3 == self._prev_test: return -1
		self._prev_test = c3

		tmp = '/tmp/__tmp__.c3'
		header = C3_EXTERNS
		if world_script:
			header += world_script
		header_lines = len(header.splitlines())
		open(tmp,'wb').write( (header+c3).encode('utf-8'))
		cmd = [
			C3, 
			#'-E', ## lex only
			#'-P', ## parse and output json
			'-C', ## lex parse check
			'compile',
			tmp
		]
		print(cmd)
		res = subprocess.run(cmd, capture_output=True, text=True)
		#print(res)
		if res.returncode != 0:
			print('C3 COMPILE ERROR!')
			print(res.stdout)  ## this should be nothing?
			print(res.stderr)  ## error message from c3c
			self.parse_c3_error(res.stderr + res.stdout, line_offset=header_lines)
			return 0
		else:
			self.popup.setText('C3 COMPILE 🆗')
			self.popup.adjustSize()
			self.hide_debug_chat()
			return 1

	def parse_c3_error(self, err, line_offset=0):
		error_lines = []
		error_messages = []
		paren_messages = []
		errors_raw = []
		for ln in err.splitlines():
			if ':' in ln and ln.split(':')[0].strip().isdigit():
				lineno = int(ln.split(':')[0].strip())
				if lineno - line_offset <= 0:
					continue
				ln = '%s :%s' % (lineno-line_offset, ln.split(':')[-1] )
				error_lines.append(ln)
			elif '^' in ln and ln.startswith(' '):
				error_lines.append(ln.replace(' ', '-'))
			elif ln.startswith('(') and '__tmp__.c3:' in ln:
				ln = ln.split('__tmp__.c3:')[-1]
				if ')' in ln:
					ln = ln[ ln.index(')')+1 : ].strip()
				errors_raw.append(ln.strip())
				if '(' in ln and ')' in ln and ln.count('(')==1:
					a,b = ln.split('(')
					p,c = (b+' ').split(')')
					ln = a + c
					paren_messages.append('<i>(%s)</i>' % p)

				if ln.startswith('Error:'):
					self.debug_chat('C3 Error!')
					ln = ln.replace('Error:', '<b>Error:</b>')

				if ', ' in ln:
					error_messages += ln.split(', ')
				else:
					error_messages.append(ln)

		#print(error_lines)
		#print(error_messages)
		#print(paren_messages)
		if self._prev_err != err:
			self._prev_err = err
			msg = '<br/>'.join(error_lines + error_messages + paren_messages)
			self.popup.setStyleSheet('background-color:black; color:lightgreen; font-size:28px')
			self.popup.setText(msg)
			self.popup.adjustSize()
			self.popup.show()

			if err not in self._c3_errors:
				print(errors_raw)
				self.c3_search_for_help(err, errors_raw, paren_messages)

	C3_ERROR_HELP = {
		"Error: Expected ';'"					: 'syntax-error1.md',
		"Error: Expected the ending ')' here."  : 'syntax-error2.md',  ## this happens for func calls missing )
	}
	def c3_search_for_help(self, err, error_messages, paren_messages):
		help = {}
		self._c3_errors[err] = help
		a = '\n'.join(error_messages)
		if a in self.C3_ERROR_HELP:
			self.learn_c3_widget.load(tag=self.C3_ERROR_HELP[a])
		else:
			a = ' '.join(error_messages).lower()
			a = a.replace('error', '')  ## otherwise all searches just return the doc on Error Handlers
			md = self.learn_c3_widget.search(a)
			if md and md not in help:
				help[md] = a

	def com_loop(self):
		scope = {'random':random, 'uniform':uniform, 'math':math}
		c3_script = zig_script = None  ## multi-line strings with c3 or zig code
		c3_scripts = {}
		zig_scripts = {}
		c3_world_script = None
		zig_world_script = None

		txt = self.editor.toPlainText()
		updates = 0
		for ln in txt.splitlines():
			if c3_script is not None:
				if ln == "'''":
					if c3_script[0].endswith('{'):
						c3_script.append('}')  ## end of wrapper function __object_script__
						self.parse_c3( '\n'.join(c3_script), world_script=c3_world_script )
					else:
						c3_world_script = '\n'.join(c3_script)
						if self.parse_c3( c3_world_script ):
							self.check_c3(c3_world_script)

					c3_script = None
				else:
					c3_script.append(ln)
			elif zig_script is not None:
				if ln == "'''":
					if zig_script[0].endswith('{'):
						zig_script.append('}')
						self.parse_zig( '\n'.join(zig_script), world_script=zig_world_script )
					else:
						zig_world_script = '\n'.join(zig_script)
						self.parse_zig(zig_world_script)
					zig_script = None
				else:
					zig_script.append(ln)

			if ln.count('=') == 1:
				a,b = ln.split('=')
				a=a.strip()
				b=b.strip()
				if b.isdigit():
					scope[a] = int(b)
				elif b.count('.')==1 and b.split('.')[0].isdigit() and b.split('.')[1].isdigit():
					scope[a] = float(b)
				elif b.startswith(('random', 'uniform', 'math')):
					try:
						scope[a] = eval(b, scope, scope)
					except:
						pass

			for binfo in self.blends:
				sym = binfo['SYMBOL']
				if ln.count(sym)==1:
					cmd = ln.split(sym)[-1]
					if cmd.startswith('.c3.script') and '=' in cmd and cmd.split('=')[-1].strip().endswith("'''"):
						c3_script = ['']
						c3_scripts[sym] = c3_script
					elif cmd.startswith('.zig.script') and '=' in cmd and cmd.split('=')[-1].strip().endswith("'''"):
						zig_script = ['']
						zig_scripts[sym] = zig_script

			for name in self.ob_syms:
				sym = self.ob_syms[name]
				if ln.count(sym)==1:
					cmd = ln.split(sym)[-1]
					if cmd.startswith('.c3.script') and '=' in cmd and cmd.split('=')[-1].strip().endswith("'''"):
						c3_script = ['fn void __object_script__(){']
						c3_scripts[name] = c3_script
					elif cmd.startswith('.zig.script') and '=' in cmd and cmd.split('=')[-1].strip().endswith("'''"):
						zig_script = ['fn __object_script__() void {']
						zig_scripts[name] = zig_script

					for key in ('rotation', 'scale'):
						if cmd.startswith('.'+key) and cmd.count(',')==2:
							if '=' in cmd: v = cmd.split('=')[-1].strip()
							else:  v = cmd.split('.'+key)[-1].strip()
							if v.startswith( ('[', '(', '{') ): v=v[1:]
							if v.endswith( (']', ')', '}') ): v=v[:-1]
							ok = False
							try:
								#v = [float(c.strip()) for c in v.split(',')]
								v = eval('[%s]' %v, scope, scope)
								ok = True
							except:
								pass
							if ok:
								if self.active_object:
									self.active_object[key] = v
									updates += 1
									break


			for name in self.mat_syms:
				sym = self.mat_syms[name]
				if ln.count(sym)==1:
					#print(ln)
					cmd = ln.split(sym)[-1]

					for key in ('position', 'scale'):
						if cmd.startswith('.'+key) and cmd.count(',')==2:
							if '=' in cmd: v = cmd.split('=')[-1].strip()
							else:  v = cmd.split('.'+key)[-1].strip()
							if v.startswith( ('[', '(', '{') ): v=v[1:]
							if v.endswith( (']', ')', '}') ): v=v[:-1]
							ok = False
							try:
								#v = [float(c.strip()) for c in v.split(',')]
								v = eval('[%s]' %v, scope, scope)
								ok = True
							except:
								pass
							if ok:
								if key.upper() in self.shared_materials[name]:
									self.shared_materials[name][key.upper()][0] = v[0]
									self.shared_materials[name][key.upper()][1] = v[1]
									self.shared_materials[name][key.upper()][2] = v[2]
								else:
									self.shared_materials[name][key.upper()]=v
								updates += 1
								break

					if cmd.startswith('.color') and cmd.count(',')==2:
						if '=' in cmd: clr = cmd.split('=')[-1].strip()
						else:  clr = cmd.split('.color')[-1].strip()
						if clr.startswith( ('[', '(', '{') ): clr=clr[1:]
						if clr.endswith( (']', ')', '}') ): clr=clr[:-1]
						ok = False
						try:
							#clr = [float(c.strip()) for c in clr.split(',')]
							clr = eval('[%s]' %clr, scope, scope)
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
							if r > 255: r = 255
							if g > 255: g = 255
							if b > 255: b = 255
							self.shared_materials[name]['WIDGET'].setStyleSheet('background-color:rgb(%s,%s,%s)' %(r,g,b))
							updates += 1
		if updates:
			self.glview.update()

	def material_sym(self, name, blend=None):
		if name not in self.mat_syms:
			sym = self._msyms.pop()
			self.mat_syms[name] = sym
			if blend not in self.mat_syms_blends:
				self.mat_syms_blends[blend] = {}
			self.mat_syms_blends[blend][sym]=name
		return self.mat_syms[name]

	def object_sym(self, name, blend=None):
		if name not in self.ob_syms:
			sym = self._osyms.pop()
			self.ob_syms[name] = sym
			if blend not in self.ob_syms_blends:
				self.ob_syms_blends[blend] = {}
			self.ob_syms_blends[blend][sym]=name
		return self.ob_syms[name]

	def open_blend(self, url):
		is_fs = self.isFullScreen()
		if is_fs:
			self.showNormal()
		self.hide()
		hash_before = hashlib.md5(open(url,'rb').read()).hexdigest()
		cmd = [codeeditor.BLENDER, url]
		if is_fs:
			cmd += ['--window-fullscreen']
		else:
			cmd += [ '--window-geometry','640','100', '800','800']
		cmd += ['--python-exit-code','1', '--python', os.path.join(_thisdir,'libgenzag.py')]
		print(cmd)
		subprocess.check_call(cmd)
		self.show()
		if is_fs:
			## TODO fix linux wayland? problem exit from fullscreen is broken
			## Qt6 is wrong when self.isFullScreen() called?
			self.showFullScreen()

		hash_after = hashlib.md5(open(url,'rb').read()).hexdigest()
		if hash_before != hash_after:
			print('user updated blend file')
			if self.active_blend == url:
				if self.active_name in self.glview.buffers:
					self.glview.buffers.pop(self.active_name)
				self.view_blender_object(self.active_name, self.active_blend)


	def blend_to_qt(self, dump):
		layout = QVBoxLayout()
		container = QWidget()
		container.setLayout(layout)
		url = dump['URL']

		qsym = QLabel(self.blend_syms[url])
		qsym.setStyleSheet('font-size:64px; color:cyan;')
		layout.addWidget(qsym)

		a,b = os.path.split(url)
		#btn = QPushButton('open: '+b)
		btn = QPushButton('blender')
		#btn.setFixedWidth(64)
		btn.setIcon(QIcon(os.path.join(_thisdir,'Blender-button.png')))
		btn.setIconSize( QSize(59,50) )

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
			btn.setStyleSheet('font-size:10px')
			btn.setFixedWidth(50)
			btn.setCheckable(True)
			if name in dump['selected']:
				btn.setChecked(True)

			btn.toggled.connect(
				lambda x,n=name: self.toggle_blend_object(x,n, dump)
			)
			box.addWidget(btn)
			#pos = [str(round(v,1)) for v in dump['objects'][name]['pos']]
			#box.addWidget(QLabel(','.join(pos)))
			box.addStretch(1)
			if name in dump['meshes']:
				osym = self.object_sym(name, url)
				btn = QPushButton(osym)
				btn.setFixedWidth(32)
				box.addWidget(btn)
				btn.clicked.connect(lambda a,s=osym:self.editor.textCursor().insertText(s))

				#btn = QPushButton('🮶')  ## no font for this on Windows :(
				btn = QPushButton('▶')
				btn.setFixedWidth(32)
				box.addWidget(btn)
				btn.clicked.connect(
					lambda e,n=name: self.view_blender_object(n, url)
				)

		return container

	def update_active_materials(self):
		if not self.active_blend: return
		blend = self.active_blend
		info = self.active_object
		rthresh = 5
		if self._is_fs:
			rthresh = 13

		#print(dir(self.materials_layout))
		clear_layout(self.materials_layout)
		self.materials_layout.setContentsMargins(1,1,1,1)
		container = QWidget()
		#container.setFixedHeight(300)
		self.materials_layout.addWidget(container)
		sub = QVBoxLayout()
		sub.setContentsMargins(1,1,1,1)
		container.setLayout(sub)
		#sub = self.materials_layout
		container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

		row = []
		for mat in info['materials']:
			self.shared_materials[mat['name']] = mat

			if self._is_fs:
				box = QVBoxLayout()
			else:
				box = QHBoxLayout()
			con = QWidget()
			if self._is_fs:
				con.setFixedHeight(60)
			else:
				box.setContentsMargins(1,1,1,1)
				con.setFixedHeight(30)
			con.setLayout(box)
			mat['WIDGET'] = con
			row.append(con)

			if False:
				lab = QLabel(mat['name'])
				if self._is_fs:
					lab.setStyleSheet('font-size:14px')
				else:
					lab.setStyleSheet('font-size:10px')
				box.addWidget(lab)

				if 'class' in mat and self._is_fs:
					btn = QPushButton(mat['class'])
					btn.setFixedHeight(16)
					btn.setFixedWidth(60)
					btn.setStyleSheet('font-size:8px')
					box.addWidget(btn)

			msym = self.material_sym(mat['name'], blend)
			btn = QPushButton( msym )
			btn.setToolTip(mat['name'])
			if self._is_fs:
				#btn.setStyleSheet('font-size:22px')
				btn.setFixedWidth(32)
			else:
				#btn.setStyleSheet('font-size:14px')
				btn.setFixedWidth(32)
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

			if len(row) >= rthresh:
				bx = QHBoxLayout()
				for wid in row: bx.addWidget(wid)
				#self.materials_layout.addLayout(bx)
				#co = QWidget()
				#co.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
				#co.setLayout(bx)
				#self.materials_layout.addWidget(co)
				sub.addLayout(bx)
				row = []

		if len(row):
			bx = QHBoxLayout()
			for wid in row: bx.addWidget(wid)
			#self.materials_layout.addLayout(bx)
			#co = QWidget()
			#co.setLayout(bx)
			#self.materials_layout.addWidget(co)
			sub.addLayout(bx)
			row = []

		#self.materials_layout.addStretch(1)
		#self.glview.adjustSize()
		#self.materials_container.adjustSize()
		#self.editor.adjustSize()
		#self.materials_layout.update()


	def view_blender_object(self, obname, blend):
		print('view_blender_object:', obname, blend)
		if self.glview:
			info = self.glview.view_blender_object(obname, blend)
			info['EYES_X'] = 0
			info['EYES_Y'] = 0
			self.active_object = info
			self.active_blend = blend
			self.active_name = obname
			self.update_active_materials()




	def insert_material(self, sym):
		#https://doc.qt.io/qt-6/richtext-html-subset.html
		##tt = Typewrite font (same as <code>)
		cur = self.editor.textCursor()
		cur.insertHtml('<tt style="background-color:red; font-size:32px">%s</tt>' % sym)


	def load_blends(self, blends):
		user_vars = list(string.ascii_letters)
		user_vars.reverse()
		cur = self.editor.textCursor()
		for i,blend in enumerate(blends):
			#cur.insertText('%s = ' % user_vars.pop())
			self.on_new_blend(blend)
			if i != len(blends)-1:
				cur.insertText('\n')

	def run_script(self, *args, **kw):
		export = kw.get('export',None)

		txt = self.editor.toPlainText()
		header = [
			'import bpy',
			'if "Cube" in bpy.data.objects: bpy.data.objects.remove( bpy.data.objects["Cube"] )',
			BLEND_WRAP_CLASS,
		]
		py = []
		blends = []

		has_c3 = has_zig = has_rust = False
		if '.rust.script' in txt:
			txt = txt.replace('.rust.script','.rust().script')
			has_rust = True
		if '.zig.script' in txt:
			txt = txt.replace('.zig.script','.zig().script')
			has_zig = True
		if '.c3.script' in txt:
			txt = txt.replace('.c3.script','.c3().script')
			has_c3 = True

		if has_c3 and has_zig:
			print('WARN: c3 and zig scripts at the same time are not yet supported')
			return

		for c in txt:
			if c in self.BLEND_SYMS:
				info = self.get_blend_from_symbol(c)
				sel = info['selected']
				blends.append(info)
				header += [
				'with bpy.data.libraries.load(r"%s") as (data_from, data_to):' % info['URL'],
				'	data_to.objects=data_from.objects',

				'__blend__%s=BlendWrap()' % len(blends),
				]
				if len(sel)==0:
					header += [
					'for ob in data_to.objects:',
					'	if ob is not None: __blend__%s.add(ob)' % len(blends),
					]
				elif len(sel)==1:
					header += [
					'for ob in data_to.objects:',
					'	if ob is not None and ob.name =="%s":' % sel[0],
					'		__blend__%s.add(ob)' % len(blends),
					]
				else:
					names = ['"%s"' % n for n in sel]
					header += [
					'for ob in data_to.objects:',
					'	if ob is not None and ob.name in (%s):' % ','.join(names),
					'		__blend__%s.add(ob)' % len(blends),
					]
				py.append('(__blend__%s)' % len(blends))

				continue
			elif c == self.OBJ_REP:
				## TODO images
				continue
			elif c in self.LATIN:
				for obname in self.ob_syms:
					if self.ob_syms[obname] == c:
						c = obname
						break
				py.append('(bpy.data.objects["%s"])' % c)
				continue
			elif c in self.CYRILLIC:
				for matname in self.mat_syms:
					if self.mat_syms[matname] == c:
						c = matname
						break
				py.append('(bpy.data.materials["%s"])' % c)
				continue

			py.append(c)
		py = '\n'.join(header) + '\n' + ''.join(py)
		print(py)

		if sys.platform=='win32':
			tmp='C:\\tmp\\zigzag_script.py'
		else:
			tmp='/tmp/zigzag_script.py'
		open(tmp,'wb').write(py.encode('utf-8'))
		cmd = [codeeditor.BLENDER, '--python-exit-code','1']
		if export:
			cmd.append('--background')
		else:
			cmd += ['--window-geometry','640','100', '800','800']

		if has_rust:
			cmd += ['--python', rustzagpy, '--', '--import='+tmp ]
		elif has_zig:
			cmd += ['--python', zigzagpy, '--', '--import='+tmp ]
		else:
			cmd += ['--python', c3zagpy, '--', '--import='+tmp ]
		if export:
			cmd.append('--export='+export)
		print(cmd)
		#subprocess.check_call(cmd)
		res = subprocess.run(cmd, capture_output=True, text=True)
		if res.returncode != 0:
			print('COMPILE ERROR!')
			print(res.stdout)
			print(res.stderr)
			self.popup.setStyleSheet('background-color:black; color:lightgreen; font-size:10px')
			if res.stderr.strip():
				self.popup.setText(res.stderr)
			else:
				self.popup.setText(res.stdout)
			self.popup.adjustSize()
			self.popup.show()


	def export_html(self, *args):
		#tmp = '/tmp/zigzag-preview.html'
		tmp = os.path.expanduser('~/Desktop/zigzag-preview.html')
		self.run_script( export=tmp )

	def __syntax_highlight_post(self, html):
		print('on_syntax_highlight_post')
		print(html)
		if "<br/>'''<br/>" in html:  ## end of tripple quote
			html = html.replace("<br/>'''<br/>", "</u><br/>'''<br />")  ## note the extra <br /> white space
		if "'''<br/>" in html:  ## no white space trick
			html = html.replace("'''<br/>", "'''<br/><u style='background-color:darkblue'>")
		print(html)
		return html

	def on_mouse_over_anchor(self, event, url, sym):
		if sym==self.OBJ_TABLE:
			assert url.isdigit()
			tab = self.tables[int(url)]
			arr = self.table_to_code(tab)
			print(arr)
			QToolTip.showText(event.globalPosition().toPoint(), arr)
		elif sym in self.BLEND_SYMS:
			info = self.blends[ int(url.split(':')[-1]) ]
			tip = info['URL'] + '\nselected:\n'
			if len(info['selected']):
				for name in info['selected']:
					tip += '\t'+name + '\n'
			else:
				tip = ' (no objects selected)'
			QToolTip.showText(event.globalPosition().toPoint(), tip)
		elif sym in self.LATIN:
			for name in self.ob_syms:
				if self.ob_syms[name] == sym:
					tip = 'Object: %s' % name
					QToolTip.showText(event.globalPosition().toPoint(), tip)
		elif sym in self.CYRILLIC:
			for name in self.mat_syms:
				if self.mat_syms[name] == sym:
					tip = 'Material: %s' % name
					QToolTip.showText(event.globalPosition().toPoint(), tip)


	def on_link_clicked(self, url, evt):
		print('clicked:', url)
		if url.isdigit():
			index = int(url)
			print('clicked on table:', index)
			tab = self.table_to_qt(self.tables[index])
			clear_layout(self.images_layout)
			self.images_layout.addWidget(tab)
			tab.show()
		elif url.startswith("BLENDER:"):
			info = self.blends[ int(url.split(':')[-1] ) ]
			url = info['URL']
			clear_layout(self.images_layout)
			self.images_layout.addWidget(self.blend_to_qt(info))
			self.blend_popup(url, info, evt)

		elif url in self.on_sym_clicked:
			self.on_sym_clicked[url](url)

		elif url in self.LATIN:
			for blend in self.ob_syms_blends:
				if url in self.ob_syms_blends[blend]:
					obname = self.ob_syms_blends[blend][url]
					#self.view_blender_object(obname, blend)
					self.object_popup(obname, blend, url, evt)
					break
		elif url in self.CYRILLIC:
			for blend in self.mat_syms_blends:
				if url in self.mat_syms_blends[blend]:
					matname = self.mat_syms_blends[blend][url]
					print('material name:', matname)
					#print(self.shared_materials[matname])
					self.material_popup(matname, blend, url, evt)
					break

		elif url in self.qimages:
			qlab = QLabel()
			qlab.setPixmap(self.qimages[url])
			clear_layout(self.images_layout)
			self.images_layout.addWidget(qlab)
			qlab.show()

	def blend_popup(self, blend, info, evt):
		box = self.ob_popup_layout
		clear_layout(box)

		for o in self.blends:
			if o['URL']==blend:
				sym = o['SYMBOL']
				break

		lab = QLabel('%s: %s' % (sym,blend))
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		btn = QPushButton('🖹')
		btn.setToolTip("attach script to world")
		btn.setFixedWidth(32)
		btn.clicked.connect(lambda e,b=btn: self.helper_script(b,sym))
		box.addWidget(btn)

		pnt = evt.globalPosition().toPoint()
		x = pnt.x()
		y = pnt.y()
		self.ob_popup.move(x+20,y+20)
		self.ob_popup.show()

	def material_popup(self, matname, blend, sym, evt):
		info = self.shared_materials[matname]
		#box = self.ob_popup_layout
		#clear_layout(box)
		box = self.clear_object_popup()

		lab = QLabel('%s: %s' % (sym,matname))
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		btn = QPushButton('⟴')
		btn.setFixedWidth(32)
		btn.clicked.connect( lambda e,b=btn: self.helper_material_position(b,sym,info) )
		box.addWidget(btn)

		btn = QPushButton('⤡')
		btn.setFixedWidth(32)
		btn.clicked.connect( lambda e,b=btn: self.helper_material_scale(b,sym,info) )
		box.addWidget(btn)

		btn = QPushButton('🎨')
		btn.setFixedWidth(32)
		btn.clicked.connect( lambda e,b=btn: self.helper_color(b,sym,info) )
		box.addWidget(btn)

		pnt = evt.globalPosition().toPoint()
		x = pnt.x()
		y = pnt.y()
		self.ob_popup.move(x+20,y+20)
		self.ob_popup.show()

	def helper_material_scale(self, button, sym, info):
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.scale = [X,Y,Z]' % sym
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

		box = self.clear_object_popup()

		lab = QLabel(sym)
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		if 'SCALE' not in info:
			info['SCALE'] = [1,1,1]
		vec = info['SCALE']
		bx = QVBoxLayout()
		con = QWidget()
		con.setStyleSheet('background-color:rgba(0,0,0, 0.1)')
		con.setLayout(bx)
		box.addWidget(con)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_scl(sym, 0, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_scl(sym, 1, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_scl(sym, 2, v, vec))
		bx.addWidget(sl)

		self.ob_popup.show()

	def on_sym_scl(self, sym, axis, value, vec):
		vec[axis] = value / 50
		for i in range(3):
			vec[i] = round(vec[i],2)
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.scale = %s' % (sym, vec)
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()
		if self.glview:
			self.glview.update()


	def helper_material_position(self, button, sym, info):
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.position = [X,Y,Z]' % sym
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

		#box = self.ob_popup_layout
		#clear_layout(box)
		box = self.clear_object_popup()
		lab = QLabel(sym)
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		if 'POSITION' not in info:
			info['POSITION'] = [0,0,0]
		vec = info['POSITION']
		bx = QVBoxLayout()
		con = QWidget()
		con.setLayout(bx)
		con.setStyleSheet('background-color:rgba(0,0,0, 0.1)')
		box.addWidget(con)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_pos(sym, 0, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_pos(sym, 1, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-100,100)
		sl.valueChanged.connect(lambda v: self.on_sym_pos(sym, 2, v, vec))
		bx.addWidget(sl)

		self.ob_popup.show()

	def on_sym_pos(self, sym, axis, value, vec):
		vec[axis] = value / 100
		for i in range(3):
			vec[i] = round(vec[i],2)
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.position = %s' % (sym, vec)
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()
		if self.glview:
			self.glview.update()

	def helper_color(self, button, sym, info):

		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.color = [RED,GREEN,BLUE]' % sym
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

		#box = self.ob_popup_layout
		#clear_layout(box)
		box = self.clear_object_popup()
		lab = QLabel(sym)
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		vec = info['color']
		bx = QVBoxLayout()
		con = QWidget()
		con.setLayout(bx)
		box.addWidget(con)

		sl = new_slider(color='pink', bgcolor='red')
		sl.valueChanged.connect(lambda v: self.on_sym_color(sym, 0, v, vec, info))
		bx.addWidget(sl)

		sl = new_slider(color='lightgreen', bgcolor='green')
		sl.valueChanged.connect(lambda v: self.on_sym_color(sym, 1, v, vec, info))
		bx.addWidget(sl)

		sl = new_slider(color='lightblue', bgcolor='blue')
		sl.valueChanged.connect(lambda v: self.on_sym_color(sym, 2, v, vec, info))
		bx.addWidget(sl)

		self.ob_popup.show()


	def on_sym_color(self, sym, axis, value, vec, info):
		vec[axis] = value / 100
		for i in range(3):
			vec[i] = round(vec[i],2)
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.color = %s' % (sym, vec[:3])
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()
		if self.glview:
			self.glview.update()

		r,g,b,a = vec
		r = int(r*255)
		g = int(g*255)
		b = int(b*255)
		if r > 255: r = 255
		if g > 255: g = 255
		if b > 255: b = 255
		info['WIDGET'].setStyleSheet('background-color:rgb(%s,%s,%s)' %(r,g,b))


	def object_popup(self, obname, blend, sym, evt):
		box = self.ob_popup_layout
		clear_layout(box)


		#btn = QPushButton('▶')
		#btn.setToolTip("view object")

		#btn.setFixedWidth(32)
		#box.addWidget(btn)
		#btn.clicked.connect(
		#	lambda e,n=obname: self.view_blender_object(n, blend)
		#)

		lab = QLabel('%s: %s' % (sym,obname))
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)


		btn = QPushButton('🖹')
		btn.setToolTip("attach script to object")
		btn.setFixedWidth(32)
		btn.clicked.connect(lambda e,b=btn: self.helper_script(b,sym))
		box.addWidget(btn)


		btn = QPushButton('⟲')
		btn.setToolTip("rotate object")
		btn.setFixedWidth(32)
		btn.clicked.connect( lambda e,b=btn: self.helper_rotate(b,sym) )
		box.addWidget(btn)

		pnt = evt.globalPosition().toPoint()
		x = pnt.x()
		y = pnt.y()
		#self.ob_popup.move(evt.pos())
		self.ob_popup.move(x+20,y+20)
		self.ob_popup.show()

	def helper_script(self, button, sym):
		box = self.ob_popup_layout
		clear_layout(box)
		lab = QLabel('%s' % sym)
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)

		#btn = QPushButton('C3')
		btn = QPushButton('',self)
		btn.setIcon(QIcon(os.path.join(_thisdir,'C3-button.png')))
		btn.setIconSize( QSize(105,60) )
		btn.clicked.connect(lambda e:self.helper_c3(sym) )
		box.addWidget(btn)
		#btn = QPushButton('ZIG')
		btn = QPushButton('',self)
		btn.setIcon(QIcon(os.path.join(_thisdir,'Zig-button.png')))
		btn.setIconSize( QSize(146,60) )
		btn.clicked.connect(lambda e:self.helper_zig(sym) )
		box.addWidget(btn)

		self.ob_popup.show()

	def helper_c3(self, sym):
		self.ob_popup.hide()
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = "%s.c3.script = '''" % sym
				o.append(ln)
				o.append('')
				o.append("'''")
			else:
				o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

	def helper_zig(self, sym):
		self.ob_popup.hide()
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = "%s.zig.script = '''" % sym
				o.append(ln)
				o.append('')
				o.append("'''")
			else:
				o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

	def helper_rotate(self, button, sym):
		box = self.ob_popup_layout
		clear_layout(box)

		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.rotation = [X,Y,Z]' % sym
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()

		box = self.ob_popup_layout
		#lab = QLabel('%s.rotation' % sym)
		#lab.setStyleSheet('background-color:rgba(0,0,0, 0.1)')
		#box.addWidget(lab)
		lab = QLabel(sym)
		lab.setStyleSheet('font-size:32px; color:cyan')
		box.addWidget(lab)


		vec = [0,0,0]

		bx = QVBoxLayout()
		con = QWidget()
		con.setStyleSheet('background-color:rgba(0,0,0, 0.1)')
		con.setLayout(bx)
		box.addWidget(con)


		sl = new_slider(-180, 180)
		sl.valueChanged.connect(lambda v: self.on_sym_rotate(sym, 0, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-180, 180)
		sl.valueChanged.connect(lambda v: self.on_sym_rotate(sym, 1, v, vec))
		bx.addWidget(sl)

		sl = new_slider(-180, 180)
		sl.valueChanged.connect(lambda v: self.on_sym_rotate(sym, 2, v, vec))
		bx.addWidget(sl)

		#self.ob_popup.resize(300,80)
		self.ob_popup.show()

	def on_sym_rotate(self, sym, axis, value, vec):
		vec[axis] = value
		o = []
		for ln in self.editor.toPlainText().splitlines():
			if ln.startswith(sym):
				ln = '%s.rotation = %s' % (sym, vec)
			o.append(ln)
		self.editor.setText('\n'.join(o))
		self.do_syntax_hl()
		if self.active_object:
			self.active_object['rotation'] = vec
		if self.glview:
			self.glview.update()

def new_slider(min=0, max=100, color='grey', bgcolor='lightblue'):
	sl = QSlider()
	sl.setStyleSheet('''
QSlider::groove:horizontal {
	background-color: %s;
	border: 1px solid;
	height: 10px;
	margin: 0px;
}
QSlider::handle:horizontal {
	background-color: %s;
	border: 1px solid;
	height: 30px;
	width: 40px;
	margin: -15px 0px;
}''' % (bgcolor, color))
	sl.setOrientation(Qt.Orientation.Horizontal)
	sl.setMinimum(min)
	sl.setMaximum(max)
	return sl


BLEND_WRAP_CLASS = '''

class BlendWrap:
	def __init__(self):
		self.objects = []

	def c3(self):
		class _wrap_c3:
			def __init__(self, ob):
				print('_wrap_c3 init:', ob)
				self.__dict__['ob'] = ob
			def __setattr__(self, name, value):
				print('__setattr__:', name, value)
				if name=='script':
					txt = bpy.data.texts.new(name=name+'.c3')
					txt.from_string(value)
					print(txt)
					self.ob.c3_script = txt
		return _wrap_c3(bpy.data.worlds[0])

	def zig(self):
		class _wrap_zig:
			def __init__(self, ob):
				self.__dict__['ob'] = ob
			def __setattr__(self, name, value):
				if name=='script':
					txt = bpy.data.texts.new(name=name+'.zig')
					txt.from_string(value)
					self.ob.zig_script = txt
		return _wrap_zig(bpy.data.worlds[0])

	def rust(self):
		class _wrap_rust:
			def __init__(self, ob):
				self.__dict__['ob'] = ob
			def __setattr__(self, name, value):
				if name=='script':
					txt = bpy.data.texts.new(name=name+'.rs')
					txt.from_string(value)
					self.ob.rust_script = txt
		return _wrap_rust(bpy.data.worlds[0])

	def add(self, ob):
		bpy.data.scenes[0].collection.objects.link(ob)
		self.objects.append(ob)

'''





LEARN_C3 = [
"""
.c3.script = '''

fn void onclick( int x, int y ) @extern("onclick") @wasm {
	js_eval(`
		window.alert("hello click")
	`);
}

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


class LearnZig(QWidget):
	def __init__(self, zoomout=0):
		super().__init__()
		self.pages = {}
		self.zoomout = zoomout
		self.resize(640, 700)
		self.setWindowTitle('Learn Zig')
		self.main_vbox = vbox = QVBoxLayout()
		self.setLayout(self.main_vbox)
		doc = open(os.path.join(_thisdir,'zig-doc.html')).read()
		#if doc.startswith('<!doctype html>'):
		#	doc = doc[ len('<!doctype html>') : ]
		key = '<div id="contents-wrapper">'
		assert doc.count(key)==1
		doc = doc.split(key)[-1]
		pages = []
		page = []
		for ln in doc.splitlines():
			lns = ln.strip()
			if lns.startswith( ('<h2 id=','<h3 id=') ):
				page = [ln]
				pages.append(page)
			else:
				page.append(ln)

		for page in pages:
			doc = '\n'.join(page).strip()
			try:
				doc = xml.dom.minidom.parseString('<body>%s</body>'%doc)
				print(doc)
			except xml.parsers.expat.ExpatError:
				print(doc.encode('utf-8'))
				continue

			title = doc.documentElement.firstChild.getAttribute('id')
			print(title)
			self.pages[title] = doc.toxml()

		self.load_random()
		self.show()

	def load_random(self):
		title = choice( list(self.pages.keys()) )
		self.load(title)

	def load(self, title):
		clear_layout(self.main_vbox)
		btn = QPushButton('next')
		btn.clicked.connect(lambda b: self.load_random())
		self.main_vbox.addWidget(btn)

		print('loading:', title)
		self.setWindowTitle(title)
		self.edit = edit = QTextEdit()
		html = self.pages[title]
		edit.setHtml(html)
		if self.zoomout:
			edit.zoomOut(self.zoomout)
		self.main_vbox.addWidget(edit)

	def search(self, s):
		words = s.lower().split()
		print('search:', words)
		rem = 'a the this is not name <br/> : -'.split()
		for r in rem:
			if r in words:
				words.remove(r)
		print('SEARCH:', words)

		ranks = {}
		tmp = QTextEdit()
		for title in self.pages:
			score = 0
			txt = title.lower().split()
			for word in words:
				score += txt.count(word) * 10

			tmp.setHtml(self.pages[title])
			txt = tmp.toPlainText().lower().split()
			for word in words:
				score += txt.count(word)

			if score not in ranks:
				ranks[score] = []

			ranks[score].append(title)

		del tmp

		scores = list(ranks.keys())
		scores.sort()
		scores.reverse()
		best = None
		for score in scores:
			if not score: break
			titles = ranks[score]
			print('rank %s:' % score)
			for title in titles:
				if best is None:
					best = title
		if best:
			self.load(title)
			return best



class Window(QWidget):
	def open_code_editor(self, *args):
		window = ZigZagEditor()
		window.reset(parent=self)
		window.show()
		self.megasolid = window
		self.hide()

	def learn_c3(self):
		w = self.blendgen("🐵")
		w.editor.textCursor().insertText(choice(LEARN_C3).strip())
		learn_wasm = ['wasm1.md', 'wasm2.md', 'wasm3.md']
		w.learn_c3_widget.load(tag=choice(learn_wasm))
		self.megasolid = w

	def learn_zig(self):
		w = self.blendgen("🐱", use_learn_zig=True)
		w.editor.textCursor().insertText(choice(LEARN_ZIG).strip())
		self.megasolid = w

	def learn_rust(self):
		w = self.blendgen("👽", use_learn_rust=True)
		w.editor.textCursor().insertText(choice(LEARN_RUST).strip())
		self.megasolid = w

	def blendgen(self, sym, use_learn_zig=False, use_learn_rust=False):
		if sys.platform=='win32':
			out = 'C:\\tmp\\%s.blend' % sym
		else:
			out = '/tmp/%s.blend' % sym
		cmd = [self.blenders[-1], '--background', '--python-exit-code', '1', '--python', os.path.join(_thisdir,'libgenzag.py'), '--', '--generate=%s' % sym, '--out='+out]
		print(cmd)
		subprocess.check_call(cmd)
		window = ZigZagEditor()
		if use_learn_rust:
			window.reset(parent=self, use_learn_c3=False, use_learn_zig=False)
		elif use_learn_zig:
			window.reset(parent=self, use_learn_c3=False, use_learn_zig=True)
		else:
			window.reset(parent=self)
		window.load_blends([out])
		window.show()
		self.megasolid = window
		self.hide()
		return window


	def thread(self):
		while self.proc:
			#print('waiting...')
			ln = self.proc.stdout.readline()
			#print(ln)
			if ln==b'':
				print('blender exit')
				break
			self.bstdout.append(ln)


	def blender_loop(self):
		try:
			self._blender_loop()
		except KeyboardInterrupt:
			print('Ctrl+C exit')
			sys.exit()

	def _blender_loop(self):
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
		cmd +=['--window-geometry','640','100', '1100','800', '--python-exit-code', '1', '--python', c3zagpy]
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
		self.timer.timeout.connect(self.blender_loop)
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

		btn = QPushButton("🐶")  ## dog
		btn.clicked.connect( lambda: self.blendgen("🐶") )
		self.tools.addWidget(btn)

		btn = QPushButton("🐻")  ## bear
		btn.clicked.connect( lambda: self.blendgen("🐻") )
		self.tools.addWidget(btn)

		btn = QPushButton("🦍")  ## gorilla
		btn.clicked.connect( lambda: self.blendgen("🦍") )
		self.tools.addWidget(btn)

		btn = QPushButton("👽")  ## alien
		btn.clicked.connect( lambda: self.blendgen("👽") )
		self.tools.addWidget(btn)

		btn = QPushButton("💩")  ## poop
		btn.clicked.connect( lambda: self.blendgen("💩") )
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

		c3btn = QPushButton('',self)
		c3btn.setIcon(QIcon(os.path.join(_thisdir,'C3-button.png')))
		c3btn.setIconSize( QSize(105,60) )
		c3btn.clicked.connect(lambda e:self.learn_c3() )

		zbtn = QPushButton('',self)
		zbtn.setIcon(QIcon(os.path.join(_thisdir,'Zig-button.png')))
		zbtn.setIconSize( QSize(146,60) )
		zbtn.clicked.connect(lambda e:self.learn_zig() )

		btn = QPushButton('Blender')
		btn.setIcon(QIcon(os.path.join(_thisdir,'Blender-button.png')))
		btn.setIconSize( QSize(59,50) )
		btn.clicked.connect(self.run_blender)

		button_cancel = QPushButton("Exit")
		button_cancel.clicked.connect(sys.exit)

		hbox = QHBoxLayout()
		hbox.addWidget(c3btn)
		hbox.addWidget(zbtn)

		if os.path.isfile(os.path.expanduser('~/.cargo/bin/rustc')):
			rbtn = QPushButton('⛭  ')
			rbtn.setStyleSheet('font-size:40px')
			lab = QLabel('rust', rbtn)
			lab.move(45,10)
			lab.setStyleSheet('font-size:14px; background-color:rgba(0,0,0,0)')
			rbtn.clicked.connect(lambda e:self.learn_rust())
			hbox.addWidget(rbtn)

		hbox.addStretch(1)
		hbox.addWidget(btn)
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
	elif '--learn-c3' in sys.argv:
		app = QApplication(sys.argv)
		window = learn_c3.LearnC3()
		app.exec()
	elif '--learn-zig' in sys.argv:
		app = QApplication(sys.argv)
		window = LearnZig()
		app.exec()
	else:
		main()

