# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from collector import Target
from datetime import datetime
import sys
import json

# converts datetime type in dictonaries to iso8601-formated string
def datetime2iso_corrector(data):
	r = { }

	for k in data:
		if type(data[k]) == dict:
			r[k] = datetime2iso_corrector(data[k])
		elif type(data[k]) == datetime:
			r[k] = data[k].isoformat()
		else:
			r[k] = data[k]

	return r

class Console(Target):
	def __init__(self, format=None, use_stderr=False):
		Target.__init__(self, "Console")

		if format == None:
			self.format = "json"
		else:
			self.format = format

		self.use_stderr = use_stderr == True

	def push(self, doc):
		if self.use_stderr == True:
			out = sys.stderr
		else:
			out = sys.stdout

		if self.format == "json":
			d = datetime2iso_corrector(doc.data())
			d["id"] = doc.id()
			d["type"] = doc.type()
			out.write(json.dumps(d, indent=2)+"\n")
		else:
			out.write(str(doc)+"\n")
