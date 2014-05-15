import re

usemap=None
config=None
ircbot=None

KARMA_RE=re.compile(r'([a-zA-Z0-9_]+|\[.*?\]|\(.*?\))(\+\+|--)[ ]*(#|//)?')

def irc_msg(source, target, msg):
	pass
	
def skype_msg(sourcedisp, source, target, msg):
	if usemap[target]:
		match=KARMA_RE.match(msg)
		if match:
			print 'Karma RE match:', match.group(1, 2, 3)
			if match.group(3):
				ircbot.say(usemap[target], msg+' (behalf of %s)'%(sourcedisp,))
			else:
				ircbot.say(usemap[target], msg+'#behalf of %s'%(sourcedisp,))
