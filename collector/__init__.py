# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from datetime import datetime
import socket, hashlib, json

class Target:
	def __init__(self, target):
		self.target = target

	def push(self, doc):
		None

class Document:
	ID_HASH_ALGO = "sha256"

	def __init__(self, source, doc_id=None, doc_type=None, doc_data=None):
		self.source = source
		self.doc_type = doc_type
		self.doc_data = doc_data

		if doc_id == None:
			h = hashlib.new(Document.ID_HASH_ALGO)
			if doc_data == None:
				self.doc_id = None
			else:
				h.update(repr(self.doc_data).encode("ASCII", errors="ignore"))
				self.doc_id = h.hexdigest()

		else:
			self.doc_id = doc_id


	def id(self):
		return self.doc_id

	def type(self):
		return self.doc_type

	def data(self):
		return self.doc_data

	def __str__(self):
		return str({
			"id": self.id(),
			"type": self.type(),
			"data": self.data(),
		})

class Source:
	def __init__(self, name):
		self.name = name
		self.timestamp = datetime.now()
		self.last_timestamp = datetime.now()

	def update(self):
		self.last_timestamp = self.timestamp
		self.timestamp = datetime.now()

	def docs(self):
		return []

	def get_timedelta(self):
		return (self.timestamp-self.last_timestamp).total_seconds()

	def get_base_information(self):
		utcdelta = datetime.now()-datetime.utcnow()

		return {
			"host": socket.gethostname(),
			"collected": {
				"year": self.timestamp.year,
				"hour": self.timestamp.hour,
				"month": self.timestamp.month,
				"day": self.timestamp.day,
				"minute": self.timestamp.minute,
				"second": self.timestamp.second,
				"microsecond": self.timestamp.microsecond,
				"weekday": self.timestamp.strftime("%A"),
				"utc": self.timestamp.isoformat(),
				"localtime": (self.timestamp-utcdelta).isoformat(),
			}
		}

class Collector:
	def __init__(self, sources=[], targets=[]):
		self.sources = sources
		self.targets = targets

	def add_source(self, s):
		self.sources += [s]

	def add_target(self, t):
		self.targets += [t]

	def collect(self):
		docs = 0

		for source in self.sources:
			for doc in source.docs():
				for target in self.targets:
					target.push(doc)
					docs += 1
		
		# print("%i documents pushed to %i targets" % (docs, len(self.targets)))

