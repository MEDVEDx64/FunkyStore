config = {
	"port": 8000,
	"host": "localhost:8000",
	"dbUri": "mongodb://192.168.56.101",

	"rconServer": {
		"host": "pyroland.who",
		"port": 25575,
		"password": "meinkraft68"
	},

	"store": {
		"maxAmount": 256
	},

	"markets": {
		"googleMapUri": "https://themassacre.org/doktor/",
		"googleMapLayerName": "doktor"
	},

	"mining": {
		"enabled": False,
		"instanceCode": "editme", # must be 6 chars long, case-insensitive letters or digits
		"reward": 100.0,

		"allowDynamicReward": False, # reward will be lowered depending on mined codes redemption frequency
		"rewardCorrectionInterval": 15 # seconds
	},

	# voucher processor settings
	"magic": {
		"fileUploadEnabled": False,
		"maxLinesPerFile": 1024
	}
}
