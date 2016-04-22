# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from datetime import datetime
from collector import Target, Document
from collector.targets import datetime2iso_corrector
import json
from collector.targets.syslog.SyslogClient import SyslogClientRFC5424, SyslogClient
import syslog

class NetSyslogRFC5424(Target):
	def __init__(self, host, port, proto="tcp"):
		Target.__init__(self, "Syslog RFC5424 host=%s:%i" % (host, port))
		self.client = SyslogClientRFC5424(host, port, proto=proto)

	def push(self, doc):
		d = datetime2iso_corrector(doc.data())
		d["type"] = doc.type()
		self.client.log(json.dumps(d), facility=SyslogClient.FAC_SYSLOG, severity=SyslogClient.SEV_DEBUG, program="syslog-collector-target", pid=1)

class Syslog(Target):
	def __init__(self):
		Target.__init__(self, "Syslog")

	def push(self, doc):
		d = datetime2iso_corrector(doc.data())
		d["type"] = doc.type()
		syslog.syslog(json.dumps(d))


