"""Constants for LG webOS Extras."""

from __future__ import annotations

DOMAIN = "lg_webos_extras"

CONF_TV_ENTITY = "tv_entity"
CONF_WARNING = "warning"
CONF_APPS = "apps"
CONF_SCREEN_OFF_SEQ = "screen_off_sequence"
CONF_FIRETV_ENTITY = "firetv_entity"
CONF_FIRETV_INPUT = "firetv_input"
CONF_FIRETV_APPS = "firetv_apps"

FIRE2MQTT_DOMAIN = "fire2mqtt"
FIRE2MQTT_DEFAULT_PREFIX = "fire2mqtt"
# "Name=package" pairs, comma separated.
DEFAULT_FIRETV_APPS = "Netflix=com.netflix.ninja, HBO Max=com.wbd.stream, TiviMate=ar.tvplayer.tv"
MACRO_KEY_DELAY = 0.7  # seconds between key presses

# Used to pick default apps from the TV source list when none are configured.
DEFAULT_APP_KEYWORDS = ("netflix", "hbo", "tivimate")
DEFAULT_APP_EXACT = ("max",)

WEBOSTV_DOMAIN = "webostv"

# Sleep timer presets (minutes). "off" = timer not running.
SLEEP_OFF = "off"
SLEEP_PRESETS = ["15", "30", "45", "60", "90", "120", "180"]
SLEEP_OPTIONS = [SLEEP_OFF, *SLEEP_PRESETS]

# Seconds before turning off when a warning toast is shown on the TV.
WARNING_SECONDS = 60

# Remote buttons: (webOS key, enabled by default)
REMOTE_BUTTONS: list[tuple[str, bool]] = [
    ("HOME", True),
    ("BACK", True),
    ("EXIT", True),
    ("MENU", True),
    ("QMENU", True),
    ("INFO", True),
    ("UP", True),
    ("DOWN", True),
    ("LEFT", True),
    ("RIGHT", True),
    ("ENTER", True),
    ("VOLUMEUP", True),
    ("VOLUMEDOWN", True),
    ("MUTE", True),
    ("CHANNELUP", True),
    ("CHANNELDOWN", True),
    ("PLAY", True),
    ("PAUSE", True),
    ("STOP", False),
    ("REWIND", False),
    ("FASTFORWARD", False),
    ("GUIDE", False),
    ("LIST", False),
    ("RED", False),
    ("GREEN", False),
    ("YELLOW", False),
    ("BLUE", False),
    ("ASTERISK", False),
    ("DASH", False),
    ("CC", False),
    ("NETFLIX", False),
    ("AMAZON", False),
    *[(str(n), False) for n in range(10)],
]

# Known webOS sound outputs (the current one from the TV is always added too).
SOUND_OUTPUTS = [
    "tv_speaker",
    "external_arc",
    "external_optical",
    "bt_soundbar",
    "tv_external_speaker",
    "tv_speaker_headphone",
    "headphone",
    "lineout",
]
