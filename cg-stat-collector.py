#!/usr/bin/python3
#
# cg-stat-collector, a OS statistics collector. 
# Copyright (C) 2017, Alexander Böhm <alxndr.boehm@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from collector import Collector
from collector.sources.cgroup import CGroupFilesystem
from collector.sources.ps import UnixPS, LinuxPS
from collector.sources.Command import Command
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

		elif source == "command":
			if options == None:
				return False
			else:
				a = options.split(" ")
				if len(a) > 1:
					sources += [Command(a[0], arguments=a[1:])]
				else:
					sources += [Command(a[0])]

		elif source == "unixps":
			sources += [UnixPS()]

		elif source == "linuxps":
			sources += [LinuxPS()]


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
				targets += [Console("json", False)]

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
					try:
						host = a[0]
						port = int(a[1])
					except Exception as e:
						return False
			
			targets += [NetSyslogRFC5424(host, port, proto=proto, program=get_program_info()["name"])]

		elif target == "syslog":
			targets += [Syslog()]


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
		prog=get_program_info()["name"],
		description="System Metric Collector",
		epilog="""
Example:

  Run collector every minute and collect cgroup and ps data. Send it to syslog.

  cg-stat-collector.py \\
	--interval 60 \\
	--source cgroupfs,/sys/fs/cgroup \\
	--source linuxps \\
	--target syslog
 \n
""",
		formatter_class=argparse.RawTextHelpFormatter
	)
	parser.add_argument(
		'--source',
		help="""add a metric source. Following are available
  - console
  - unixps
  - linuxps
  - cgroupfs,PATH_TO_CGROUPFS
""",
		dest='source',
		default=[],
		action=SourceAction,
	)
	parser.add_argument(
		'--target',
		help="""add a logging target. Following are available
  - syslog
  - netsyslog,(tcp|udp)://HOST:PORT
  - elasticsearch,HOST:PORT
""",
		dest='target',
		default=[],
		action=TargetAction,
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

# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet
