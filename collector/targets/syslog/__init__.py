# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from datetime import datetime
from collector import Target, Document
from collector.targets import datetime2iso_corrector
import json
from collector.targets.syslog.SyslogClient import SyslogClientRFC5424, SyslogClient
import syslog
import os

class NetSyslogRFC5424(Target):
	def __init__(self, host, port, proto="tcp", program="netsyslog"):
		Target.__init__(self, "Syslog RFC5424 host=%s:%i" % (host, port))
		self.program = program
		self.client = SyslogClientRFC5424(host, port, proto=proto)

	def push(self, doc):
		d = datetime2iso_corrector(doc.data())
		d["type"] = doc.type()
		self.client.log("@cee: %s" % (json.dumps(d)), facility=SyslogClient.FAC_SYSLOG, severity=SyslogClient.SEV_DEBUG, program=self.program, pid=os.getpid(), timestamp=datetime.utcnow())

class Syslog(Target):
	def __init__(self):
		Target.__init__(self, "Syslog")

	def push(self, doc):
		d = datetime2iso_corrector(doc.data())
		d["type"] = doc.type()
		syslog.syslog("@cee: %s" % (json.dumps(d)))


