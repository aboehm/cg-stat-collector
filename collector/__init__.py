# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from datetime import datetime
import json

class Target:
	def __init__(self, target):
		self.target = target

	def push(self, doc):
		None

class Document:
	def __init__(self, source, doc_id=None, doc_type=None, doc_data=None):
		self.source = source
		self.doc_id = doc_id
		self.doc_type = doc_type
		self.doc_data = doc_data

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

	def docs(self):
		return []

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
		
		print("%i documents pushed to %i targets" % (docs, len(self.targets)))

