# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from datetime import datetime
import os, socket, hashlib
from collector import Source, Document
from collector.sources import compute_difference_over_dictonaries, field_converter_integer, field_converter_kilobyte, field_converter_nanosecond, field_converter_microsecond, field_converter_userhz

class GroupException(Exception):
	def __init__(self, cause, data=None):
		self.cause = cause
		self.data = data

	def str(self):
		s = "%s: %s" % (self.__class__.__name__, self.cause)
		if self.data != None:
			s += " : " + self.data
		return s

	def unicode(self):
		s = u"%s: %s" % (self.__class__.__name__, self.cause)
		if self.data != None:
			s += u" : "+self.data
		return s

class GroupExceptionBadPath(GroupException):
	def __init__(self, path):
		GroupException.__init__(self, cause="Only absolute path allowed", data=path)

class GroupExceptionInaccessiblePath(GroupException):
	def __init__(self, path):
		GroupException.__init__(self, "Path not accessible", path)

class CGroup(Source):
	def __init__(self, name, gtype, path, source="Filesystem"):
		Source.__init__(self, name)
		self.type = gtype
		self.path = os.path.abspath(path)
		self.data = { }
		self.last_data = { }
		self.pids = { }
		self.params = [
			# name, filename, read function, simple value monotonic growing
			("tasks", "tasks", self.read_param_array, field_converter_integer),
		]

	def update(self):
		Source.update(self)

		self.last_data = self.data
		self.data = { }

		for param, filename, func, conv in self.params:
			if param == "tasks":
				self.pids = func(filename)

			self.data[param] = func(filename, conv)

	def build_data(self, timediff_sec):
		return [compute_difference_over_dictonaries(self.data, self.last_data, timediff_sec)]

	def docs(self):
		docs = [ ]
		basedoc = self.get_base_information()
		basedoc.update({
			"name": self.name,
			"path": self.path,
			"pids": self.pids,
		})

		for d in self.build_data(self.get_timedelta()):
			doc_data = basedoc.copy()
			doc_data.update({ self.type: d })

			docs += [Document(
				self.name,
				doc_type = self.type,
				doc_data = doc_data
			)]

		return docs 

	def test_param(self, param):
		"""
		>>> Group("test", "test", "tests/CPUAccount").test_param("../CPUAccount/tasks") # +IGNORE_EXCEPTION_DETAIL
		Traceback (most recent call last):
		 ...
		cgroup_v1.GroupExceptionBadPath: ../CPUAccount/tasks
		"""

		if param.find("/") >= 0:
			raise GroupExceptionBadPath(param)

	def read_param(self, param, conv=None):
		self.test_param(param)

		p = self.path + "/" + param
		if os.path.exists(p) == False:
			return None

		f = open(p, "r")
		if f == None:
			raise GroupExceptionInaccessiblePath(p)
		else:
			# TODO: customize
			d = f.read(1024)
			f.close()

		if d == None:
			return None

		if len(d) == 0:
			return None

		if conv != None:
			return conv(d)
		else:
			return d

	def read_param_key_value(self, param, conv=None):
		r = {}

		d = self.read_param(param)
		if d == None:
			return { }
		else:
			d = d.split("\n")

		for i in d:
			j = i.split(" ")
			if len(j) != 2:
				continue
			else:
				if conv != None:
					r[j[0]] = conv(j[1])
				else:
					r[j[0]] = j[1]

		return r

	def read_param_enumerated_array(self, param, conv=None):
		r = { }

		d = self.read_param(param)
		if d == None:
			return { }
		else:
			d = d.split("\n")

		idx = 0
		for i in d:
			j = i.split(" ")
			for k in j:
				if k != "":
					if conv != None:
						r["%i" % (idx)] = conv(k)
					else:
						r["%i" % (idx)] = int(k)

					idx += 1

		return r

	def read_param_array(self, param, conv=None):
		r = [] 

		d = self.read_param(param)
		if d == None:
			return [ ]
		else:
			d = d.split("\n")

		idx = 0
		for i in d:
			j = i.split(" ")
			for k in j:
				if k != "":
					if conv != None:
						r += [conv(k)]
					else:
						r += [int(k)]

		return r

class CPUAccount(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
			("usage", "cpuacct.usage", self.read_param, field_converter_nanosecond),
			("stat", "cpuacct.stat", self.read_param_key_value, field_converter_userhz),
			("usage_percpu", "cpuacct.usage_percpu", self.read_param_enumerated_array, field_converter_nanosecond),
		]

class CPU(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("cfs_period_us", "cpu.cfs_period_us", self.read_param, field_converter_microsecond),
				("stat", "cpu.stat", self.read_param_key_value, field_converter_nanosecond),
				("shares", "cpu.shares", self.read_param, field_converter_nanosecond),
		]

class Memory(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("usage_in_bytes", "memory.usage_in_bytes", self.read_param, field_converter_integer),
				("failcnt", "memory.failcnt", self.read_param, field_converter_integer),
				("stat", "memory.stat", self.read_param_key_value, field_converter_integer),
		]

class Blkio(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("io_service_bytes", "blkio.io_service_bytes", self.read_per_device_key_value, field_converter_integer),
				("io_service_bytes_recursive", "blkio.io_service_bytes_recursive", self.read_per_device_key_value, field_converter_integer),
				("io_service_time", "blkio.io_service_time", self.read_per_device_key_value, field_converter_nanosecond),
				("io_service_time_recursive", "blkio.io_service_time_recursive", self.read_per_device_key_value, None),
				("io_merged", "blkio.io_merged", self.read_per_device_key_value, field_converter_integer),
				("io_merged_recursive", "blkio.io_merged_recursive", self.read_per_device_key_value, field_converter_integer),
				("io_wait_time", "blkio.io_wait_time", self.read_per_device_key_value, field_converter_nanosecond),
				("io_wait_time_recursive", "blkio.io_wait_time_recursive", self.read_per_device_key_value, field_converter_nanosecond),
				("io_queued", "blkio.io_queued", self.read_per_device_key_value, field_converter_integer),
				("io_queued_recursive", "blkio.io_queued_recursive", self.read_per_device_key_value, field_converter_integer),
		]

	def build_data(self, timediff_sec):
		r_old = { }
		g_old = { }
		r_new = { }
		g_new = { }
		r = { }

		for key in self.last_data:
			if key[:3] == "io_":
				for dev in self.last_data[key]:
					if not dev in r_old:
						r_old[dev] = { "device": dev }

					r_old[dev][key] = self.last_data[key][dev]
			else:
				g_old[key] = self.last_data[key]

		for key in self.data:
			if key[:3] == "io_":
				for dev in self.data[key]:
					if not dev in r_new:
						r_new[dev] = { "device": dev }

					r_new[dev][key] = self.data[key][dev]
			else:
				g_new[key] = self.data[key]

		for dev in r_new:
			r_new[dev].update(g_new)

			if dev in r_old:
				r_old[dev].update(g_old)
				r[dev] = compute_difference_over_dictonaries(r_new[dev], r_old[dev], timediff_sec)
			else:
				r[dev] = compute_difference_over_dictonaries(r_new[dev], { }, timediff_sec)

		return r.values()

	def read_per_device_key_value(self, param, conv=None):
		r = { }

		d = self.read_param(param)
		if d == None:
			raise Exception("parameter %s returns null!" % (param))

		d = d.split("\n")

		for i in d:
			j = i.split(" ")
			if len(j) != 3:
				continue
			else:
				dev = self.get_devname_from_major_minor(j[0])
				if dev in r:
					r[dev][j[1]] = int(j[2])
				else:
					r[dev] = { }

		return r

	def get_devname_from_major_minor(self, majmin):
		v = majmin.split(":")
		major = int(v[0])
		minor = int(v[1])

		if major == 8:
			disk = int(minor / 8)
			disk = chr(ord('a')+disk)
			part = (minor % 8)+1

			return "sd%s%i" % (disk, part)

		elif major == 112:
			disk = int(minor / 8)
			disk = chr(ord('a')+disk)
			part = (minor % 8)+1

			return "sd%s%i" % (disk, part)

		elif major == 252:
			return "dm-%i" % (int(minor))

		else:
			return majmin

class CGroupFilesystem(Source):
	def __init__(self, mount_point):
		Source.__init__(self, "CGroupFilesystem")
		self.mount_point = mount_point
		self.controler = ["blkio", "cpu", "cpuacct", "memory"]
		self.groups = { }

	def enumerate_groups(self, controler):
		r = []

		search_path = "%s/%s" % (self.mount_point, controler)
		for dirname, directories, files in os.walk(search_path):
			cg = dirname[len(search_path):]
			if cg == "":
				cg = "/"

			r += [(cg, dirname, controler)]

		return r

	def update(self):
		cgs = []

		for controler in self.controler:
			cgs += self.enumerate_groups(controler)
			if not controler in self.groups:
				self.groups[controler] = { }

		for name, path, controler in cgs:
			if not name in self.groups[controler]:
				if controler == "cpu":
					self.groups[controler][name] = CPU(name, path)

				elif controler == "cpuacct":
					self.groups[controler][name] = CPUAccount(name, path)

				elif controler == "memory":
					self.groups[controler][name] = Memory(name, path)
				
				elif controler == "blkio":
					self.groups[controler][name] = Blkio(name, path)

				else:
					continue

			self.groups[controler][name].update()

	def docs(self):
		self.update()

		docs = []
		for controler in self.groups:
			for name in self.groups[controler]:
				docs += self.groups[controler][name].docs()

		return docs



