# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

from collector import Source
from collector.sources.cgroup import CPU, CPUAccount, Memory, Blkio
import os
import json

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


