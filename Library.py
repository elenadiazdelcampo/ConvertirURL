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

class NullLogger:
	def debug(self, msg):
		'''Ignore debug messages'''

	def warning(self, msg):
		'''Ignore warnings'''

	def error(self, msg):
		'''Ignore errors'''


# Default configuration for youtube-dl
DOWNLOADER_OPTS = {
	'format': 'bestaudio/best',
	'postprocessors': [{
	'key': 'FFmpegExtractAudio',
	'preferredcodec': 'mp3',
	'preferredquality': '192',
	}],
	'logger': NullLogger()
}


def _download_mp3_(url, destination='./'):
	options = {}
	task_status = {}

	def progress_hook(status):
		task_status.update(status)

	options.update(DOWNLOADER_OPTS)
	options['progress_hooks'] = [progress_hook]
	options['outtmpl'] = os.path.join(destination, '%(title)s.%(ext)s')
	with youtube_dl.YoutubeDL(options) as ydl:
		ydl.download([url])
	filename = task_status['filename']
	# BUG: filename extension is wrong, it must be mp3
	filename = filename[:filename.rindex('.') + 1]
	return filename + options['postprocessors'][0]['preferredcodec']


class WorkQueue(Thread):
	'''Job Queue to dispatch tasks'''
	QUIT = 'QUIT'
	CANCEL = 'CANCEL'

	def __init__(self, server):
		super(WorkQueue, self).__init__()
		self.server = server
		self.queue = Queue()

	def run(self):
		'''Task dispatcher loop'''
		for job in iter(self.queue.get, self.QUIT):
			job.download()
			self.queue.task_done()

		self.queue.task_done()
		self.queue.put(self.CANCEL)

		for job in iter(self.queue.get, self.CANCEL):
			job.cancel()
			self.queue.task_done()

		self.queue.task_done()

	def send_status(self, url, status):
		status_data = ClipData()
		status_data.URL = url
		status_data.status = status
		self.server.syncClient.notify(status_data)

	def add(self, callback, url):
		'''Add new task to queue'''
		self.send_status(url, Status.PENDING)
		self.queue.put(Job(callback, url, self))

	def destroy(self):
		'''Cancel tasks queue'''
		self.queue.put(self.QUIT)
		self.queue.join()


class Job:
	def __init__(self, call, url, work_queue):
		self.call = call
		self.url = url
		self.work_queue = work_queue

	def download(self):
		self.work_queue.send_status(self.url, Status.INPROGRESS)
		result = _download_mp3_(self.url)
		self.work_queue.server.localList.add(result)
		self.work_queue.send_status(self.url, Status.DONE)
		self.call.set_result(result)

	def cancel(self):
		self.work_queue.send_status(self.url, Status.ERROR)
		self.call.ice_exception(SchedulerCancelJob())


class TransferI(Transfer):
	def __init__(self, local_filename):
		self.file_contents = open(local_filename, 'rb')

	def recv(self, size, current=None):
		'''Send data block to client'''
		return str(
			binascii.b2a_base64(self.file_contents.read(size), newline=False)
			)

	def end(self, current=None):
		'''Close transfer and free objects'''
		self.file_contents.close()
		current.adapter.remove(current.id)

class DownloadSchedulerI(DownloadScheduler, SyncEvent):
	def __init__(self, name):
		print('Creando objeto ', name, '...')
		self.localList = set()
		self.name = name
		self.path = "./"
		self.syncTimer = None
		self.syncClient = None
		self.jobQueue = WorkQueue(self)
		self.jobQueue.start()

	def getSongList(self, current=None):
		return list(self.localList)

	def addDownloadTask(self, url, current=None):
		print(self.name, ': añadiendo tarea...')
		call = Ice.Future()
		self.jobQueue.add(call, url)

		return call

	def get(self, song, current=None):
		print(self.name, ': transfiriendo...')
		return TransferPrx.checkedCast(current.adapter.addWithUUID(TransferI(os.path.join(self.path, song))))

	def requestSync(self, current=None):
		self.syncTimer.notify(list(self.localList))

	def notify(self, globalList, current=None):
		self.localList=self.localList.union(set(globalList))



class SchedulerFactoryI(SchedulerFactory):
	def __init__(self, servant, topic_mgr):
		self.stopic = None
		self.ptopic = None
		self.cont = 0
		self.adapters = []
		self.name_actives = []
		self.servant = servant
		try:
			self.ptopic = topic_mgr.retrieve("ProgressTopic")
		except IceStorm.NoSuchTopic:
			self.ptopic = topic_mgr.create("ProgressTopic")
		try:
			self.stopic = topic_mgr.retrieve("SyncTopic")
		except IceStorm.NoSuchTopic:
			self.stopic = topic_mgr.create("SyncTopic")

	def make(self, name, current=None):
		if name in self.name_actives:
			raise SchedulerAlreadyExists()
		new = self.generarYoutube(name, current.adapter)
		return new


	def generarYoutube(self, name, adapter,current=None):
		self.name_actives.append(name)
		iceId = Ice.stringToIdentity(name)
		prx = DownloadSchedulerI(name)
		proxy = adapter.add(prx, iceId)
		sync = self.stopic.subscribeAndGetPublisher({}, proxy)
		self.adapters.append(sync)
		prx.syncTimer = SyncEventPrx.uncheckedCast(sync)
		pgrproxy = self.ptopic.getPublisher()
		prx.syncClient = ProgressEventPrx.uncheckedCast(pgrproxy)
		self.cont = self.cont + 1

		return DownloadSchedulerPrx.checkedCast(proxy)


	def availableSchedulers(self, current=None):
		return self.cont

	def eliminarAdapter(self,name,adapter, current =None):
		j = 0
		kill = False
		for i in range(0, len(self.adapters)):
			if self.name_actives[i] == name:
				adapter.remove(Ice.stringToIdentity(name))
				j = i
				kill = True
		if kill:
			self.stopic.unsubscribe(self.adapters[j])
			del (self.adapters[j])
			del (self.name_actives[j])
			self.cont = self.cont - 1

	def kill(self, name, current=None):
		if not(name in self.name_actives):
			raise SchedulerNotFound()
		self.eliminarAdapter(name, current.adapter)
