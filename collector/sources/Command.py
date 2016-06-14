# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from collector import Source, Document
from subprocess import Popen, PIPE
from datetime import datetime

class Command(Source):
	def __init__(self, command, arguments=[], bufsize=1048576):
		Source.__init__(self, "Command")
		self.command = command
		self.arguments = arguments
		self.bufsize = bufsize
		self.data_stdout = None
		self.data_stderr = None
		self.pid = None

	def execute(self, command, arguments):
		p = Popen([command]+arguments, stdout=PIPE, stderr=PIPE)

		data_stdout = b''
		data_stderr = b''
		eof_stdout = False
		eof_stderr = False

		while True:
			d = p.stdout.read(self.bufsize)
			if d == None or len(d) == 0:
				eof_stdout = True
			else:
				data_stdout += d

			d = p.stderr.read(self.bufsize)
			if d == None or len(d) == 0:
				eof_stderr = True
			else:
				data_stderr += d

			if eof_stdout and eof_stderr:
				break

		return (p.pid, data_stdout, data_stderr)

	def update(self):
		Source.update(self)
		self.pid, self.data_stdout, self.data_stderr = self.execute(self.command, self.arguments)

	def docs(self):
		self.update()
		d = self.get_base_information()

		cmd = self.command
		for i in self.arguments:
			cmd += " " + i

		d.update({
			"name": self.command,
			self.name: {
				"command": cmd,
				"pid": self.pid,
				"stdout": self.data_stdout.decode("UTF-8"),
				"stderr": self.data_stderr.decode("UTF-8"),
			},
		})
		
		return [Document(self.name, doc_type="Command", doc_data=d)]

