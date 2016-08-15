# -*- coding: utf-8 -*-
# vim: noet shiftwidth=4 tabstop=4

import re, os

REGEX_TIME = re.compile("(([0-9]+)-)?(([0-9]+):)?(([0-9]+):)?([0-9]+)")

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

def field_converter_integer(value):
	try:
		return int(value)
	except:
		return None

def field_converter_kilobyte(value):
	try:
		return int(value)*1024
	except:
		return None

def field_converter_nanosecond(value):
	try:
		return float(value)/(1000.0*1000.0*1000.0)
	except:
		return None

def field_converter_microsecond(value):
	try:
		return float(value)/(1000.0*1000.0)
	except:
		return None

def field_converter_millisecond(value):
	try:
		return float(value)/(1000.0)
	except:
		return None

def field_converter_float(value):
	try:
		return float(value)
	except:
		return None

def field_converter_time(value):
	global REGEX_TIME

	m = REGEX_TIME.match(value)
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

USER_HZ = float(os.sysconf_names['SC_CLK_TCK'])

def field_converter_userhz(value):
	global USER_HZ
	try:
		return float(value)/USER_HZ
	except:
		return None

