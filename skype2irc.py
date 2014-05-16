#! /usr/bin/env python
# -*- coding: utf-8 -*-

# IRC ⟷  Skype Gateway Bot: Connects Skype Chats to IRC Channels
# Copyright (C) 2013  Märt Põder <mart.poder@p6drad-teel.net>
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

# *** This bot deliberately prefers IRC to Skype! ***

# Snippets from
#
#  Feebas Skype Bot (C) duxlol 2011 http://sourceforge.net/projects/feebas/
#  IRC on a Higher Level http://www.devshed.com/c/a/Python/IRC-on-a-Higher-Level/
#  Time until a date http://stackoverflow.com/questions/1580227/find-time-until-a-date-in-python

import sys, signal
import time, datetime
import string, textwrap
import json

from ircbot import SingleServerIRCBot
from irclib import ServerNotConnectedError
from threading import Timer

from config import config

import importlib
import logging

logging.basicConfig(level=logging.WARN,
					format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
					datefmt='%Y-%m-%d %H:%M:%S')

version = "0.22"

servers = config['servers']

nick = config['nick']
botname = config['botname'].decode("UTF-8")
password = config['password']
vhost = config['vhost']

mirrors = config['mirrors']

modconfig = config['modules']

max_irc_msg_len = 442
ping_interval = 2*60
reconnect_interval = 30

# to avoid flood excess
max_seq_msgs = 2
delay_btw_msgs = 0.35
delay_btw_seqs = 0.15

preferred_encodings = ["UTF-8", "CP1252", "ISO-8859-1"]

name_start = "<".decode('UTF-8') # "<"
name_end = ">".decode('UTF-8') # ">"
emote_char = "*".decode('UTF-8') # "*"

muted_list_filename = nick + '.%s.muted'

usemap = {}
bot = None
mutedl = {}
lastsaid = {}

pinger = None
bot = None

wrapper = textwrap.TextWrapper(width=max_irc_msg_len - 2)
wrapper.break_on_hyphens = False

# Time consts
SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR
MONTH = 30 * DAY

def get_relative_time(dt):
	"""Returns relative time compared to now from timestamp"""
	now = datetime.datetime.now()
	delta_time = now - dt

	delta =  delta_time.days * DAY + delta_time.seconds 
	minutes = delta / MINUTE
	hours = delta / HOUR
	days = delta / DAY

	if delta <= 0:
		return "in the future"
	if delta < 1 * MINUTE: 
	  if delta == 1:
		  return  "moment ago"
	  else:
		  return str(delta) + " seconds ago"
	if delta < 2 * MINUTE:    
		return "a minute ago"
	if delta < 45 * MINUTE:    
		return str(minutes) + " minutes ago"
	if delta < 90 * MINUTE:    
		return "an hour ago"
	if delta < 24 * HOUR:
		return str(hours) + " hours ago"
	if delta < 48 * HOUR:    
		return "yesterday"
	if delta < 30 * DAY:    
		return str(days) + " days ago"
	if delta < 12 * MONTH:    
		months = delta / MONTH
		if months <= 1:
			return "one month ago"
		else:
			return str(months) + " months ago"
	else:    
	  years = days / 365.0
	  if  years <= 1:
		  return "one year ago"
	  else:
		  return str(years) + " years ago"

def cut_title(title):
	"""Cuts Skype chat title to be ok"""
	newtitle = ""
	for chunk in title.split():
		newtitle += chunk.strip(string.punctuation) + " "
		if len(newtitle) > 10:
			break
	return newtitle.strip()

def irc_wrap(prefix, items, sep=u', ', natural=True):
	"""
	Returns a list of strings that efficiently utilize IRC message size for displaying large lists.
	
	prefix (unicode): A prefix for the list, which is included obeying size limits
	items (list of unicode): Items to join
	sep (unicode): Separator to use between items
	natural (bool): If true, add "and" to the last item to match the natural English written list form.
	
	Note: this may not obey size limits for multi-byte encoding schemes like UTF-8.
	"""
	parts=[]
	buf=prefix
	items=list(items)
	while items:
		item=items.pop(0)
		if items:
			part=unicode(item)+sep
		else:
			if natural:
				part=u'and '+unicode(item)
			else:
				part=unicode(item)
		while len(buf)>max_irc_msg_len:
			parts.append(buf[:max_irc_msg_len])
			buf=buf[max_irc_msg_len:]
		if len(buf)+len(part)>max_irc_msg_len:
			parts.append(buf)
			buf=part
		else:
			buf=buf+part
	parts.append(buf)
	return parts

def load_mutes():
	"""Loads people who don't want to be broadcasted from IRC to Skype"""
	for channel in mirrors.keys():
		mutedl[channel] = []
		try:
			f = open(muted_list_filename % channel, 'r')
			for line in f.readlines():
				name = line.rstrip("\n")
				mutedl[channel].append(name)
				mutedl[channel].sort()
			f.close()
			print 'Loaded list of ' + str(len(mutedl[channel])) + ' mutes for ' + channel + '!'
		except:
			pass

def save_mutes(channel):
	"""Saves people who don't want to be broadcasted from IRC to Skype"""
	try:
		f = open(muted_list_filename % channel, 'w')
		for name in mutedl[channel]:
			f.write(name + '\n')
		mutedl[channel].sort()
		f.close
		print 'Saved ' + str(len(mutedl[channel])) + ' mutes for ' + channel + '!'
	except:
		pass

def OnMessageStatus(Message, Status):
	"""Create Skype object listener"""
	raw = Message.Body
	msgtype = Message.Type
	chat = Message.Chat
	send = chat.SendMessage
	senderDisplay = Message.FromDisplayName
	senderHandle = Message.FromHandle

	# Only react to defined chats
	if chat in usemap:
		if Status == 'RECEIVED':
			if msgtype == 'EMOTED':
				bot.say(usemap[chat], emote_char + u" " + senderDisplay + u" " + raw)
			elif msgtype == 'SAID':
				bot.say(usemap[chat], name_start + senderDisplay + name_end + u" " + raw)
				for modname in modules:
					modules[modname].skype_msg(senderHandle, senderDisplay, chat, raw)

def decode_irc(raw, preferred_encs = preferred_encodings):
	"""Heuristic IRC charset decoder"""
	changed = False
	for enc in preferred_encs:
		try:
			res = raw.decode(enc)
			changed = True
			break
		except:
			pass
	if not changed:
		try:
			import chardet
			enc = chardet.detect(raw)['encoding']
			res = raw.decode(enc)
		except:
			res = raw.decode(enc, 'ignore')
			#enc += "+IGNORE"
	return res

def signal_handler(signal, frame):
	print "Ctrl+C pressed!"
	if pinger is not None:
		print "Cancelling the pinger..."
		pinger.cancel()
	print 'Cleaning up modules...'
	for modname in modules.copy(): #Note the shallow copy to avoid modify-on-iterate
		if hasattr(module[modname], 'finish'):
			module[modname].finish()
		del modules[modname]
	if bot is not None:
		print "Killing the bot..."
		for dh in bot.ircobj.handlers["disconnect"]:
			bot.ircobj.remove_global_handler("disconnect", dh[1])
		if len(bot.ircobj.handlers["disconnect"]) == 0:
			print "Finished."
			bot.die()

class MirrorBot(SingleServerIRCBot):
	"""Create IRC bot class"""

	def __init__(self):
		SingleServerIRCBot.__init__(self, servers, nick, (botname).encode("utf-8"), reconnect_interval)

	def start(self):
		"""Override default start function to avoid starting/stalling the bot with no connection"""
		while not self.connection.is_connected():
			self._connect()
			if not self.connection.is_connected():
				time.sleep(self.reconnection_interval)
				self.server_list.append(self.server_list.pop(0))
		SingleServerIRCBot.start(self)

	def routine_ping(self, first_run = False):
		"""Ping server to know when try to reconnect to a new server."""
		global pinger
		if not first_run and not self.pong_received:
			print "Ping reply timeout, disconnecting from", self.connection.get_server_name()
			self.disconnect()
			return
		self.pong_received = False
		self.connection.ping(self.connection.get_server_name())
		pinger = Timer(ping_interval, self.routine_ping, ())
		pinger.start()

	def on_pong(self, connection, event):
		"""React to pong"""
		self.pong_received = True

	def say(self, target, msg, do_say = True):
		"""Send messages to channels/nicks"""
		try:
			lines = msg.split("\n")
			cur = 0
			for line in lines:
				for irc_msg in wrapper.wrap(line.strip("\r")):
					print target, irc_msg
					irc_msg += "\r\n"
					if target not in lastsaid.keys():
						lastsaid[target] = 0
					while time.time()-lastsaid[target] < delay_btw_msgs:
						time.sleep(0.2)
					lastsaid[target]=time.time()
					if do_say:
						self.connection.privmsg(target, irc_msg)
					else:
						self.connection.notice(target, irc_msg)
					cur += 1
					if cur % max_seq_msgs == 0:
						time.sleep(delay_btw_seqs) # to avoid flood excess
		except ServerNotConnectedError:
			print "{" +target + " " + msg+"} SKIPPED!"
			
	def notice(self, target, msg):
		"""Send notices to channels/nicks"""
		self.say(self, target, msg, False)

	def on_welcome(self, connection, event):
		"""Do stuff when when welcomed to server"""
		print "Connected to", self.connection.get_server_name()
		if password is not None:
			bot.say("NickServ", "identify " + password)
		if vhost:
			bot.say("HostServ", "ON")
			time.sleep(1)
		# ensure handler is present exactly once by removing it before adding
		self.connection.remove_global_handler("ctcp", self.handle_ctcp)
		self.connection.add_global_handler("ctcp", self.handle_ctcp)
		time.sleep(3) #This appears to be a bug on certain IRC servers with +r mode support
					  #Delay joins until we're confident NickServ has given us necessary modes
					  #TODO: Hangs main thread
		for pair in mirrors:
			connection.join(pair)
			print "Joined " + pair
		self.routine_ping(first_run = True)

	def on_pubmsg(self, connection, event):
		"""React to channel messages"""
		args = event.arguments()
		source = event.source().split('!')[0]
		target = event.target().lower()
		cmds = args[0].split()
		if cmds and cmds[0].rstrip(":,") == nick:
			if len(cmds)==2:
				if cmds[1].upper() == 'ON' and source in mutedl[target]:
					mutedl[target].remove(source)
					save_mutes(target)
				elif cmds[1].upper() == 'OFF' and source not in mutedl[target]:
					mutedl[target].append(source)
					save_mutes(target)
			return
		if not mutedl.has_key(target) or source in mutedl[target]:
			return
		msg_hdr = name_start + source + name_end + " "
		msg_body = ''
		for raw in args:
			msg_body += decode_irc(raw) + "\n"
		msg_body = msg_body.rstrip("\n")
		print cut_title(usemap[target].FriendlyName), msg_hdr + msg_body
		usemap[target].SendMessage(msg_hdr + msg_body)
		for modname in modules:
			modules[modname].irc_msg(source, target, msg_body)

	def handle_ctcp(self, connection, event):
		"""Handle CTCP events for emoting"""
		args = event.arguments()
		source = event.source().split('!')[0]
		target = event.target().lower()
		if target in mirrors.keys():
			if source in mutedl[target]:
				return
		if args[0]=='ACTION' and len(args) == 2 and target in usemap:
			# An emote/action message has been sent to us
			msg = emote_char + " " + source + " " + decode_irc(args[1]) + "\n"
			print cut_title(usemap[target].FriendlyName), msg
			usemap[target].SendMessage(msg)

	def on_privmsg(self, connection, event):
		"""React to ON, OF(F), ST(ATUS), IN(FO) etc for switching gateway (from IRC side only)"""
		source = event.source().split('!')[0]
		raw = event.arguments()[0].decode('utf-8', 'ignore')
		args = raw.split()
		if not args:
			return
		two = args[0][:2].upper()
		
		if two == 'ST': # STATUS
			muteds = []
			brdcsts = []
			for channel in mirrors.keys():
				if source in mutedl[channel]:
					muteds.append(channel)
				else:
					brdcsts.append(channel)
			if len(brdcsts) > 0:
				bot.say(source, "You're mirrored to Skype from " + ", ".join(brdcsts))
			if len(muteds) > 0:
				bot.say(source, "You're silent to Skype on " + ", ".join(muteds))
				
		if two == 'OF': # OFF
			for channel in mirrors.keys():
				if source not in mutedl[channel]:
					mutedl[channel].append(source)
					save_mutes(channel)
			bot.say(source, "You're silent to Skype now")
				
		elif two == 'ON': # ON
			for channel in mirrors.keys():
				if source in mutedl[channel]:
					mutedl[channel].remove(source)
					save_mutes(channel)
			bot.say(source, "You're mirrored to Skype now")
				
		elif two == 'IN' and len(args) > 1 and args[1] in mirrors: # INFO
			chat = usemap[args[1]]
			members = chat.Members
			active = chat.ActiveMembers
			msg = args[1] + " ⟷  \"".decode("UTF-8") + chat.FriendlyName + "\" (%d/%d)\n" % (len(active), len(members))
			# msg += chat.Blob + "\n"
			userList = []
			for user in members:
				if user in active:
					desc = " * " + user.Handle + " [" + user.FullName
				else:
					desc = " - " + user.Handle + " [" + user.FullName
				#print user.LastOnlineDatetime
				last_online = user.LastOnline
				timestr = ""
				if last_online > 0:
					timestr += " --- " + get_relative_time(datetime.datetime.fromtimestamp(last_online))
				mood = user.MoodText
				if len(mood) > 0:
					desc += ": \"" + mood + "\""
				desc += "]" + timestr
				userList.append(desc)
			userList.sort()
			bot.say(source, u'\n'.join(irc_wrap(msg, userList)))
			
		elif two in ('?', 'HE', 'HI', 'WT'): # HELP
			bot.say(source, botname + " " + version + " " + "\n * ON/OFF/STATUS --- Trigger mirroring to Skype\n * INFO #channel --- Display list of users from relevant Skype chat\nDetails: https://github.com/boamaod/skype2irc#readme")

# *** Start everything up! ***

signal.signal(signal.SIGINT, signal_handler)

print "Running", botname, "Gateway Bot", version
try:
	import Skype4Py
except:
	print 'Failed to locate Skype4Py API! Quitting...'
	sys.exit()
try:
	skype = Skype4Py.Skype();
except:
	print 'Cannot open Skype API! Quitting...'
	sys.exit()

if skype.Client.IsRunning:
	print 'Skype process found!'
elif not skype.Client.IsRunning:
	try:
		print 'Starting Skype process...'
		skype.Client.Start()
	except:
		print 'Failed to start Skype process! Quitting...'
		sys.exit()

try:
	skype.Attach();
	skype.OnMessageStatus = OnMessageStatus
except:
	print 'Failed to connect! You have to log in to your Skype instance and enable access to Skype for Skype4Py! Quitting...'
	sys.exit()

print 'Skype API initialised.'

for pair in mirrors:
	chat = skype.CreateChatUsingBlob(mirrors[pair])
	topic = chat.FriendlyName
	print "Joined \"" + topic + "\""
	usemap[pair] = chat
	usemap[chat] = pair

load_mutes()

bot = MirrorBot()

# module API:
# main module sets config, usemap, and irc_say
# on Skype msg, main module calls module.skype_msg(senderDisplay, senderHandle, chat, msg)
# on IRC msg, main module calls module.irc_msg(source, target, msg)

modules = {}
for modname in modconfig:
	try:
		module = importlib.import_module(modname)
		module.config = modconfig[modname]
		module.usemap = usemap
		module.ircbot = bot
		if hasattr(module, 'init'):
			module.init()
		modules[modname] = module
		logging.info('Loaded module %s' % modname)
	except:
		logging.error('Failed to load module %s!' % modname)

print "Starting IRC bot..."
bot.start()
