DOMAIN = "dmx_monitor"
VERSION = "0.14.1"

CONF_INTERFACE = "interface"
CONF_UNIVERSES = "universes"
CONF_THRESHOLD = "threshold"
CONF_LANGUAGE = "language"

DEFAULT_THRESHOLD = 10
DEFAULT_LANGUAGE = "auto"

SACN_PORT = 5568
ARTNET_PORT = 6454
MA_NET3_PORT = 30020
OSC_PORT = 8000
CONF_OSC_INPUT_ENABLED = "osc_input_enabled"
CONF_OSC_INPUT_PORT = "osc_input_port"
CONF_OSC_INPUT_INTERFACE = "osc_input_interface"
CONF_MIDI_ENABLED = "midi_enabled"

EVENT_DMX_CHANGE = f"{DOMAIN}_dmx_change"
EVENT_PROTOCOL_SEEN = f"{DOMAIN}_protocol_seen"
EVENT_OSC_MESSAGE = f"{DOMAIN}_osc_message"

CONF_GIGACORE_HOSTS = "gigacore_hosts"
CONF_GIGACORE_COMMUNITY = "gigacore_community"
DEFAULT_GIGACORE_COMMUNITY = "public"
GIGACORE_SNMP_PORT = 161
GIGACORE_TEMP_OID = "1.3.6.1.4.1.4413.1.1.43.1.8.1.5.1.0"

CONF_ENTTEC_DEVICE = "enttec_device"
CONF_ENTTEC_MODEL = "enttec_model"

CONF_MIDI_DEVICE = "midi_device"
CONF_MIDI_MODEL = "midi_model"
CONF_PUNCHLIGHT_ENABLED = "punchlight_enabled"
CONF_PUNCHLIGHT_DEVICE = "punchlight_device"
CONF_PUNCHLIGHT_RECORD_SCENE = "punchlight_record_scene"
CONF_PUNCHLIGHT_STOP_SCENE = "punchlight_stop_scene"
CONF_PUNCHLIGHT_READY_SCENE = "punchlight_ready_scene"
CONF_PUNCHLIGHT_NOT_READY_SCENE = "punchlight_not_ready_scene"

CONF_WATCHDOG_ENABLED = "watchdog_enabled"
CONF_WATCHDOG_PROTOCOL = "watchdog_protocol"
CONF_WATCHDOG_UNIVERSE = "watchdog_universe"
CONF_WATCHDOG_SOURCE = "watchdog_source"
CONF_WATCHDOG_TIMEOUT = "watchdog_timeout"
CONF_WATCHDOG_RECOVERY_DELAY = "watchdog_recovery_delay"
CONF_WATCHDOG_LOSS_SCENE = "watchdog_loss_scene"
CONF_WATCHDOG_RECOVERY_SCENE = "watchdog_recovery_scene"

CONF_LIGHT_SYNC_ENABLED = "light_sync_enabled"

# Passive PunchLight network discovery cadence. Discovery never opens a
# control session and never sends MIDI/control data to discovered devices.
PUNCHLIGHT_DISCOVERY_INTERVAL_S = 60


CONF_ARCHIVE_DESTINATION = "archive_destination"
CONF_ARCHIVE_RETENTION_DAYS = "archive_retention_days"
CONF_ARCHIVE_MAX_BYTES = "archive_max_bytes"
CONF_CAPACITY_LINK_MBPS = "capacity_link_mbps"
CONF_CAPACITY_DANTE_MBPS = "capacity_dante_mbps"
CONF_CAPACITY_CAMERAS_MBPS = "capacity_cameras_mbps"
CONF_CAPACITY_ST2110_MBPS = "capacity_st2110_mbps"
CONF_CAPACITY_OTHER_MBPS = "capacity_other_mbps"
CONF_INTERFACE_DMX = "interface_dmx"
CONF_INTERFACE_DANTE = "interface_dante"
CONF_INTERFACE_PTP = "interface_ptp"
CONF_INTERFACE_MA = "interface_ma"
CONF_INTERFACE_AUDIO = "interface_audio"
CONF_DMX_ARTNET_ENABLED = "dmx_artnet_enabled"
CONF_DMX_SACN_ENABLED = "dmx_sacn_enabled"
CONF_DMX_SOURCE = "dmx_source"
CONF_MA_ENABLED = "ma_enabled"
CONF_AES70_HOSTS = "aes70_hosts"
CONF_AES70_PORT = "aes70_port"
CONF_CHAOS_ENABLED = "chaos_enabled"
CONF_PROJECTOR_MONITOR_ENABLED = "projector_monitor_enabled"

CONF_NOTIFICATION_ENABLED = "notification_enabled"
CONF_NOTIFICATION_TARGET = "notification_target"
CONF_HA_BUILDER_ENABLED = "ha_builder_enabled"

CONF_NOTIFICATION_MODE = "notification_mode"

CONF_PERFORMANCE_PROFILE = "performance_profile"
PERFORMANCE_PROFILES = ("auto", "minimal", "standard", "full")
