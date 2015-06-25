#!/usr/bin/env python

import copy
import errno
import fnmatch
import getpass
import os
import re
import shutil
import socket
import subprocess
import tempfile
import yaml

user = getpass.getuser()
basecontrol = {
	'package': os.path.basename(os.getcwd()),
	'section': 'config',
	'priority': 'optional',
	'maintainer': user + ' <' + user + '@' + socket.gethostname() + '>',
	'version': '0-0',
	'architecture': 'all',
	'essential': 'no',
	'description': 'configuration package'
}

def exclude(names, *patterns):
	for name in names:
		for pattern in patterns:
			if fnmatch.fnmatch(name, pattern):
				break
		else:
			yield name

def expandtabs(s, tablen = 8):
	def expand(m):
		return m.group().expandtabs(tablen)
	return ''.join(re.sub(r'^\s+', expand, m) for m in s.splitlines(True))

def rm(*paths):
	for path in paths:
		try:
			os.unlink(path)
		except OSError, ex:
			if ex.errno != errno.ENOENT:
				raise

def rmtree(path):
	try:
		shutil.rmtree(path)
	except OSError, ex:
		if ex.errno != errno.ENOENT:
			raise

def emit(f, key, values):
	print >>f, key, ', '.join(values) if isinstance(values, (list, tuple)) else values

def confpack_debian(path, override):
	tmp = False
	if path is None:
		path = tempfile.mkdtemp()
		tmp = True
	path = os.path.realpath(path)
	path_control = os.path.join(path, 'control.yml')
	control = copy.deepcopy(basecontrol)
	if not tmp:
		control['package'] = os.path.basename(path)
	if os.path.isfile(path_control):
		control.update(yaml.load(expandtabs(open(path_control).read())))
	for k, v in override.iteritems():
		control[k] = ', '.join(v)
	fname = control['package'] + '_' + control['version'] + '_' + control['architecture'] + '.deb'
	rm(fname)
	path_debian = os.path.join(path, 'DEBIAN')
	rmtree(path_debian)
	os.mkdir(path_debian)
	with open(os.path.join(path_debian, 'control'), 'w+') as f:
		try: emit(f, 'Package:', control['package'])
		except KeyError: pass
		try: emit(f, 'Section:', control['section'])
		except KeyError: pass
		try: emit(f, 'Priority:', control['priority'])
		except KeyError: pass
		try: emit(f, 'Maintainer:', control['maintainer'])
		except KeyError: pass
		try: emit(f, 'Version:', control['version'])
		except KeyError: pass
		try: emit(f, 'Architecture:', control['architecture'])
		except KeyError: pass
		try: emit(f, 'Essential:', control['essential'])
		except KeyError: pass
		try: emit(f, 'Pre-Depends:', control['pre-depends'])
		except KeyError: pass
		try: emit(f, 'Depends:', control['depends'])
		except KeyError: pass
		try: emit(f, 'Replaces:', control['replaces'])
		except KeyError: pass
		try: emit(f, 'Description:', control['description'])
		except KeyError: pass
	if 'preinst' in control:
		with open(os.path.join(path_debian, 'preinst'), 'w+') as f:
			f.write(control['preinst'])
			os.fchmod(f.fileno(), 0755)
	if 'postinst' in control:
		with open(os.path.join(path_debian, 'postinst'), 'w+') as f:
			f.write(control['postinst'])
			os.fchmod(f.fileno(), 0755)
	if 'prerm' in control:
		with open(os.path.join(path_debian, 'prerm'), 'w+') as f:
			f.write(control['prerm'])
			os.fchmod(f.fileno(), 0755)
	if 'postrm' in control:
		with open(os.path.join(path_debian, 'postrm'), 'w+') as f:
			f.write(control['postrm'])
			os.fchmod(f.fileno(), 0755)
	cwd = os.getcwd()
	os.chdir(path_debian)
	subprocess.call(['tar', '--owner=0', '--group=0', '-czf', 'control.tar.gz'] + os.listdir('.'))
	os.chdir(path)
	subprocess.call(['tar', '--owner=0', '--group=0', '-czf', os.path.join(path_debian, 'data.tar.gz'), '-T', '/dev/null'] + sorted(exclude(os.listdir('.'), 'control.yml', 'DEBIAN', '.*', '*.deb')))
	os.chdir(path_debian)
	with open('debian-binary', 'w+') as f:
		print >>f, '2.0'
	subprocess.call(['ar', 'r', os.path.join(cwd, fname), 'debian-binary', 'control.tar.gz', 'data.tar.gz'])
	os.chdir(cwd)
	rmtree(path_debian)
	if tmp:
		rmtree(path)
	return fname

if __name__ == '__main__':
	import sys
	override = {}
	paths = []
	if len(sys.argv) < 2:
		print >>sys.stderr, 'Usage:', sys.argv[0], '[key=value]... [path]...'
		sys.exit()
	for arg in sys.argv[1:]:
		if '=' in arg:
			arg = arg.split('=', 1)
			key = arg[0].strip()
			value = arg[1].strip()
			try:
				override[key].append(value)
			except KeyError:
				override[key] = [value]
		else:
			paths.append(arg)
	if len(paths) > 0:
		for path in paths:
			print path, '=>', confpack_debian(path, override)
	else:
		print '=>', confpack_debian(None, override)
