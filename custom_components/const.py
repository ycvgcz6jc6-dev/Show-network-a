DOMAIN = "dmx_monitor"
VERSION = "0.15.27"

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
CONF_GENERIC_SWITCH_HOSTS = "generic_switch_hosts"
CONF_UPS_HOSTS = "ups_hosts"
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

# Receive-only IP tally (TSL UMD over UDP).
CONF_TALLY_IP_ENABLED = "tally_ip_enabled"
CONF_TALLY_IP_INTERFACE = "tally_ip_interface"
CONF_TALLY_IP_PORT = "tally_ip_port"
CONF_TALLY_IP_SCREEN = "tally_ip_screen"
CONF_TALLY_IP_INDEX = "tally_ip_index"
CONF_TALLY_IP_STALE_TIMEOUT = "tally_ip_stale_timeout"
DEFAULT_TALLY_IP_PORT = 4003

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
CONF_DANTE_MANAGED_URL = "dante_managed_url"
CONF_DANTE_MANAGED_API_KEY = "dante_managed_api_key"
CONF_DANTE_MANAGED_DOMAIN_ID = "dante_managed_domain_id"
CONF_DMX_ARTNET_ENABLED = "dmx_artnet_enabled"
CONF_DMX_SACN_ENABLED = "dmx_sacn_enabled"
CONF_DMX_SOURCE = "dmx_source"
CONF_MA_ENABLED = "ma_enabled"
CONF_AES70_HOSTS = "aes70_hosts"
CONF_YAMAHA_OSC_HOSTS = "yamaha_osc_hosts"
CONF_QLAB_HOSTS = "qlab_hosts"
CONF_RESOLUME_HOSTS = "resolume_hosts"
CONF_NEXUS_AUDIO_HOSTS = "nexus_audio_hosts"
CONF_PDU_HOSTS = "pdu_hosts"
CONF_REOLINK_HA_ENABLED = "reolink_ha_enabled"
CONF_NEXUS_AUDIO_PLAYERS = "nexus_audio_players"
CONF_MILLUMIN_LISTEN_PORT = "millumin_listen_port"
CONF_MILLUMIN_PING_TARGET = "millumin_ping_target"
CONF_SENDSPIN_DANTE_PLAYERS = "sendspin_dante_players"
CONF_GREENGO_MULTICAST_GROUP = "greengo_multicast_group"
CONF_AES70_PORT = "aes70_port"
CONF_AVDECC_BRIDGE_URL = "avdecc_bridge_url"
CONF_AVDECC_BRIDGE_TOKEN = "avdecc_bridge_token"
CONF_CHAOS_ENABLED = "chaos_enabled"
CONF_PROJECTOR_MONITOR_ENABLED = "projector_monitor_enabled"

CONF_ETC_CEM3_ENABLED = "etc_cem3_enabled"
CONF_ONTIME_ENABLED = "ontime_enabled"
CONF_ONTIME_HOST = "ontime_host"
CONF_ONTIME_PORT = "ontime_port"
CONF_QLCPLUS_ENABLED = "qlcplus_enabled"
CONF_QLCPLUS_HOST = "qlcplus_host"
CONF_QLCPLUS_PORT = "qlcplus_port"
CONF_ETC_CEM3_HOSTS = "etc_cem3_hosts"
CONF_INTERFACE_ETC = "interface_etc"

CONF_VIDEO_IP_ENABLED = "video_ip_enabled"
CONF_VIDEO_IP_INTERFACE = "video_ip_interface"
CONF_VIDEO_IP_PREVIEW_ENABLED = "video_ip_preview_enabled"

CONF_RDM_BRIDGE_URL = "rdm_bridge_url"
CONF_RDM_BRIDGE_TOKEN = "rdm_bridge_token"
CONF_RDMNET_BRIDGE_URL = "rdmnet_bridge_url"
CONF_RDMNET_BRIDGE_TOKEN = "rdmnet_bridge_token"
CONF_RDM_ENABLED = "rdm_enabled"
CONF_RDMNET_ENABLED = "rdmnet_enabled"
CONF_RDM_ALLOW_WRITES = "rdm_allow_writes"

CONF_NOTIFICATION_ENABLED = "notification_enabled"
CONF_NOTIFICATION_TARGET = "notification_target"
CONF_HA_BUILDER_ENABLED = "ha_builder_enabled"

CONF_NOTIFICATION_MODE = "notification_mode"

CONF_PERFORMANCE_PROFILE = "performance_profile"
PERFORMANCE_PROFILES = ("auto", "minimal", "standard", "full")
CONF_ETC_CEM3_DISCOVERY = "etc_cem3_discovery"
CONF_ETC_CEM3_INTERFACES = "etc_cem3_interfaces"
