# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from datetime import datetime
import logging, elasticsearch
from collector import Target, Document

class Elasticsearch(Target):
	def __init__(self, es_hosts, index_format="collector-%Y.%m.%d"):
		Target.__init__(self, "Elasticsearch hosts="+str(es_hosts))
		self.client = elasticsearch.Elasticsearch(es_hosts)
		self.index_format = index_format

	def get_current_index(self):
		return datetime.now().strftime(self.index_format)

	def push(self, doc):
		self.client.index(
			index=self.get_current_index(),
			id=doc.id(),
			doc_type=doc.type(),
			body=doc.data(),
		)

