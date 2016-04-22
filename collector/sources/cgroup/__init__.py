# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

import os
from datetime import datetime
import socket, hashlib
from collector import Source, Document

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


def compute_difference_over_dictonaries(new, old, diffseconds = 0):
	r = { }

	for k in new:
		if type(new[k]) == dict:
			# jump to recursion

			if k in old:
				r[k] = compute_difference_over_dictonaries(new[k], old[k], diffseconds)
			else:
				r[k] = compute_difference_over_dictonaries(new[k], { }, diffseconds)

		else:
			# simple datatypes

			if type(new[k]) == list:
				r[k] = { "items": new[k] }

				if k in old:
					r[k].update({
						"removed": list(set(new[k]).difference(set(old[k]))),
						"added": list(set(old[k]).difference(set(new[k]))), 
					})

			elif type(new[k]) == float or type(new[k]) == int:
				r[k] = { "absolute": new[k] }

				if k in old:
					r[k]["difference"] = new[k]-old[k]

					if diffseconds != 0:
						r[k]["difference_per_second"] = (new[k]-old[k])/diffseconds

			else:
				r[k] = new[k]

	return r

class CGroup(Source):
	ID_HASH_ALGO = "sha256"

	def __init__(self, name, gtype, path, source="Filesystem"):
		Source.__init__(self, name)
		self.id = hashlib.new(CGroup.ID_HASH_ALGO)
		self.type = gtype
		self.path = os.path.abspath(path)
		self.data = { }
		self.timestamp = datetime.now()
		self.last_data = { }
		self.last_timestamp = datetime.now()
		self.params = [
			# name, filename, read function, simple value monotonic growing
			("tasks", "tasks", self.read_param_number_array),
		]

	def get_uuid(self):
		s = "%s|%s|%s|%s" % (socket.gethostname(), self.name, self.type, self.timestamp.isoformat())
		# python3->2 compatiblity
		s = s.encode("ASCII", errors='ignore')
		self.id.update(s)
		return self.id.hexdigest()

	def update(self):		
		self.last_timestamp = self.timestamp
		self.timestamp = datetime.now()
		self.last_data = self.data
		self.data = { }

		for param, filename, func in self.params:
			self.data[param] = func(filename)

	def build_data(self, timediff_sec):
		return [compute_difference_over_dictonaries(self.data, self.last_data, timediff_sec)]

	def docs(self):
		docs = [ ]
		utcdelta = datetime.now()-datetime.utcnow()
		td = (self.timestamp-self.last_timestamp).total_seconds()

		basedoc = {
			"host": socket.gethostname(),
			"name": self.name,
			"path": self.path,
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

		for d in self.build_data(td):
			doc_data = basedoc.copy()
			doc_data.update({ self.type: d })

			docs += [Document(
				self.name,
				doc_id = self.get_uuid(),
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

	def read_param(self, param):
		self.test_param(param)

		p = self.path + "/" + param
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

		return d

	def read_number_param(self, param):
		v = self.read_param(param)
		if v != None:
			return int(v)
		else:
			return None

	def read_param_key_value(self, param):
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
				r[j[0]] = int(j[1])

		return r

	def read_param_enumerated_number_array(self, param):
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
					r["%i" % (idx)] = int(k)
					idx += 1

		return r

	def read_param_number_array(self, param):
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
					r += [int(k)]

		return r

class CPUAccount(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
			("usage", "cpuacct.usage", self.read_number_param),
			("stat", "cpuacct.stat", self.read_param_key_value),
			("usage_percpu", "cpuacct.usage_percpu", self.read_param_enumerated_number_array),
		]

class CPU(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("cfs_period_us", "cpu.cfs_period_us", self.read_number_param),
				("stat", "cpu.stat", self.read_param_key_value),
				("shares", "cpu.shares", self.read_number_param),
		]

class Memory(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("usage_in_bytes", "memory.usage_in_bytes", self.read_number_param),
				("stat", "memory.stat", self.read_param_key_value),
		]

class Blkio(CGroup):
	def __init__(self, name, path):
		CGroup.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("io_service_bytes", "blkio.io_service_bytes", self.read_per_device_key_value),
				("io_service_bytes_recursive", "blkio.io_service_bytes_recursive", self.read_per_device_key_value),
				("io_service_time", "blkio.io_service_time", self.read_per_device_key_value),
				("io_service_time_recursive", "blkio.io_service_time_recursive", self.read_per_device_key_value),
				("io_merged", "blkio.io_merged", self.read_per_device_key_value),
				("io_merged_recursive", "blkio.io_merged_recursive", self.read_per_device_key_value),
				("io_wait_time", "blkio.io_wait_time", self.read_per_device_key_value),
				("io_wait_time_recursive", "blkio.io_wait_time_recursive", self.read_per_device_key_value),
				("io_queued", "blkio.io_queued", self.read_per_device_key_value),
				("io_queued_recursive", "blkio.io_queued_recursive", self.read_per_device_key_value),

#				("throttle_io_service_bytes", "blkio.throttle.io_service_bytes", self.read_per_device_key_value),
#				("throttle_io_serviced", "blkio.throttle.io_serviced", self.read_per_device_key_value),
#				("throttle_write_iops_device", "blkio.throttle.write_iops_device", self.read_per_device_key_value),
#				("throttle_read_iops_device", "blkio.throttle.read_iops_device", self.read_per_device_key_value),
#				("throttle_write_bps_device", "blkio.throttle.write_bps_device", self.read_per_device_key_value),
#				("throttle_read_bps_device", "blkio.throttle.read_bps_device", self.read_per_device_key_value),
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

	def read_per_device_key_value(self, param):
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




