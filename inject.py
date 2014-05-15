import os
import string
from threading import Timer, Thread

usemap=None
config=None
ircbot=None

inspectors={}
injectors={}

class FIFOWatcher(Thread):
	def __init__(self, name):
		Thread.__init__(self)
		self.daemon=True
		self.path=os.path.join(config['path'][self.TYPE], name)
		if os.path.exists(self.path):
			os.unlink(self.path)
		print 'FIFO: Making a FIFO at', self.path
		self.working=True
		try:
			os.mkfifo(self.path)
		except IOError:
			print 'FIFO: FAILED!'
			self.working=False
		
class Injector(FIFOWatcher):
	TYPE='inject'
	def run(self):
		while self.working: #Run this thread forever
			f=open(self.path, 'rb', 0)
			print 'Injection: opened', self.path
			while True: #Listen while still open (python do-while)
				data=f.readline()
				if not data:
					break
				self.inject(data)
			print 'Injection: closed', self.path
			f.close()
	def inject(self, data):
		raise NotImplementedError('Injector is an ABC!')
		
class SkypeInjector(Injector):
	def __init__(self, skypeobj):
		Injector.__init__(self, cut_title(skypeobj.FriendlyName))
		self.skypeobj=skypeobj
	def inject(self, data):
		self.skypeobj.SendMessage(data)
		
class IRCInjector(Injector):
	def __init__(self, channel):
		Injector.__init__(self, channel)
		self.channel=channel
	def inject(self, data):
		ircbot.say(self.channel, data)
		
class Inspector(FIFOWatcher):
	TYPE='inspect'
	def run(self):
		while self.working:
			self.open=False
			self.f=open(self.path, 'wb', 0)
			print 'Inspection: opened', self.path
			self.open=True
			while self.open:
				time.sleep(0.5)
			print 'Inspection: closed', self.path
			self.f.close()
	def emit(self, data):
		if getattr(self, 'open', False):
			try:
				self.f.write(data.encode('UTF-8', 'replace'))
			except IOError:
				self.open=False
		

#Shamelessly borrowed from the main module
def cut_title(title):
	"""Cuts Skype chat title to be ok"""
	newtitle = ""
	for chunk in title.split():
		newtitle += chunk.strip(string.punctuation) + " "
		if len(newtitle) > 10:
			break
	return newtitle.strip()

def init():
	inspectors['SKYPE']=Inspector('SKYPE')
	inspectors['SKYPE'].start()
	Timer(config['wait']['initial'], create_pipes).start()

def create_pipes():
	for key in usemap:
		value=usemap[key]
		if isinstance(value, str): #blob -> IRC channel
			if value not in inspectors:
				inspectors[value]=Inspector(value)
				inspectors[value].start()
			if value not in injectors:
				injectors[value]=IRCInjector(value)
				injectors[value].start()
		else: #Skype object
			if value not in injectors:
				injectors[value]=SkypeInjector(value)
				injectors[value].start()
	Timer(config['wait']['update'], create_pipes).start()
	
def irc_msg(source, target, msg):
	if target in inspectors:
		inspectors[target].emit('%s %s %s\n'%(target, source, msg))

def skype_msg(sourcedisp, source, target, msg):
	inspectors['SKYPE'].emit('%s %s (%s) %s\n'%(target, sourcedisp, source, msg))
