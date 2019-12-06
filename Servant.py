#!/usr/bin/env python3
# -*- coding: utf-8; mode: python; -*-
import Ice
import IceStorm
Ice.loadSlice('downloader.ice')
import os.path
from threading import Thread
from queue import Queue
import sys
import youtube_dl
from Downloader import *
import binascii
from Library import *

KEY = 'Youtube.IceStorm/TopicManager'

class Server(Ice.Application):
	def get_topic_manager(self):

		proxy = self.communicator().stringToProxy(KEY)
		if proxy is None:
			print("property '{}' not set".format(KEY))
			return None

		print("Using IceStorm in: '%s'" % KEY)
		return IceStorm.TopicManagerPrx.checkedCast(proxy)

	def run(self, argv):
		ic = self.communicator()
		servant = ic.createObjectAdapter("FactoryAdapter")
		topic_mgr = self.get_topic_manager()
		if not topic_mgr:
			print("Invalid proxy")
			return 2

		escuchar = servant.add(SchedulerFactoryI(servant, topic_mgr), self.communicator().stringToIdentity("servidor"))

		print('-----------------------------------------')
		print('PRX: ', escuchar)
		print('-----------------------------------------')

		servant.activate()
		self.shutdownOnInterrupt()
		ic.waitForShutdown()

		return 0

server = Server()
sys.exit(server.main(sys.argv))
