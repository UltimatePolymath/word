class Config(object):
    LOGGER = True

    # Get this value from my.telegram.org/apps
    OWNER_ID = "6765826972"
    sudo_users = "6845325416", "6765826972"
    GROUP_ID = -1002501304890
    TOKEN = "7507037404:AAHQkZN9UPmIWGIR48QnOI2pn4IF8YsuZI8"
    mongo_url = "mongodb+srv://worker:TFqF209jhTbnWDAN@cluster0.if6ahq2.mongodb.net/?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
    PHOTO_URL = ["https://telegra.ph/file/b925c3985f0f325e62e17.jpg", "https://telegra.ph/file/4211fb191383d895dab9d.jpg"]
    SUPPORT_CHAT = "+9y7_hAj6wpMyZGZl"
    UPDATE_CHAT = "+2wCcFlLzGY83Nzll"
    BOT_USERNAME = "sincatcherbot"
    CHARA_CHANNEL_ID = "-1002575869195"
    api_id = 26626068
    api_hash = "bf423698bcbe33cfd58b11c78c42caa2"

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
