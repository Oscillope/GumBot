'''
Authentication Interface

Modules which support authentication should adhere to (and feel free to utilize)
the interfaces and protocols defined here. These modules should also:
-Register themselves as an authenticator in init().
-Unregister themselves in finish().
-Be aware of the fact that they may work alongside other (possibly very different)
 authenticators, so their say isn't final (though the user's is :P)

The general support classes are as follows:
-PermNode represents a "permission node," an atom which may be tested against
 another such node to determine whether or not it applies. In general, the
 testing node is part of an access control, and the tested node is a permission
 required to access something. Nodes are represented in string form as a hierarchy
 of a.b.c where the components may be any strings (though they should be lowercase
 words) and where basic shell-like patterns (using fnmatch--*, ?, [], etc.) are
 supported. Additionally, if a component is **, the match applies recursively down
 the entire node. (For example, "auth.*" matches "auth.set" but not "auth.get.status",
 whereas "auth.**" matches both.)
-ACL is an access control list, consisting of a sequence of sets. Even indices
 represent allowed permissions, whereas odd indices represent denied permissions,
 both in order of increasing priority (complete omission represents denial). That
 is, a permission is allowed if it has a match in 0, but not if a match is found
 in 1, but again allowed if a match is in 2, and so on. The primary feature of an
 ACL is that it may be converted to and loaded from a string format.
-Token represents several laterally-merged ACLs. A Token is typically generated by
 pooling ACLs from various sources, such as per-user and per-group permissions.
 Because they are transient, they do not support serialization.
-Session represents a session. Sessions contain a Token and whatever other data
 an authenticator wishes to associate with them.
-Context represents a user context. It contains information that hopefully allows
 the authenticator to differentiate request sources (and sessions). The .username
 is unique per-connection, but may not be authentic on some media (like IRC).
 Other attributes are given on a basis of availability.

Finally, a module must implement the following interfaces:
-IAuthenticator, the Authenticator interface, represents the primary entry point.
 It must define the following:
 -.Recognize(ctx): Given a Context (see), return a Session (see). The Session may
  change, as needed, if the Context re-identifies.
'''

import fnmatch

class PermNode(object):
	def __init__(self, *pspecs):
		self.parts=[]
		for spec in pspecs:
			self.parts.extend(permspec.split('.'))
	def __str__(self):
		return '.'.join(self.parts)
	def __repr__(self):
		return '<Permission %s>'%(self,)
	def IsGlob(self):
		return any(['*' in i for i in self.parts])
	def Apply(self, node):
		for i in xrange(min(len(self.parts), len(node.parts))):
			spart=self.parts[i]
			npart=node.parts[i]
			if spart=='**': #Recursively applied
				return True
			elif not fnmatch.fnmatch(npart, spart):
				return False #Did not apply
		if len(self.parts)>len(node.parts):
			return False #Not specific enough, did not recurse
		else:
			return True #Tested against a general node
			
class ACL(object):
	def __init__(self, aspec):
		priorities=aspec.split(';')
		self.priorities=[]
		for pris in priorities:
			self.priorities.append(set([PermNode(i) for i in pris.split(',')]))
	def __str__(self):
		return ';'.join([','.join([str(j) for j in i]) for i in self.priorities])
	def FindLevel(self, node):
		i=-1
		for priset in self.priorities:
			for perm in priset:
				if perm.Apply(node):
					i+=1
					break
			else:
				return i
		#No further priority sets, assume the last level
		return i
	def Apply(self, node):
		#This works, even when level == -1
		return self.FindLevel(node)%2==0
		
class Token(object):
	def __init__(self, *acls):
		self.acls=acls
	def Apply(self, node):
		return max([i.FindLevel(node) for i in self.acls])%2==0
		
class Session(object):
	def __init__(self, token):
		self.token=token
	def Apply(self, node):
		return self.token.Apply(node)

class Context(object):
	def __init__(self, username):
		self.username=username
		
class SkypeContext(Context):
	def __init__(self, username, displayname, chat=None):
		Context.__init__(self, username)
		self.displayname=displayname
		self.chat=chat
		
class IRCContext(Context):
	def __init__(self, username, channel=None):
		Context.__init__(self, username)
		self.channel=channel

class IAuthenticator(object):
	def 
