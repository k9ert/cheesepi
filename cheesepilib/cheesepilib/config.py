#!/usr/bin/env python
""" Copyright (c) 2015, Swedish Institute of Computer Science
  All rights reserved.
  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions are met:
	  * Redistributions of source code must retain the above copyright
		notice, this list of conditions and the following disclaimer.
	  * Redistributions in binary form must reproduce the above copyright
		notice, this list of conditions and the following disclaimer in the
		documentation and/or other materials provided with the distribution.
	  * Neither the name of The Swedish Institute of Computer Science nor the
		names of its contributors may be used to endorse or promote products
		derived from this software without specific prior written permission.

 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 DISCLAIMED. IN NO EVENT SHALL THE SWEDISH INSTITUTE OF COMPUTER SCIENCE BE LIABLE
 FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Authors: ljjm@sics.se
Testers:
Description: Handles all configuration file duties, including initialising
a local config file (if one does not exist, and initialising logging options
"""

import sys
import os
import re
import uuid
import logging
import json
import urllib2

import cheesepilib as cp


# Globals
cheesepi_dir = os.path.dirname(os.path.realpath(__file__))
config_file  = os.path.join(cheesepi_dir,"cheesepi.conf")
version_file = os.path.join(cheesepi_dir,"version")

logfile = os.path.join(cheesepi_dir, "cheesepi.log")
logging.basicConfig(filename=logfile, level=logging.ERROR, format="%(asctime)s;%(levelname)s; %(message)s")
logger = logging.getLogger('CheesePi')



def get_logger():
	return logger
def generate_secret():
	"""Make a secret for this node, to use in signing data dumps"""
	return str(uuid.uuid4())

def create_default_config():
	"""If config file does not exist, try to copy from default.
	   Also add a local secret to the file."""
	# is there already a local config file?
	if os.path.isfile(config_file):
		return

	logging.warning("Copying default config file to a local version")
	default_config = os.path.join(cheesepi_dir,"cheesepi.default.conf")
	# Can we find the default config file?
	if os.path.isfile(default_config):
		secret = generate_secret()
		try:
			copyfile(default_config, config_file, "_SECRET_", secret)
		except:
			msg = "Problem copying files - check permissions of %s" % cheesepi_dir
			logger.error(msg)
			exit(1)
	else:
		logger.error("Can not find default config file!")

def read_config():
	# ensure we have a config file to read
	create_default_config()
	try:
		fd = open(config_file)
		lines = fd.readlines()
		fd.close()
	except Exception as e:
		logger.error("Error: can not read config file: "+str(e))
		# should copy from default location!
		sys.exit(1)
	return lines


def get_config():
	config = {}
	lines  = read_config()
	for line in lines:
		# strip comment and badly formed lines
		if re.match('^\s*#', line) or not re.search('=',line):
			continue
		# logger.debug(line)
		(key, value) = line.split("=",1)
		config[clean(key)] = clean(value)
	config['cheesepi_dir'] = cheesepi_dir
	config['config_file']  = config_file
	config['version']      = version()
	return config

def main():
	from pprint import PrettyPrinter
	printer = PrettyPrinter(indent=4)
	printer.pprint(config)






def get_dao():
	if config_equal('database',"mongo"):
		return cp.storage.dao_mongo.DAO_mongo()
	elif config_equal('database',"influx"):
		return cp.storage.dao_influx.DAO_influx()
	elif config_equal('database',"mysql"):
		return cp.storage.dao_mysql.DAO_mysql()
	elif config_equal('database',"null"):
		return cp.storage.dao.DAO()
	# and so on for other database engines...

	msg = "Fatal error: 'database' type not set to a valid value in config file, exiting."
	logger.error("Database type: "+config['database']+"\n"+msg)
	exit(1)

def get_controller():
	if "controller" in config:
		return config['controller']
	else:
		return "http://cheesepi.sics.se"

def get_cheesepi_dir():
	return config['cheesepi_dir']

def make_databases():
	cmd = get_cheesepi_dir()+"/install/make_influx_DBs.sh"
	logger.warn("Making databases: "+cmd)
	os.system(cmd)


def set_last_updated(dao=None):
	if dao==None:
		dao = get_dao()
	dao.write_user_attribute("last_updated",cp.utils.now())

def get_last_updated(dao=None):
	"""When did we last update our code from the central server?"""
	if dao==None:
		dao = get_dao()
	last_updated = dao.read_user_attribute("last_updated")
	# convert to seconds
	return last_updated

def get_update_period():
	"""How frequently should we update?"""
	return 259200

def should_update(dao=None):
	"""Should we update our code?"""
	if not config_true('auto_update'):
		return False
	last_updated = get_last_updated(dao)
	update_period = get_update_period()
	if (last_updated < (cp.utils.now()-update_period)):
		return True
	return False


def set_last_dumped(dao=None):
	if dao==None:
		dao = get_dao()
	dao.write_user_attribute("last_dumped", cp.utils.now())

def get_last_dumped(dao=None):
	"""When did we last dump our data to the central server?"""
	if dao==None:
		dao = get_dao()
	last_dumped = dao.read_user_attribute("last_dumped")
	# convert to seconds
	return last_dumped

def get_dump_period():
	"""How frequently should we dump?"""
	return 86400

def should_dump(dao=None):
	"""Should we update our code?"""
	last_dumped = get_last_dumped(dao)
	dump_period = get_dump_period()
	if (last_dumped < (cp.utils.now()-dump_period)):
		return True
	return False


def copyfile(from_file, to_file, occurance, replacement):
	"""Copy a file <from_file> to <to_file> replacing all occurrences"""
	logger.info(from_file+" "+to_file+" "+ occurance+" "+ replacement)
	with open(from_file, "rt") as fin:
		with open(to_file, "wt") as fout:
			for line in fin:
				fout.write(line.replace(occurance, replacement))




def version():
	"""Which version of the code are we running?"""
	version="repos"
	try:
		fd = open(version_file)
		lines = fd.readlines()
		fd.close()
		version = lines[0].strip()
	except:
		logging.warning("No version file!")
	return version


def get(key):
	key = clean(key)
	if key in config:
		return config[key]
	return None

def get_landmarks():
	"""Who shall we ping/httping?"""
	if not config_defined('landmarks'):
		return []
	landmark_string = config['landmarks']
	landmarks = landmark_string.split()
	return landmarks


def config_defined(key):
	"""Is the specified key defined and true in the config object?"""
	key = clean(key)
	if key in config:
		return True
	return False

def config_equal(key, value):
	"""Is the specified key equal to the given value?"""
	key   = clean(key)
	value = clean(value)
	if key in config:
		if config[key]==value:
			return True
	return False

def config_true(key):
	"""Is the specified key defined and true in the config object?"""
	key = clean(key)
	if key in config:
		if config[key]=="true":
			return True
	return False

# see if we can grab a schedule from the central server
# this should (in future) include authentication
def load_remote_schedule():
	try:
		url = 'http://cheesepi.sics.se/schedule.dat'
		response = urllib2.urlopen(url)
		schedule = response.read()
		return schedule
	except urllib2.HTTPError as e:
		logger.error("The CheesePi controller server '%s' couldn\'t fulfill the request. Code: %s" % (url, str(e.code)))
	except urllib2.URLError as e:
		logger.error('We failed to reach the central server: '+e.reason)
	except:
		logger.error("Unrecognised problem when downloading remote schedule...")
	return None

# read config file
def load_local_schedule():
	filename = get_cheesepi_dir()+"/"+config['schedule']
	lines = []
	schedule = []

	with open(filename) as f:
		lines = f.readlines()

	for l in lines:
		if l=="" or l.startswith("#"):
			continue # skip this comment line
		try:
			spec = json.loads(l)
			schedule.append(spec)
		except:
			#logger.error("JSON task spec not parsed: "+l)
			pass
	return schedule



# clean the identifiers
def clean(id):
	return id.strip().lower()


# Some accounting to happen on every import (mostly for config file making)
config = get_config()


if __name__ == "__main__":
	main()
