# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from collector.sources.Command import Command
from collector.sources import compute_difference_over_dictonaries, field_converter_integer, field_converter_float, field_converter_time, field_converter_kilobyte
from collector import Document
import re

regex_compress = re.compile("( )+")
regex_begin = re.compile("^( )+")

def ps_time_to_seconds(strtime):
	m = regex_time.match(strtime)
	if m == None:
		return None
	else:
		total = 0
		(_, days, _, hours, _, minutes, seconds) = m.groups()

		if seconds != None:
			total += int(seconds)

		if minutes != None:
			total += int(minutes)*60

		if hours != None:
			total += int(hours)*60*60

		if days != None:
			total += int(days)*24*60*60

		return total

class PS(Command):
	def __init__(self, ps="/bin/ps", fields=["pid"]):
		self.fields = fields

		field_list = ""
		for i in range(0, len(self.fields)):
			if i != 0:
				field_list += ","

			field_list += self.fields[i]

		Command.__init__(self, ps, ["-axo", field_list])

		self.pids = { }
		self.last_pids = { }
		self.field_converter = { }

		self.add_field_converter("pid", field_converter_integer)

	def add_field_converter(self, name, conv):
		self.field_converter[name] = conv

	def update(self):
		global regex_compress, regex_begin

		self.last_pids = self.pids.copy()
		self.pids = { }
		Command.update(self)
		
		# get lines from output
		lines = self.data_stdout.decode("UTF-8")
		lines = lines.split("\n")
		# drop header
		lines = lines[1:]

		r = []

		for line in lines:
			# compress white spaces
			d = regex_compress.sub(" ", line)
			d = regex_begin.sub("", d)
			ar = d.split(" ", len(self.fields)-1)
			if len(d) == 0 or len(d[0]) == 0:
				continue

			# create field list
			data = { }
			pid = None
			for i in range(0, len(self.fields)):
				field = self.fields[i].lower()

				if field == "pid":
					pid = ar[i]
				else:
					if ar[i] == "-":
						continue

					if field in self.field_converter:
						v = self.field_converter[field](ar[i])
						if v != None:
							data[field] = v

						continue

				data[field] = ar[i]

			if pid != None:
				self.pids[pid] = data

	def docs(self):
		self.update()
		basedoc = self.get_base_information()
		docs = []

		for pid in self.pids:
			data = basedoc.copy()
			if pid in self.last_pids:
				data[self.name] = compute_difference_over_dictonaries(self.pids[pid], self.last_pids[pid], self.get_timedelta())
			else:
				data[self.name] = compute_difference_over_dictonaries(self.pids[pid], { }, self.get_timedelta())

			data[self.name]["pid"] = pid
			data["pids"] = [pid]
			docs += [Document(self.name, doc_type=self.name, doc_data=data)]
	
		return docs 


class UnixPS(PS):
	def __init__(self, ps="/bin/ps", fields=["pid", "ppid", "pgid", "pcpu", "ruser", "user", "rgroup", "group", "time", "etime", "vsz", "nice", "tty", "comm", "args"]):
		PS.__init__(self, ps=ps, fields=fields)
		self.name = "UnixPS"
		self.add_field_converter("pcpu", field_converter_float)
		self.add_field_converter("vsz", field_converter_kilobyte)
		self.add_field_converter("nice", field_converter_integer)
		self.add_field_converter("time", field_converter_time)
		self.add_field_converter("etime", field_converter_time)


class LinuxPS(UnixPS):
	def __init__(self, ps="/bin/ps", fields=["pid", "ppid", "pgid", "pcpu", "ruser", "user", "rgroup", "group", "time", "etime", "vsz", "nice", "tty", "euid", "egid", "ruid", "rgid", "fuid", "fuser", "fgid", "fgroup", "suid", "sgid", "pending", "class", "rss", "drs", "trs", "size", "eip", "esp", "stackp", "mntns", "netns", "pidns","ipcns", "label", "maj_flt", "min_flt", "nlwp", "psr", "rtprio", "sched", "state", "comm", "pmem", "command"]):
		UnixPS.__init__(self, ps=ps, fields=fields)
		self.name = "LinuxPS"
		self.add_field_converter("pmem", field_converter_float)

		self.add_field_converter("egid", field_converter_integer)
		self.add_field_converter("euid", field_converter_integer)
		self.add_field_converter("sgid", field_converter_integer)
		self.add_field_converter("suid", field_converter_integer)
		self.add_field_converter("fgid", field_converter_integer)
		self.add_field_converter("fuid", field_converter_integer)

		self.add_field_converter("mntns", field_converter_integer)
		self.add_field_converter("netns", field_converter_integer)
		self.add_field_converter("ipcns", field_converter_integer)
		self.add_field_converter("pidns", field_converter_integer)

		self.add_field_converter("min_flt", field_converter_integer)
		self.add_field_converter("maj_flt", field_converter_integer)

		self.add_field_converter("nlwp", field_converter_integer)
		self.add_field_converter("psr", field_converter_integer)
		self.add_field_converter("rtprio", field_converter_integer)

		self.add_field_converter("rss", field_converter_kilobyte)
		self.add_field_converter("size", field_converter_kilobyte)
		self.add_field_converter("drs", field_converter_kilobyte)
		self.add_field_converter("trs", field_converter_kilobyte)

