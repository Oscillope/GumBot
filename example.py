# example GumBot module

config = None
usemap = None
ircbot = None

def irc_msg(source, target, msg):
	usemap[target].SendMessage('EXAMPLE: IRC msg %s -> %s: %s' % (source, target, msg))
	print 'EXAMPLE: IRC msg %s -> %s: %s' % (source, target, msg)

def skype_msg(sourceDisplay, sourceHandle, target, msg):
	ircbot.say(usemap[target], 'EXAMPLE: Skype msg %s (%s) -> %s: %s' % (sourceHandle, sourceDisplay, target, msg))
	print 'EXAMPLE: Skype msg %s (%s) -> %s: %s' % (sourceHandle, sourceDisplay, target, msg)
