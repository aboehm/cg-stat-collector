#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from collector import Collector
from collector.sources import CGroupFilesystem
from collector.targets import Console
from collector.targets.elastic import Elasticsearch
from collector.targets.syslog import SyslogRFC5424
import datetime, sys, time, argparse

class SourceAction(argparse.Action):
	def __init__(self, option_strings, dest, nargs=None, **kwargs):
		if nargs is not None:
			raise ValueError("nargs not allowed")
		argparse.Action.__init__(self, option_strings, dest, **kwargs)
	
	def __call__(self, parser, namespace, values, option_string=None):
		if getattr(namespace, self.dest) == None:
			setattr(namespace, self.dest, [])

		a = values.split(',', 1)
		if len(a) < 1 or len(a) > 2:
			return False
		else:
			source = a[0]
			if len(a) == 2:
				options = a[1]
			else:
				options = None

		sources = getattr(namespace, self.dest)
		if source == "cgroupfs":
			if options == None:
				options = "/sys/fs/cgroup"

			sources += [CGroupFilesystem(options)]

class TargetAction(argparse.Action):
	def __init__(self, option_strings, dest, nargs=None, **kwargs):
		if nargs is not None:
			raise ValueError("nargs not allowed")
		argparse.Action.__init__(self, option_strings, dest, **kwargs)
	
	def __call__(self, parser, namespace, values, option_string=None):
		if getattr(namespace, self.dest) == None:
			setattr(namespace, self.dest, [])

		a = values.split(',', 1)
		if len(a) < 1 or len(a) > 2:
			return False
		else:
			target = a[0]
			if len(a) == 2:
				options = a[1]
			else:
				options = None

		targets = getattr(namespace, self.dest)
		if target == "elasticsearch":
			if options == None:
				options = "http://localhost:9200"

			targets += [Elasticsearch(options)]

		elif target == "console":
			if options != None and options.lower() == "stderr":
				targets += [Console("json", True)]
			else:
				targets += [Console("json", True)]

		elif target == "syslog":
			if options == None:
				host = "localhost"
				port = 514
			else:
				a = options.split(':')
				if len(a) != 2:
					return False

				host = a[0]
				port = int(a[1])
			
			targets += [SyslogRFC5424(host, port)]

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="System Metric Collector")
	parser.add_argument(
		'--target',
		dest='targets',
		action=TargetAction,
	)
	parser.add_argument(
		'--source',
		dest='sources',
		action=SourceAction,
	)
	parser.add_argument(
		'--interval',
		dest='interval',
		type=float,
		nargs='?',
		default=0
	)
	args = parser.parse_args()

	c = Collector()
	c.add_source(CGroupFilesystem("/sys/fs/cgroup"))

	for t in args.targets:
		c.add_target(t)

	while True:
		try:
			c.collect()
		except KeyboardInterrupt as e:
			break

		if args.interval == 0:
			break
		else:
			time.sleep(args.interval)

