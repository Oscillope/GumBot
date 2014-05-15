# GumBot config file

config = {
	"servers": [("irc.IRCHighway.net", 6667)],
	"nick": "RoBot",
	"botname": "RoBot",
	"password": "robotnik",
	"vhost": False,
	"mirrors": {
		"#channel": "blob"
	},
	"modules": {
#        "example": {},
#        "quotes": {"url": "", "http-user": "", "http-pass": "", "channels": ["#example"]},
		"inject": {"path": {"inject": "./run/inject", "inspect": "./run/inspect"}, "wait": {"initial": 10, "update": 10}},
		"spikebot": {},
	}
}
