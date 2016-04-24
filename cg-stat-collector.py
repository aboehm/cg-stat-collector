#!/usr/bin/python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

from collector import Collector
from collector.sources import CGroupFilesystem
from collector.targets import Console
from collector.targets.elastic import Elasticsearch
from collector.targets.syslog import Syslog, NetSyslogRFC5424
import datetime, sys, time, argparse

def get_program_info():
	return {
		"name": "cg-stat-collector",
		"version": "0.0.1",
	}

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

		elif target == "netsyslog":
			if options == None:
				host = "localhost"
				port = 514
			else:
				a = options.split('://')
				if len(a) == 1:
					proto = "udp"
					con_port = a[0]
				else:
					proto = a[0].lower()
					if proto != "udp" and proto != "tcp":
						return False
					else:
						proto = a[0]

					con_part = a[1]

				a = con_part.split(':')
				if len(a) != 2:
					return False
				else:
					host = a[0]
					port = int(a[1])
			
			targets += [NetSyslogRFC5424(host, port, proto=proto, program=get_program_info()["name"])]

		elif target == "syslog":
			targets += [Syslog()]


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog=get_program_info()["name"],
		description="System Metric Collector",
	)
	parser.add_argument(
		'--target',
		help="add logging target",
		dest='target',
		default=[],
		action=TargetAction,
	)
	parser.add_argument(
		'--source',
		help="add metric source",
		dest='source',
		default=[],
		action=SourceAction,
	)
	parser.add_argument(
		'--interval',
		dest='interval',
		help="interval between metric collection runs",
		type=float,
		nargs='?',
		default=0
	)
	args = parser.parse_args()

	if len(args.source) == 0 or len(args.target) == 0:
		print("No sources or targets given!\n")
		parser.print_help()

	c = Collector()

	for s in args.source:
		c.add_source(s)

	for t in args.target:
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

