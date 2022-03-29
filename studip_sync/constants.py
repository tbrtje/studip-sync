from studip_sync.logins import LoginPreset
from studip_sync.logins.general import GeneralLogin

URL_BASEURL_DEFAULT = "https://studip.ibs-ol.de"
CONFIG_FILENAME = "config.json"
LOGIN_PRESETS = [
    LoginPreset(name="IBS Oldenburg", base_url="https://studip.ibs-ol.de",
                auth_type="general", auth_data={}
                ),
]
AUTHENTICATION_TYPES = {"general": GeneralLogin}
AUTHENTICATION_TYPE_DEFAULT = "general"
AUTHENTICATION_TYPE_DATA_DEFAULT = {}
