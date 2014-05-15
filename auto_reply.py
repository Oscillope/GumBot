#Bot will auto-respond to lines containing a specified regex
#I <3 PR

import re

config = None
usemap = None
ircbot = None

#put the regex you want here 
my_exp = re.compile('')

#put the message to auto-respond with here
#suggestion: "Just ignore her."
my_response = ''

def message_scan(source, msg):
	msg = msg.strip()
	ismatch = my_exp.match(msg)
	if ismatch: 
		return source + ": " + my_response

def irc_msg(source, target, msg):
	if not target in config['channels']:
		return
	scanner = message_scan(source, msg)
	if scanner and target in config['channels']:
		ircbot.say(target, scanner)
		usemap[target].SendMessage(scanner)

def skype_msg(sourceDisplay, sourceHandle, target, msg):
	scanner = message_scan(sourceDisplay, msg)
	if scanner and usemap[target] in config['channels']:
		ircbot.say(usemap[target], scanner)
		target.SendMessage(scanner)