# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

import os
from datetime import datetime
import json

class CGroupV1:
	def __init__(self):
		None

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

class Group:
	def __init__(self, name, gtype, path):
		self.name = name
		self.type = gtype
		self.path = os.path.abspath(path)
		self.last_data = { }
		self.last_updated = datetime.now()
		self.params = [
			# name, filename, read function, simple value monotonic growing
			("tasks", "tasks", self.read_param_number_array, False),
		]

	def get_name(self):
		return self.name

	def update(self):
		ts = datetime.now()

		for param, filename, func, mono in self.params:
			value = func(filename)
			
			new_data = { }
			if not param in self.last_data:
				self.last_data[param] = { }

			if mono == True:
				if param in self.last_data:
					diff_t = ts-self.last_updated
					diff_v = value-self.last_data[param]["absolute"]

					self.last_data[param] = {
						"difference": diff_v,
						"difference_per_sec": diff_v/diff_t,
						"absolute": value,
					}
				else:
					self.last_data[param].update({
						"difference": 0,
						"difference_per_sec": 0,
						"absolute": value,
					})

			else:
				self.last_data[param] = value

	def get_repr(self):
		r = {
			"cgroup_type": self.type,
			"name": self.name,
			"path": self.path,
			"seen": self.last_updated.isoformat(),
		}

		if self.last_data == None:
			self.update()

		r.update(self.last_data)

		return [r]

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

class CPUAccount(Group):
	def __init__(self, name, path):
		Group.__init__(self, name, self.__class__.__name__, path)
		self.params += [
			("usage", "cpuacct.usage", self.read_number_param, False),
			("stat", "cpuacct.stat", self.read_param_key_value, False),
			("usage_percpu", "cpuacct.usage_percpu", self.read_param_number_array, False),
		]

class CPU(Group):
	def __init__(self, name, path):
		Group.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("cfs_period_us", "cpu.cfs_period_us", self.read_number_param, False),
				("stat", "cpu.stat", self.read_param_key_value, False),
				("shares", "cpu.shares", self.read_number_param, False),
		]

class Memory(Group):
	def __init__(self, name, path):
		Group.__init__(self, name, self.__class__.__name__, path)
		self.params += [
				("usage_in_bytes", "memory.usage_in_bytes", self.read_number_param, False),
				("stat", "memory.stat", self.read_param_key_value, False),
		]

class Blkio(Group):
	def __init__(self, name, path):
		Group.__init__(self, name, self.__class__.__name__, path)

	def read_per_device_key_value(self, param):
		r = []

		d = self.read_param(param)
		d = d.split("\n")

		for i in d:
			j = i.split(" ")
			if len(j) < 2 or len(j) != 3:
				continue
			else:
				dev = self.get_devname_from_major_minor(j[0])
				r += [(dev, { j[1] : int(j[2]) })]

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

	def get_repr(self):
		devs = {}

		for i in [
			"io_service_bytes",
			"io_service_bytes_recursive",
			"io_merged",
			"io_merged_recursive",
			"io_service_time",
			"io_service_time_recursive",
			"io_serviced",
			"io_serviced_recursive",
			"io_wait_time",
			"io_wait_time_recursive",
			"io_queued",
			"io_queued_recursive",
			]:

			for dev, dev_stats in self.read_per_device_key_value("blkio."+i):
				if not dev in devs:
					devs[dev] = { "throttle": {} }

				if not i in devs[dev]:
					devs[dev][i] = {}

				devs[dev][i].update( dev_stats )

		throttle = {}
		for i in [
			"io_service_bytes",
			"io_serviced",
			"read_bps_device",
			"read_iops_device",
			"write_bps_device",
			"write_iops_device",
			]:

			for dev, dev_stats in self.read_per_device_key_value("blkio.throttle."+i):
				if not dev in devs:
					devs[dev] = { "throttle": { } }

				if not i in devs[dev]["throttle"]:
					devs[dev]["throttle"][i] = {}

				devs[dev]["throttle"][i].update( dev_stats )

		r = []
		for dev in devs:
			r1 = Group.get_repr(self)[0]
			r1.update({ "Blkio": { "device": dev } })
			r1["Blkio"].update(devs[dev])
			r += [r1]

		return r

class CGroupFileSystem:
	def __init__(self, mount_point):
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
			if not name in self.groups:
				if controler == "cpu":
					self.groups[controler][name] = CPU(name, path)

				elif controler == "cpuacct":
					self.groups[controler][name] = CPUAccount(name, path)

				elif controler == "memory":
					self.groups[controler][name] = Memory(name, path)

				else:
					continue

			self.groups[controler][name].update()

	def get_repr(self):
		r = []

		for controler in self.groups:
			for name in self.groups[controler]:
				r += self.groups[controler][name].get_repr()

		return r

cgfs = CGroupFileSystem("/sys/fs/cgroup")
cgfs.update()

for i in cgfs.get_repr():
	print(json.dumps(i))
		

