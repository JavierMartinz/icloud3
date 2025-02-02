"""
Platform that supports scanning iCloud.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.icloud/


Special Note: I want to thank Walt Howd, (iCloud2 fame) who inspired me to
    tackle this project. I also want to give a shout out to Kovács Bálint,
    Budapest, Hungary who wrote the Python WazeRouteCalculator and some
    awesome HA guys (Petro31, scop, tsvi, troykellt, balloob, Myrddyn1,
    mountainsandcode,  diraimondo, fabaff, squirtbrnr, and mhhbob) who
    gave me the idea of using Waze in iCloud3.
                ...Gary Cobb aka GeeksterGary, Vero Beach, Florida, USA

Thanks to all
"""

#pylint: disable=bad-whitespace, bad-indentation
#pylint: disable=bad-continuation, import-error, invalid-name, bare-except
#pylint: disable=too-many-arguments, too-many-statements, too-many-branches
#pylint: disable=too-many-locals, too-many-return-statements
#pylint: disable=unused-argument, unused-variable
#pylint: disable=too-many-instance-attributes, too-many-lines

VERSION = '1.1.0b5'      #Custom Component Updater

import logging
import os
import sys
import time
import voluptuous as vol

from   homeassistant.const                import CONF_USERNAME, CONF_PASSWORD
from   homeassistant.helpers.event        import track_utc_time_change
import homeassistant.helpers.config_validation as cv
from   homeassistant.util                 import slugify
import homeassistant.util.dt              as dt_util
from   homeassistant.util.location        import distance
#from   homeassistant.components.zone.zone import async_active_zone
#from   homeassistant.util.async_ import run_callback_threadsafe

from   homeassistant.components.device_tracker import (
          PLATFORM_SCHEMA, DOMAIN, ATTR_ATTRIBUTES)

#Changes in device_tracker entities are not supported in HA v0.94 and
#legacy code is being used for the DeviceScanner. Try to import from the
#.legacy directory and retry from the normal directory if the .legacy
#directory does not exist.
try:
    from homeassistant.components.device_tracker.legacy import DeviceScanner
    HA_DEVICE_TRACKER_LEGACY_MODE = True
except ImportError:
    from homeassistant.components.device_tracker import DeviceScanner
    HA_DEVICE_TRACKER_LEGACY_MODE = False

#Vailidate that Waze is available and can be used
try:
    import WazeRouteCalculator
    WAZE_IMPORT_SUCCESSFUL = 'YES'
except ImportError:
    WAZE_IMPORT_SUCCESSFUL = 'NO'
    pass

try:
    from .pyicloud_ic3 import PyiCloudService
    PYICLOUD_IC3_IMPORT_SUCCESSFUL = True
except ImportError:
    PYICLOUD_IC3_IMPORT_SUCCESSFUL = False
    pass

_LOGGER = logging.getLogger(__name__)
#REQUIREMENTS = ['pyicloud==0.9.1']

DEBUG_TRACE_CONTROL_FLAG    = False

CONF_ACCOUNTNAME            = 'account_name'
CONF_GROUP                  = 'group'
CONF_DEVICENAME             = 'device_name'
CONF_NAME                   = 'name'
CONF_TRACKING_METHOD        = 'tracking_method'
CONF_MAX_IOSAPP_LOCATE_CNT  = 'max_iosapp_locate_cnt'
CONF_INCLUDE_DEVICETYPES    = 'include_device_types'
CONF_INCLUDE_DEVICETYPE     = 'include_device_type'
CONF_INCLUDE_DEVICES        = 'include_devices'
CONF_INCLUDE_DEVICE         = 'include_device'
CONF_EXCLUDE_DEVICETYPES    = 'exclude_device_types'
CONF_EXCLUDE_DEVICETYPE     = 'exclude_device_type'
CONF_EXCLUDE_DEVICES        = 'exclude_devices'
CONF_EXCLUDE_DEVICE         = 'exclude_device'
CONF_IOSAPP_DEVICE_IDS      = 'iosapp_device_ids'
CONF_IOSAPP_DEVICE_ID       = 'iosapp_device_id'
CONF_TRACK_DEVICES          = 'track_devices'
CONF_TRACK_DEVICE           = 'track_device'
CONF_FILTER_DEVICES         = 'filter_devices'
CONF_UNIT_OF_MEASUREMENT    = 'unit_of_measurement'
CONF_INTERVAL               = 'interval'
CONF_BASE_ZONE              = 'base_zone'
CONF_INZONE_INTERVAL        = 'inzone_interval'
CONF_STATIONARY_STILL_TIME  = 'stationary_still_time'
CONF_STATIONARY_INZONE_INTERVAL = 'stationary_inzone_interval'
CONF_MAX_INTERVAL           = 'max_interval'
CONF_TRAVEL_TIME_FACTOR     = 'travel_time_factor'
CONF_GPS_ACCURACY_THRESHOLD = 'gps_accuracy_threshold'
CONF_IGNORE_GPS_ACC_INZONE  = 'ignore_gps_accuracy_inzone'
CONF_HIDE_GPS_COORDINATES   = 'hide_gps_coordinates'
CONF_WAZE_REGION            = 'waze_region'
CONF_WAZE_MAX_DISTANCE      = 'waze_max_distance'
CONF_WAZE_MIN_DISTANCE      = 'waze_min_distance'
CONF_WAZE_REALTIME          = 'waze_realtime'
CONF_DISTANCE_METHOD        = 'distance_method'
CONF_COMMAND                = 'command'
CONF_SENSOR_NAME_PREFIX     = 'sensor_name_prefix'
CONF_SENSOR_BADGE_PICTURE   = 'sensor_badge_picture'
CONF_SENSORS                = 'create_sensors'
CONF_EXCLUDE_SENSORS        = 'exclude_sensors'


# entity attributes
ATTR_ZONE               = 'zone'
ATTR_ZONE_TIMESTAMP     = 'zone_timestamp'
ATTR_LAST_ZONE          = 'last_zone'
ATTR_BASE_ZONE          = 'base_zone'
ATTR_LOC_TIMESTAMP      = 'timeStamp'
ATTR_TIMESTAMP          = 'timestamp'
ATTR_TRIGGER            = 'trigger'
ATTR_BATTERY            = 'battery'
ATTR_INTERVAL           = 'interval'
ATTR_ZONE_DISTANCE      = 'zone_distance'
ATTR_CALC_DISTANCE      = 'calc_distance'
ATTR_WAZE_DISTANCE      = 'waze_distance'
ATTR_WAZE_TIME          = 'travel_time'
ATTR_DIR_OF_TRAVEL      = 'dir_of_travel'
ATTR_TRAVEL_DISTANCE    = 'travel_distance'
ATTR_DEVICE_STATUS      = 'device_status'
ATTR_LOW_POWER_MODE     = 'low_power_mode'
ATTR_BATTERY_STATUS     = 'battery_status'
ATTR_TRACKING           = 'tracking'
ATTR_ALIAS              = 'alias'
ATTR_AUTHENTICATED      = 'authenticated'
ATTR_LAST_UPDATE_TIME   = 'last_update'
ATTR_NEXT_UPDATE_TIME   = 'next_update'
ATTR_LAST_LOCATED       = 'last_located'
ATTR_INFO               = 'info'
ATTR_GPS_ACCURACY       = 'gps_accuracy'
ATTR_GPS                = 'gps'
ATTR_LATITUDE           = 'latitude'
ATTR_LONGITUDE          = 'longitude'
ATTR_POLL_COUNT         = 'poll_count'
ATTR_ICLOUD3_VERSION    = 'icloud3_version'
ATTR_SPEED              = 'speed'
ATTR_VERTICAL_ACCURACY  = 'vertical_acuracy'
ATTR_ALTITUDE           = 'altitude'
ATTR_BADGE              = 'badge'
ATTR_EVENT_LOG          = 'event_log'
ATTR_SPEED              = 'speed'
ATTR_SPEED_HIGH         = 'speed_high'
ATTR_SPEED_AVERAGE      = 'speed_average'

#icloud and other attributes
ATTR_LOCATION           = 'location'
ATTR_ATTRIBUTES         = 'attributes'
ATTR_RADIUS             = 'radius'
ATTR_FRIENDLY_NAME      = 'friendly_name'
ATTR_ISOLD              = 'isOld'

ISO_TIMESTAMP           = '0000-00-00T00:00:00.000'
ZERO_HHMMSS             = '00:00:00'
SENSOR_EVENT_LOG_ENTITY = 'sensor.icloud3_event_log'

#Devicename config parameter file extraction
DI_DEVICENAME    = 0
DI_DEVICE_TYPE   = 1
DI_FRIENDLY_NAME = 2
DI_EMAIL         = 3
DI_PICTURE       = 4
DI_RESERVED      = 5
DI_SENSOR_PREFIX_NAME = 6

DEVICE_ATTRS_BASE       = {ATTR_LATITUDE: 0, ATTR_LONGITUDE: 0,
                           ATTR_BATTERY: 0, ATTR_GPS_ACCURACY: 0,
                           ATTR_TIMESTAMP: ISO_TIMESTAMP,
                           ATTR_LOC_TIMESTAMP: ZERO_HHMMSS,
                           ATTR_TRIGGER: '',
                           ATTR_BATTERY_STATUS: '', ATTR_DEVICE_STATUS: '',
                           ATTR_LOW_POWER_MODE: ''}
TRACE_ATTRS_BASE        = {ATTR_ZONE: '', ATTR_LAST_ZONE: '',
                           ATTR_ZONE_TIMESTAMP: '', ATTR_GPS: 0,
                           ATTR_LATITUDE: 0, ATTR_LONGITUDE: 0,
                           ATTR_TRIGGER: '',
                           ATTR_TIMESTAMP: ISO_TIMESTAMP,
                           ATTR_ZONE_DISTANCE: 0, ATTR_INTERVAL: 0,
                           ATTR_DIR_OF_TRAVEL: '', ATTR_TRAVEL_DISTANCE: 0,
                           ATTR_LAST_UPDATE_TIME: '',
                           ATTR_NEXT_UPDATE_TIME: '',
                           ATTR_SPEED: '', ATTR_SPEED_HIGH: '',
                           ATTR_SPEED_AVERAGE: '',
                           ATTR_POLL_COUNT: '', ATTR_INFO: ''}
TRACE_ICLOUD_ATTRS_BASE = {CONF_NAME: '', 'deviceStatus': '',
                           ATTR_ISOLD: False,
                           ATTR_LATITUDE: 0, ATTR_LONGITUDE: 0,
                           ATTR_LOC_TIMESTAMP: 0, 'horizontalAccuracy': 0,
                          'positionType': 'Wifi'}

SENSOR_DEVICE_ATTRS     = ['zone', 'zone_name1', 'zone_name2', 'zone_name3',
                           'last_zone', 'last_zone_name1', 'last_zone_name2',
                           'last_zone_name3', 'zone_timestamp', 'base_zone',
                           'zone_distance', 'calc_distance', 'waze_distance',
                           'travel_time', 'dir_of_travel', 'interval', 'info',
                           'last_located', 'last_update', 'next_update',
                           'poll_count', 'travel_distance', 'trigger',
                           'battery', 'battery_status', 'gps_accuracy',
                           'speed', 'speed_high', 'speed_average',
                           'speed_summary', 'altitude', 'badge', 'event_log']

SENSOR_ATTR_FORMAT      = {'zone_distance': 'dist',
                           'calc_distance': 'dist',
                           'waze_distance': 'diststr',
                           'travel_distance': 'dist',
                           'battery': '%',
                           'dir_of_travel': 'title',
                           'speed': 'kph-mph',
                           'speed_high': 'kph-mph',
                           'speed_average': 'kph-mph',
                           'altitude': 'm-ft',
                           'badge': 'badge'}

#---- iPhone Device Tracker Attribute Templates ----- Gary -----------
SENSOR_ATTR_ICON        = {'zone': 'mdi:cellphone-iphone',
                           'last_zone': 'mdi:cellphone-iphone',
                           'base_zone': 'mdi:cellphone-iphone',
                           'zone_timestamp': 'mdi:restore-clock',
                           'zone_distance': 'mdi:map-marker-distance',
                           'calc_distance': 'mdi:map-marker-distance',
                           'waze_distance': 'mdi:map-marker-distance',
                           'travel_time': 'mdi:clock-outline',
                           'dir_of_travel': 'mdi:compass-outline',
                           'interval': 'mdi:clock-start',
                           'info': 'mdi:information-outline',
                           'last_located': 'mdi:restore-clock',
                           'last_update': 'mdi:restore-clock',
                           'next_update': 'mdi:update',
                           'poll_count': 'mdi:counter',
                           'travel_distance': 'mdi:map-marker-distance',
                           'trigger': 'mdi:flash-outline',
                           'battery': 'mdi:battery',
                           'speed': 'mdi:speedometer',
                           'speed_high': 'mdi:speedometer',
                           'speed_average': 'mdi:speedometer',
                           'speed_summary': 'mdi:speedometer',
                           'altitude': 'mdi:image-filter-hdr',
                           'battery_status': 'mdi:battery',
                           'gps_accuracy': 'mdi:map-marker-radius',
                           'badge': 'mdi:shield-account',
                           'entity_log': 'mdi:format-list-checkbox'}
SENSOR_ID_NAME_LIST     = {'zon': 'zone', 'zon1': 'zone_name1',
                           'zon2': 'zone_name2','zon3': 'zone_name3',
                           'bzon': 'base_zone',
                           'lzon': 'last_zone', 'lzon1': 'last_zone_name1',
                           'lzon2': 'last_zone_name2', 'lzon3': 'last_zone_name3',
                           'zonts': 'zone_timestamp',
                           'zdis': 'zone_distance', 'cdis': 'calc_distance',
                           'wdis': 'waze_distance',
                           'tdis': 'travel_distance', 'ttim': 'travel_time',
                           'dir': 'dir_of_travel', 'intvl':  'interval',
                           'lloc': 'last_located', 'lupdt': 'last_update',
                           'nupdt': 'next_update',
                           'cnt': 'poll_count',  'info': 'info',
                           'trig': 'trigger', 'bat': 'battery',
                           'spd': 'speed', 'spdhi': 'speed_high',
                           'spdavg': 'speed_average', 'spdsum': 'speed_summary',
                           'alt': 'altitude', 'gpsacc': 'gps_accuracy',
                           }


ATTR_TIMESTAMP_FORMAT    = '%Y-%m-%dT%H:%M:%S.%f'
APPLE_DEVICE_TYPES = ['iphone', 'ipad', 'ipod', 'watch', 'iwatch']

#icloud_update commands
CMD_ERROR    = 1
CMD_INTERVAL = 2
CMD_PAUSE    = 3
CMD_RESUME   = 4
CMD_WAZE     = 5

#Other constants
IOSAPP_DT_ENTITY = True
ICLOUD_DT_ENTITY = False
ICLOUD_LOCATION_DATA_ERROR = [False, 0, 0, '', ZERO_HHMMSS,
                              0, 0, '', '', '', \
                              False, ZERO_HHMMSS, 0]

#Waze status codes
WAZE_REGIONS      = ['US', 'NA', 'EU', 'IL', 'AU']
WAZE_USED         = 0
WAZE_NOT_USED     = 1
WAZE_PAUSED       = 2
WAZE_OUT_OF_RANGE = 3
WAZE_ERROR        = 4

#Operating Mode - This is set by the 'mode:' config parameter.
MODE_FMF            = 'fmf'       #Find My Friends
MODE_ICLOUD         = 'icloud'    #iCloud Find-my-Phone
MODE_FMPHN          = 'fmphn'     #icloud Find-my-Phone
MODE_IOSAPP         = 'iosapp'    #HA IOS App v1.5x
MODE_IOSAPP1        = 'iosapp1'   #HA IOS App v1.5x
MODE_IOSAPP2        = 'iosapp2'   #HA IOS App v2.0+
MODE_FMF_FMPHN      = [MODE_FMF, MODE_FMPHN, MODE_ICLOUD]
MODE_IOSAPP_V1_V2   = [MODE_IOSAPP, MODE_IOSAPP1, MODE_IOSAPP2]
MODE_VALID          = [MODE_FMF, MODE_FMPHN, MODE_ICLOUD,
                        MODE_IOSAPP, MODE_IOSAPP1, MODE_IOSAPP2]

MODE_NAME = {
    'fmf': 'Find My Friends',
    'fmphn': 'Find My Phone',
    'icloud': 'Find My Phone',
    'iosapp': 'IOS App',
    'iosapp1': 'IOS App Version 1',
    'iosapp2': 'IOS App Version 2',
}
MODE_SHORT_NAME= {
    'fmf': 'FmF',
    'fmphn': 'FmPhn',
    'icloud': 'FmPhn',
    'iosapp': 'IOS App',
    'iosapp1': 'IOS App v1',
    'iosapp2': 'IOS App v2',
}

# If the location data is old during the _update_device_icloud routine,
# it will retry polling the device (or all devices) after 3 seconds,
# up to 4 times. If the data is still old, it will set the next normal
# interval to C_LOCATION_ISOLD_INTERVAL and keep track of the number of
# times it overrides the normal polling interval. If it is still old after
# C_MAX_LOCATION_ISOLD_CNT retries, the normal intervl will be used and
# the cycle starts over on the next poll. This will prevent a constant
# repolling if the location data is always old.
C_LOCATION_ISOLD_INTERVAL = 15
C_MAX_LOCATION_ISOLD_CNT = 4


ICLOUD_GROUPS    = {}
CONFIGURING_DEVICE = {}

DEVICE_STATUS_SET = ['deviceModel', 'rawDeviceModel', 'deviceStatus',
                    'deviceClass', 'batteryLevel', 'id', 'lowPowerMode',
                    'deviceDisplayName', 'name', 'batteryStatus', 'fmlyShare',
                    'location',
                    'locationCapable', 'locationEnabled', 'isLocating',
                    'remoteLock', 'activationLocked', 'lockedTimestamp',
                    'lostModeCapable', 'lostModeEnabled', 'locFoundEnabled',
                    'lostDevice', 'lostTimestamp',
                    'remoteWipe', 'wipeInProgress', 'wipedTimestamp',
                    'isMac']

DEVICE_STATUS_CODES = {
    '200': 'online',
    '201': 'offline',
    '203': 'pending',
    '204': 'unregistered',
}

SERVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_ACCOUNTNAME): vol.All(cv.ensure_list, [cv.slugify]),
    vol.Optional(CONF_DEVICENAME): cv.slugify,
    vol.Optional(CONF_INTERVAL): cv.slugify,
    vol.Optional(CONF_COMMAND): cv.string
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_ACCOUNTNAME): cv.slugify,
    vol.Optional(CONF_GROUP): cv.slugify,
    vol.Optional(CONF_TRACKING_METHOD, default='fmf'): cv.string,
    vol.Optional(CONF_MAX_IOSAPP_LOCATE_CNT, default=100): cv.string,
    vol.Optional(CONF_BASE_ZONE, default='home'): cv.string,

    #-----►►General Attributes ----------
    vol.Optional(CONF_UNIT_OF_MEASUREMENT, default='mi'): cv.slugify,
    vol.Optional(CONF_INZONE_INTERVAL, default='2 hrs'): cv.string,
    vol.Optional(CONF_MAX_INTERVAL, default=0): cv.string,
    vol.Optional(CONF_TRAVEL_TIME_FACTOR, default=.60): cv.string,
    vol.Optional(CONF_GPS_ACCURACY_THRESHOLD, default=100): cv.string,
    vol.Optional(CONF_IGNORE_GPS_ACC_INZONE, default=True): cv.boolean,
    vol.Optional(CONF_HIDE_GPS_COORDINATES, default=False): cv.boolean,

    #-----►►Filter, Include, Exclude Devices ----------
    vol.Optional(CONF_TRACK_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_TRACK_DEVICE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_IOSAPP_DEVICE_IDS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_IOSAPP_DEVICE_ID, default=[]): vol.All(cv.ensure_list, [cv.string]),

    #-----►►Waze Attributes ----------
    vol.Optional(CONF_DISTANCE_METHOD, default='waze'): cv.string,
    vol.Optional(CONF_WAZE_REGION, default='US'): cv.string,
    vol.Optional(CONF_WAZE_MAX_DISTANCE, default=1000): cv.string,
    vol.Optional(CONF_WAZE_MIN_DISTANCE, default=1): cv.string,
    vol.Optional(CONF_WAZE_REALTIME, default=False): cv.boolean,

    #-----►►Other Attributes ----------
    vol.Optional(CONF_STATIONARY_INZONE_INTERVAL, default='30 min'): cv.string,
    vol.Optional(CONF_STATIONARY_STILL_TIME, default='8 min'): cv.string,
    vol.Optional(CONF_SENSORS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_SENSORS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_COMMAND): cv.string,

    #-----►►Depreciated Parameters ----------vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_INCLUDE_DEVICETYPES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_INCLUDE_DEVICETYPE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SENSOR_NAME_PREFIX, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SENSOR_BADGE_PICTURE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_INCLUDE_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_INCLUDE_DEVICE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICETYPES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICETYPE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_DEVICE, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_FILTER_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string])
    })

#--------------------------------------------------------------------
def _combine_lists(parm_lists):
    '''
    Take a list of lists and return a single list of all of the items.
        [['a,b,c'],['d,e,f']] --> ['a','b','c','d','e','f']
    '''
    new_list = []
    for lists in parm_lists:
        lists_items = lists.split(',')
        for lists_item in lists_items:
            new_list.append(lists_item)

    return new_list

#--------------------------------------------------------------------
def setup_scanner(hass, config: dict, see, discovery_info=None):
    """Set up the iCloud Scanner."""
    username  = config.get(CONF_USERNAME)
    password  = config.get(CONF_PASSWORD)
    account   = config.get(CONF_ACCOUNTNAME)
    group     = config.get(CONF_GROUP)
    base_zone = config.get(CONF_BASE_ZONE)
    tracking_method  = config.get(CONF_TRACKING_METHOD).lower()
    max_iosapp_locate_cnt = int(config.get(CONF_MAX_IOSAPP_LOCATE_CNT))

    #set default group if none based on the username and base_zone
    #initially set group to account for backwards compatability
    if group is None:
        group = account
        if group is None:
            group = slugify(username.split('@')[0])
            if base_zone is not None:
                group = group + "::" + base_zone
            account = group

    log_msg =("Setting up iCloud3 v{} device tracker for {}:{}:{}").format(
            VERSION, username, group, base_zone)
    if HA_DEVICE_TRACKER_LEGACY_MODE:
        log_msg = ("{}, using device_tracker.legacy code").format(log_msg)
    _LOGGER.info(log_msg)

    iosapp_device_ids = config.get(CONF_IOSAPP_DEVICE_IDS)
    iosapp_device_ids.extend(config.get(CONF_IOSAPP_DEVICE_ID))

    track_devices = config.get(CONF_TRACK_DEVICES)
    track_devices.extend(config.get(CONF_TRACK_DEVICE))

    if config.get(CONF_MAX_INTERVAL) == '0':
        inzone_interval_str = config.get(CONF_INZONE_INTERVAL)
    else:
        inzone_interval_str = config.get(CONF_MAX_INTERVAL)

    max_interval           = config.get(CONF_MAX_INTERVAL)
    gps_accuracy_threshold = config.get(CONF_GPS_ACCURACY_THRESHOLD)
    ignore_gps_accuracy_inzone_flag = config.get(CONF_IGNORE_GPS_ACC_INZONE)
    hide_gps_coordinates   = config.get(CONF_HIDE_GPS_COORDINATES)
    unit_of_measurement    = config.get(CONF_UNIT_OF_MEASUREMENT)

    stationary_inzone_interval_str = config.get(CONF_STATIONARY_INZONE_INTERVAL)
    stationary_still_time_str = config.get(CONF_STATIONARY_STILL_TIME)

    sensor_ids             = _combine_lists(config.get(CONF_SENSORS))
    exclude_sensor_ids     = _combine_lists(config.get(CONF_EXCLUDE_SENSORS))

    travel_time_factor     = config.get(CONF_TRAVEL_TIME_FACTOR)
    waze_realtime          = config.get(CONF_WAZE_REALTIME)
    distance_method        = config.get(CONF_DISTANCE_METHOD)
    waze_region            = config.get(CONF_WAZE_REGION)
    waze_max_distance      = config.get(CONF_WAZE_MAX_DISTANCE)
    waze_min_distance      = config.get(CONF_WAZE_MIN_DISTANCE)
    if waze_region not in WAZE_REGIONS:
        log_msg = ("Invalid Waze Region ({}). Valid Values are: "\
                      "NA=US or North America, EU=Europe, IL=Isreal").\
                      format(waze_region)
        _LOGGER.error(log_msg)

        waze_region       = 'US'
        waze_max_distance = 0
        waze_min_distance = 0

    if tracking_method == MODE_IOSAPP:
        tracking_method == MODE_IOSAPP1
    if tracking_method not in MODE_VALID:
        tracking_method = MODE_FMF

#----------------------------------------------
#DEPRECIATED PARAMETERS
    include_device_types = config.get(CONF_INCLUDE_DEVICETYPES)
    include_device_type  = config.get(CONF_INCLUDE_DEVICETYPE)
    include_devices      = config.get(CONF_INCLUDE_DEVICES)
    include_device       = config.get(CONF_INCLUDE_DEVICE)
    exclude_device_types = config.get(CONF_EXCLUDE_DEVICETYPES)
    exclude_device_type  = config.get(CONF_EXCLUDE_DEVICETYPE)
    exclude_devices      = config.get(CONF_EXCLUDE_DEVICES)
    exclude_device       = config.get(CONF_EXCLUDE_DEVICE)
    filter_devices       = config.get(CONF_FILTER_DEVICES)
    sensor_name_prefix   = config.get(CONF_SENSOR_NAME_PREFIX)
    sensor_badge_picture = config.get(CONF_SENSOR_BADGE_PICTURE)

#----------------------------------------------

    icloud_group = Icloud(
        hass, see, username, password, account, group, base_zone,
        tracking_method, track_devices,
        iosapp_device_ids,  max_iosapp_locate_cnt,
        inzone_interval_str, gps_accuracy_threshold,
        stationary_inzone_interval_str, stationary_still_time_str,
        ignore_gps_accuracy_inzone_flag, hide_gps_coordinates,
        sensor_ids, exclude_sensor_ids,
        unit_of_measurement, travel_time_factor, distance_method,
        waze_region, waze_realtime, waze_max_distance, waze_min_distance,

        include_device_types, include_device_type,
        exclude_device_types, exclude_device_type,
        include_devices, include_device,
        exclude_device, exclude_device,
        filter_devices,
        sensor_badge_picture,  sensor_name_prefix
        )

    ICLOUD_GROUPS[group] = icloud_group

#--------------------------------------------------------------------
    def service_callback_lost_iphone(call):
        """Call the lost iPhone function if the device is found."""
        groups = call.data.get(CONF_GROUP, ICLOUD_GROUPS)
        devicename = call.data.get(CONF_DEVICENAME)
        for group in groups:
            if group in ICLOUD_GROUPS:
                ICLOUD_GROUPS[group].service_handler_lost_iphone(
                                    group, devicename)

    hass.services.register(DOMAIN, 'icloud_lost_iphone',
                service_callback_lost_iphone, schema=SERVICE_SCHEMA)

#--------------------------------------------------------------------

    def service_callback_update_icloud(call):
        """Call the update function of an iCloud group."""
        groups     = call.data.get(CONF_GROUP, ICLOUD_GROUPS)
        devicename = call.data.get(CONF_DEVICENAME)
        command    = call.data.get(CONF_COMMAND)
        _LOGGER.warning("accounts=%s",accounts)
        _LOGGER.warning("devicename=%s",devicename)
        _LOGGER.warning("=%s",)

        for group in groups:
            if group in ICLOUD_GROUPS:
                _LOGGER.warning("group=%s",group)
                ICLOUD_GROUPS[group].service_handler_icloud_update(
                                    group, devicename, command)

    hass.services.register(DOMAIN, 'icloud_update',
                service_callback_update_icloud, schema=SERVICE_SCHEMA)


#--------------------------------------------------------------------
    def service_callback_restart_icloud(call):
        """Reset an iCloud group."""
        groups = call.data.get(CONF_GROUP, ICLOUD_GROUPS)
        for group in groups:
            if group in ICLOUD_GROUPS:
                ICLOUD_GROUPS[group].restart_icloud()

    hass.services.register(DOMAIN, 'icloud_restart',
                service_callback_restart_icloud, schema=SERVICE_SCHEMA)

#--------------------------------------------------------------------
    def service_callback_setinterval(call):
        """Call the update function of an iCloud group."""
        '''
        groups = call.data.get(CONF_GROUP, ICLOUD_GROUPS)
        interval = call.data.get(CONF_INTERVAL)
        devicename = call.data.get(CONF_DEVICENAME)
        _LOGGER.warning("accounts=%s",accounts)
        _LOGGER.warning("devicename=%s",devicename)
        _LOGGER.warning("=%s",)

        for group in groups:
            if group in ICLOUD_GROUPS:
                _LOGGER.warning("account=%s",account)
                ICLOUD_GROUPS[group].service_handler_icloud_setinterval(
                                    account, interval, devicename)
        '''
        groups   = call.data.get(CONF_GROUP, ICLOUD_GROUPS)
        interval = call.data.get(CONF_INTERVAL)
        devicename = call.data.get(CONF_DEVICENAME)
        _LOGGER.warning("groups=%s",groups)
        _LOGGER.warning("devicename=%s",devicename)
        _LOGGER.warning("=%s",)

        for group in groups:
            if group in ICLOUD_GROUPS:
                _LOGGER.warning("group=%s",group)
                ICLOUD_GROUPS[group].service_handler_icloud_setinterval(
                                    group, interval, devicename)

    hass.services.register(DOMAIN, 'icloud_set_interval',
                service_callback_setinterval, schema=SERVICE_SCHEMA)


    # Tells the bootstrapper that the component was successfully initialized
    return True


#====================================================================
class Icloud(DeviceScanner):
    """Representation of an iCloud account."""

    def __init__(self,
        hass, see, username, password, account, group, base_zone,
        tracking_method, track_devices,
        iosapp_device_ids,  max_iosapp_locate_cnt,
        inzone_interval_str, gps_accuracy_threshold,
        stationary_inzone_interval_str, stationary_still_time_str,
        ignore_gps_accuracy_inzone_flag, hide_gps_coordinates,
        sensor_ids, exclude_sensor_ids,
        unit_of_measurement, travel_time_factor, distance_method,
        waze_region, waze_realtime, waze_max_distance, waze_min_distance,

        include_device_types, include_device_type,
        exclude_device_types, exclude_device_type,
        include_devices, include_device,
        exclude_devices, exclude_device,
        filter_devices,
        sensor_badge_picture, sensor_name_prefix
        ):

        """Initialize an iCloud account."""
        self.hass                = hass
        self.username            = username
        self.password            = password
        self.api                 = None
        self.group               = group
        self.accountname         = account
        self.base_zone_config    = base_zone     #use as 'home' base location
        self.see                 = see
        self.iosapp_device_ids   = iosapp_device_ids
        self.verification_code   = None
        self.trusted_device      = None
        self.trusted_device_id   = None
        self.valid_trusted_device_ids = None

        #Setup MODE type and verify pyicloud-ic3 import
        mode = tracking_method

        self._setup_tracking_method(tracking_method)

        self.max_iosapp_locate_cnt = max_iosapp_locate_cnt
        self.restart_icloud_group_request_flag   = False
        self.restart_icloud_group_inprocess_flag = False
        self.authenticated_time   = ''

        self._setup_debug_control()

        self.attributes_initialized_flag     = False
        self.track_devices              = track_devices
        self.distance_method_waze_flag = (distance_method.lower() == 'waze')
        self.inzone_interval = self._time_str_to_secs(inzone_interval_str)
        self.gps_accuracy_threshold      = int(gps_accuracy_threshold)
        self.ignore_gps_accuracy_inzone_flag = ignore_gps_accuracy_inzone_flag
        self.hide_gps_coordinates        = hide_gps_coordinates
        self.sensor_ids                  = sensor_ids
        self.exclude_sensor_ids          = exclude_sensor_ids
        self.unit_of_measurement         = unit_of_measurement
        self.travel_time_factor          = float(travel_time_factor)
        self.e_seconds_local_offset_secs = 0
        self.time_zone_offset_seconds    = self._calculate_time_zone_offset()

        self._setup_um_formats(unit_of_measurement)
        self._setup_general_variables()
        self._setup_zone_tables()
        self._setup_stationary_zone_variables(stationary_inzone_interval_str,
                    stationary_still_time_str)
        self._setup_polling_variables()
        self._verify_waze_installation()
        self._setup_waze_variables(waze_region, waze_min_distance,
                    waze_max_distance, waze_realtime)

        #----- DEPREIATED ITEMS ------------------------------------
        self.include_device_types = include_device_types
        self.include_device_type  = include_device_type
        self.include_devices      = include_devices
        self.include_device       = include_device
        self.exclude_device_types = exclude_device_types
        self.exclude_device_type  = exclude_device_type
        self.exclude_devices      = exclude_devices
        self.exclude_device       = exclude_device
        self.filter_devices       = filter_devices
        self.sensor_name_prefix   = sensor_name_prefix
        self.sensor_badge_picture = sensor_badge_picture
        #----- DEPREIATED ITEMS ------------------------------------

        #add HA event that will call the _polling_loop_15_sec_icloud function every 15 seconds
        #that will check a iphone's location if the time interval
        #has passed. If so, update all tracker attributes for all phones
        #being tracked with the new information.

        #Restart the icloud tracker which will finish initializing the fields
        #for all devices and setting everything up. Do not start the polling
        #times if there is an error.
        if self.restart_icloud():
            track_utc_time_change(self.hass, self._polling_loop_5_sec_device,
                    second=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])

#--------------------------------------------------------------------
    def restart_icloud(self):
        """Reset an iCloud account."""

        #check to see if restart is in process
        if self.restart_icloud_group_inprocess_flag:
            return

        self.restart_icloud_group_request_flag   = False
        self.restart_icloud_group_inprocess_flag = True

        event_msg = ("^^^^^ {} ^^^^^ HA Started ^^^^^").format(
            dt_util.now().strftime('%A, %B %d'))
        self._save_event("*", event_msg)
        event_msg = ("iCloud3 Initalization, Stage 1, Verify iCloud "
                    "Location Service")
        self._save_event("*", event_msg)
        self._LOGGER_info_msg(event_msg)

        log_msg = ("iCloud3 Tracking Method: {}").format(self.mode_name)
        self._LOGGER_info_msg(log_msg)
        self._save_event("*", log_msg)

        if (PYICLOUD_IC3_IMPORT_SUCCESSFUL == False and \
                self.CURRENT_MODE_FMF_FMPHN):
            self.mode = MODE_IOSAPP
            log_msg = ("Error: 'pyicloud_ic3.py' module not found")
            self._LOGGER_error_msg(log_msg)
            log_msg = ("Falling back to using IOSAPP instead of {}").\
                    format(self.mode_s)
            self._LOGGER_error_msg(log_msg)

        from .pyicloud_ic3 import (
                PyiCloudFailedLoginException, PyiCloudNoDevicesException)

        if self.CURRENT_MODE_IOSAPP:
            self.api = None

        elif self.CURRENT_MODE_FMF_FMPHN:
            log_msg = ("Requesting authorization for {}:{}").format(
                         self.username, self.group)
            self._LOGGER_info_msg(log_msg)

            icloud_dir = self.hass.config.path('icloud')
            if not os.path.exists(icloud_dir):
                os.makedirs(icloud_dir)

            try:
                self.api = PyiCloudService(self.username, self.password,
                           cookie_directory=icloud_dir, verify=True)

                log_msg = ("Authentication for {}:{} successful").format(
                                self.username, self.group)
                self._LOGGER_info_msg(log_msg)

            except PyiCloudFailedLoginException as error:
                self.api = None

                log_msg = ("Error authenticating iCloud FmF/FmPhn Service "
                           "for {}:{}").format(self.username, self.group)
                self._LOGGER_error_msg(log_msg)
                self._save_event("*", log_msg)
                log_msg = ("pyicloud_ic3 iCloud Service Handler Error: {}").\
                            format(error)
                self._LOGGER_error_msg(log_msg)
                log_msg = ("iCloud location service has been disabled")
                self._LOGGER_error_msg(log_msg)
                log_msg = ("Falling back to using IOSAPP instead of {}").\
                            format(self.mode_short_name)
                self._LOGGER_error_msg(log_msg)

                self.mode = MODE_IOSAPP

        self._setup_tracking_method(self.mode)  #setup again in case of errors
        self._setup_device_tracking_fields()
        self._setup_sensor_variables()

        event_msg = ("^^^^^ {} ^^^^^ HA Started ^^^^^").format(
                    dt_util.now().strftime('%A, %B %d'))
        self._save_event("*", event_msg)

        event_msg = ("iCloud3 Initalization, Stage 2, Set up tracked devices")
        self._save_event("*", event_msg)
        self._LOGGER_info_msg(event_msg)

        log_msg = ("Initializing Device Tracking for user {}").format(
                    self.username)
        self._LOGGER_info_msg(log_msg)

        try:
            self.tracked_devices = []
            self._check_depreciated_config_parms()
            self._setup_tracked_devices(self.track_devices)

            if self.CURRENT_MODE_FMF:
                self._setup_tracked_devices_fmf()

            elif self.CURRENT_MODE_FMPHN:
                self._setup_tracked_devices_icloud()

            elif self.CURRENT_MODE_IOSAPP:
                self._setup_tracked_devices_iosapp()

            self.track_devicename_list = ''
            for devicename in self.devicename_verified:
                if self.devicename_verified.get(devicename):
                    self.tracking_device_flag[devicename] = True

                    self.tracked_devices.append(devicename)

                    self.track_devicename_list = '{}, {}'.format(
                            self.track_devicename_list, devicename)

                    event_msg = ("Tracking ({}) {}:{}:{}").format(
                            self.mode_short_name,
                            self.group, devicename,
                            self.fmf_devicename_email.get(devicename))
                    self._save_event("*", event_msg)
                    self._LOGGER_info_msg(event_msg)
                else:
                    event_msg = ("Not Tracking ({}) {}:{}:{}").format(
                            self.mode_short_name,
                            self.group, devicename,
                            self.fmf_devicename_email.get(devicename))
                    self._save_event("*", event_msg)
                    self._LOGGER_info_msg(event_msg)

            #nothing to do if no devices to track
            if self.track_devicename_list == '':
                log_msg = ("iCloud3 Setup Aborted, no devices to track")
                self._LOGGER_error_msg(log_msg)
                if self.CURRENT_MODE_FMPHN:
                    log_msg = ("Devicenames or device_types must be "
                                "included in configuration parameters")
                else:
                    log_msg = ("Devicenames must be included in the"
                              "'tracked_devices' configuration parameter")
                self._LOGGER_error_msg(log_msg)
                return False

            #Now that the devices have been set up, finish setting up
            #the Event Log Sensor
            self._setup_event_log()

            self.track_devicename_list = '{}'.format(
                            self.track_devicename_list[1:])
            log_msg = ("Tracking Devices{}").format(
                            self.track_devicename_list)
            self._LOGGER_info_msg(log_msg)
            self._save_event("*", log_msg)

            #Now we know tracked devices, associate them with the iosapp
            #devices
            self._setup_sensor_base_attrs()
            self._setup_sensors_custom_list()

            for devicename in self.tracked_devices:
                event_msg = ("iCloud3 Initalization, Stage 3, "
                      "Setting up {}:{}").format(self.group, devicename)
                self._save_event("*", event_msg)
                self._LOGGER_info_msg(event_msg)

                self._initialize_device_fields(devicename)
                self._initialize_times_counts_flags(devicename)
                self._initialize_intervals_distances_times(devicename)
                self._initialize_location_speed_fields(devicename)
                self._update_stationary_zone(devicename,
                        self.stat_zone_base_latitude,
                        self.stat_zone_base_longitude, True)
                self.in_stationary_zone_flag[devicename] = False

                #Initialize the new attributes
                kwargs = self._setup_base_kwargs(devicename,
                        self.zone_home_lat, self.zone_home_long, 0, 0)
                attrs  = self._initialize_attrs(devicename)

                self._update_device_attributes(devicename, kwargs, attrs,
                            'restart_icloud')
                self._update_device_sensors(devicename, kwargs)
                self._update_device_sensors(devicename, attrs)

            #Everying reset. Now do an iCloud update to set up the device info.
            self.this_update_seconds = self._time_now_secs()
            event_msg = ("iCloud3 Initalization, Stage 4, Locating devices")
            self._save_event("*", event_msg)
            self._LOGGER_info_msg(event_msg)

            if self.CURRENT_MODE_FMF_FMPHN:
                self.restart_icloud_group_inprocess_flag = False
                self._update_device_icloud('Initializing location')
                self._update_event_log_sensor_data(devicename)

            if devicename == 'gary_iphone':
                self._notify_device('Test message Gary', devicename=devicename)
        except:
            pass
        #except PyiCloudNoDevicesException:
        #    log_msg = ('No iCloud Devices found!')
        #    self._LOGGER_error_msg(log_msg)

        self.restart_icloud_group_inprocess_flag = False

        return True
#--------------------------------------------------------------------
    def icloud_need_trusted_device(self):
        """We need a trusted device."""
        configurator = self.hass.components.configurator
        if self.group in CONFIGURING_DEVICE:
            return

        devicesstring = ''
        if self.valid_trusted_device_ids == 'Invalid Entry':
            devicesstring = '\n\n'\
                '----------------------------------------------\n'\
                '●●● Previous Trusted Device Id Entry is Invalid ●●●\n\n\n' \
                '----------------------------------------------\n\n\n'
            self.valid_trusted_device_ids = None

        devices = self.api.trusted_devices
        _LOGGER.info("Devices=%s",devices)
        device_list = "ID&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Phone Number\n" \
                      "––&nbsp;&nbsp;&nbsp;&nbsp;––––––––––––\n"
        for i, device in enumerate(devices):
            _LOGGER.info("Device=%s-%s",i,device)
            device_list += ("{}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                        "&nbsp;&nbsp;{}\n").format(
                        i, device.get('phoneNumber'))

            self.valid_trusted_device_ids = "{},{}".format(i,
                        self.valid_trusted_device_ids)

        description_msg = ("Enter the ID for the Trusted Device to receive "
                  "the verification code via a text message.\n\n\n{}").format(
                        device_list)

        CONFIGURING_DEVICE[self.group] = configurator.request_config(
            'iCloud Account Reauthorization required for {}'.format(self.group),
            self.icloud_trusted_device_callback,
            description    = (description_msg),
            entity_picture = "/static/images/config_icloud.png",
            submit_caption = 'Confirm',
            fields         = [{'id': 'trusted_device', \
                               CONF_NAME: 'Trusted Device ID'}]
        )

#--------------------------------------------------------------------
    def icloud_trusted_device_callback(self, callback_data):
        """
        Take the device number enterd above, get the api.device info and
        have pyiCloud validate the device.

        callbackData={'trusted_device': '1'}
        apiDevices=[{'deviceType': 'SMS', 'areaCode': '', 'phoneNumber':
                    '********65', 'deviceId': '1'},
                    {'deviceType': 'SMS', 'areaCode': '', 'phoneNumber':
                    '********66', 'deviceId': '2'}]
        """
        self.trusted_device_id = int(callback_data.get('trusted_device'))
        self.trusted_device    = \
                    self.api.trusted_devices[self.trusted_device_id]

        if self.group in CONFIGURING_DEVICE:
            request_id   = CONFIGURING_DEVICE.pop(self.group)
            configurator = self.hass.components.configurator
            configurator.request_done(request_id)

        if str(self.trusted_device_id) not in self.valid_trusted_device_ids:
            log_msg = ("Invalid Trusted Device ID. Entered={}, "
                          "Valid IDs={}").format(
                          self.trusted_device_id,
                          self.valid_trusted_device_ids)

            self._LOGGER_error_msg(log_msg)

            self.trusted_device = None
            self.valid_trusted_device_ids = 'Invalid Entry'
            self.icloud_need_trusted_device()

        elif not self.api.send_verification_code(self.trusted_device):
            log_msg = ("Failed to send verification code")
            self._LOGGER_error_msg(log_msg)

            self.trusted_device = None
            self.valid_trusted_device_ids = None

        else:
            # Get the verification code, Trigger the next step immediately

            self.icloud_need_verification_code()

#------------------------------------------------------
    def icloud_need_verification_code(self):
        """Return the verification code."""
        configurator = self.hass.components.configurator
        if self.group in CONFIGURING_DEVICE:
            return

        CONFIGURING_DEVICE[self.group] = configurator.request_config(
            'iCloud Account Verification Code for {}'.format(self.group),
            self.icloud_verification_callback,
            description    = ('Enter the Verification Code'),
            entity_picture = "/static/images/config_icloud.png",
            submit_caption = 'Confirm',
            fields         = [{'id': 'code', \
                               CONF_NAME: 'Verification Code'}]
        )

#--------------------------------------------------------------------
    def icloud_verification_callback(self, callback_data):
        """Handle the chosen trusted device."""
        from .pyicloud_ic3 import PyiCloudException
        self.verification_code = callback_data.get('code')

        try:
            if not self.api.validate_verification_code(
                    self.trusted_device, self.verification_code):
                raise PyiCloudException('Unknown failure')
        except PyiCloudException as error:
            # Reset to the initial 2FA state to allow the user to retry
            log_msg = ("Failed to verify verification code: {}").format(error)
            self._LOGGER_error_msg(log_msg)

            self.trusted_device = None
            self.verification_code = None

            # Trigger the next step immediately
            self.icloud_need_trusted_device()

        if self.group in CONFIGURING_DEVICE:
            request_id   = CONFIGURING_DEVICE.pop(self.group)
            configurator = self.hass.components.configurator
            configurator.request_done(request_id)
#--------------------------------------------------------------------
    def icloud_reauthorizing_account(self, restarting_flag = False):
        '''
        Make sure iCloud is still available and doesn't need to be reauthorized
        in 15-second polling loop

        Returns True  if Reauthorization is needed.
        Returns False if Authorization succeeded
        '''

        if self.CURRENT_MODE_IOSAPP:
            return False
        elif self.restart_icloud_group_inprocess_flag:
            return False

        fct_name = "icloud_reauthorizing_account"

        from .pyicloud_ic3 import PyiCloudService
        from .pyicloud_ic3 import (
            PyiCloudFailedLoginException, PyiCloudNoDevicesException)

        try:
            if restarting_flag == False:
                if self.api is None:
                    log_msg = ("iCloud/FmF API Error, No device API information "
                                    "for devices. Resetting iCloud")
                    self._LOGGER_error_msg(log_msg)

                    self.restart_icloud()

                elif self.restart_icloud_group_request_flag:    #via service call
                    log_msg = ("iCloud Restarting, via svc call")
                    self._LOGGER_error_msg(log_msg)
                    self.restart_icloud()

                if self.api is None:
                    log_msg = ("iCloud reset failed, no device API information "
                                    "after reset")
                    self._LOGGER_error_msg(log_msg)

                    return True

            if self.api.requires_2sa:
                from .pyicloud_ic3 import PyiCloudException
                try:
                    if self.trusted_device is None:
                        self.icloud_need_trusted_device()
                        return True  #Reauthorization needed

                    if self.verification_code is None:
                        self.icloud_need_verification_code()

                        attrs            = {}
                        attrs[ATTR_INFO] = ''
                        devicename = list(self.tracked_devices.keys())[0]
                        self._update_device_sensors(devicename, attrs)
                        return True  #Reauthorization needed

                    self.api.authenticate()
                    self.authenticated_time = \
                                dt_util.now().strftime(
                                        self.um_date_time_strfmt)

                    log_msg = ("iCloud/FmF Authentication, Devices={}").format(
                        self.api.devices)
                    self._LOGGER_info_msg(log_msg)

                    if self.api.requires_2sa:
                        raise Exception('Unknown failure')

                    self.trusted_device    = None
                    self.verification_code = None

                except PyiCloudException as error:
                    log_msg = ("►►Error setting up 2FA: {}").format(error)
                    self._LOGGER_error_msg(log_msg)

                    return True  #Reauthorization needed, Authorization Failed

            return False         #Reauthorization not needed, (Authorized OK)

        except Exception as err:
            _LOGGER.exception(err)
            x = self._internal_error_msg(fct_name, err, 'AuthiCloud')
            return True

#########################################################
#
#   This function is called every 5 seconds by HA. Cycle through all
#   of the iCloud devices to see if any of the ones being tracked need
#   to be updated. If so, we might as well update the information for
#   all of the devices being tracked since PyiCloud gets data for
#   every device in the account.
#
#########################################################

    def _polling_loop_5_sec_device(self, now):
        """Keep the API alive. Will be called by HA every 15 seconds"""
        try:
            fct_name = "_polling_loop_5_sec_device"

            if self.restart_icloud_group_request_flag:    #via service call
                self.restart_icloud()

            elif self.any_device_being_updated_flag:
                return

        except Exception as err:
            _LOGGER.exception(err)
            return

        self.this_update_seconds = self._time_now_secs()
        count_reset_timer     = dt_util.now().strftime('%H:%M:%S')
        this_minute           = int(dt_util.now().strftime('%M'))
        this_5sec_loop_second = int(dt_util.now().strftime('%S'))

        #Reset counts on new day, check for daylight saving time new offset
        if count_reset_timer == '00:00:05':
            for devicename in self.tracked_devices:
                event_msg = ("^^^^^ {} ^^^^^").format(
                        dt_util.now().strftime('%A, %B %d'))
                self._save_event(devicename, event_msg)

                self.event_cnt[devicename]         = 0
                self.poll_count_iosapp[devicename] = 0
                self.poll_count_icloud[devicename] = 0
                self.poll_count_ignore[devicename] = 0
                self.iosapp_location_update_cnt[devicename] = 0

                #Reset each night to get fresh data next time
                if devicename in self.waze_distance_history:
                    self.waze_distance_history[devicename] = ''

        elif count_reset_timer == '01:00:00':
            self._calculate_time_zone_offset()

        try:
            for devicename in self.tracked_devices:
                if (self.tracking_device_flag.get(devicename) is False or
                   self.next_update_time.get(devicename) == 'Paused'):
                    continue

                update_via_iosapp_flag = False
                update_via_icloud_flag = False
                self.state_change_flag[devicename] = False

                current_state = self._get_current_state(devicename, IOSAPP_DT_ENTITY)
                current_state = current_state.lower()
                dev_attrs = self._get_device_attributes(devicename, IOSAPP_DT_ENTITY)

                #Extract only attrs needed to update the device
                dev_attrs_avail = {k: v for k, v in dev_attrs.items() \
                                        if k in DEVICE_ATTRS_BASE}
                dev_data        = {**DEVICE_ATTRS_BASE, **dev_attrs_avail}
                dev_timestamp      = dev_data[ATTR_TIMESTAMP]
                dev_trigger        = dev_data[ATTR_TRIGGER]
                dev_latitude       = dev_data[ATTR_LATITUDE]
                dev_longitude      = dev_data[ATTR_LONGITUDE]
                dev_timestamp_time = self._timestamp_to_time_dev(dev_timestamp, True)
                dev_timestamp_secs = self._timestamp_to_secs_dev(dev_timestamp)


                #If there are multiple platforms with the same devicename,
                #the last_dev_timestamp(devicename) gets set in both places
                #and triggers a constant refresh. This loop checks to see if
                #all timestamps for all acct_devs are different.
                self.trigger[devicename] = dev_trigger
                update_via_trigger = False

                group_devicename = self.group + devicename
                last_dev_timestamp_secs  = self._timestamp_to_secs_dev(
                                    self.last_dev_timestamp.get(group_devicename))

                #_LOGGER.warning(">>> Account %s/%s,  trigger %s",\
                #                self.group, devicename, dev_trigger)

                        #_LOGGER.debug("-------------------")
                        #_LOGGER.info(dev_attrs)
                        #entity_id = self.device_tracker_entity.get(devicename)
                        #_LOGGER.info("..................")
                        #dev_data_all  = self.hass.states.get(entity_id)
                        #_LOGGER.info(dev_data_all)

                #_LOGGER.debug("-------------------")
                #entity_id = self.device_tracker_entity.get(devicename)
                #trace_dev_data  = self.hass.states.get(entity_id)
                #log_msg = "Dev-data for {}:{}={}".format(self.group,
                #            devicename, trace_dev_data)
                #self._LOGGER_debug_msg(log_msg)

                if (self.CURRENT_MODE_IOSAPP and
                        self.zone_current.get(devicename) == ''):
                    update_via_iosapp_flag = True
                    update_reason = ("Initialize Location with IOS App")

                #device_tracker.see svc all from automation wipes out
                #latitude and longitude. Reset via icloud update.
                elif dev_latitude == 0:
                    update_via_icloud_flag = True
                    self.next_update_seconds[devicename] = 0
                    update_reason = "GPS data = 0 {}:{}".format(
                         self.state_last_poll.get(devicename), current_state)

                #if lots of accuracy errors. wait and process on 15-second
                #icloud poll
                elif (self.location_isold_cnt.get(devicename) > 5 or
                        self.poor_gps_accuracy_cnt.get(devicename) > 5):
                    self._save_event(devicename,
                          'Retry in 15 sec, old data or poor GPS 5 times')
                    continue

                #iosapp has just entered or exited the north poll stationary
                #zone in error. Reset to the last zone location.
                elif (dev_latitude == 90 and dev_longitude == 180):
                    update_via_iosapp_flag   = True
                    log_msg = ("Resetting Enter/Exit Stationary Zone Location "
                                "Error, ({}:{}) to ({}:{})").format(
                                dev_latitude, dev_longitude,
                                self.last_lat.get(devicename),
                                self.last_long.get(devicename))
                    self._LOGGER_info_msg(log_msg)

                    self._save_event(devicename, 'Reset Stationary Zone')

                    dev_data[ATTR_LATITUDE]  = self.last_lat.get(devicename)
                    dev_latitude             = self.last_lat.get(devicename)
                    dev_data[ATTR_LONGITUDE] = self.last_long.get(devicename)
                    dev_longitude            = self.last_long.get(devicename)
                    update_reason = "ResetNorthPollStatZoneError"

                #Update the device if it wasn't completed last time.
                elif (self.state_last_poll.get(devicename) == 'not_set'):
                    update_via_icloud_flag = True
                    update_reason = ("iCloud3 Restart not completed, "
                            "will retry location update")
                    self._save_event(devicename, update_reason)

                #The state can be changed via device_tracker.see service call
                #with a different location_name in an automation or by an
                #ios app notification that a zone is entered or exited. If
                #by the ios app, the trigger is 'Geographic Region Exited' or
                #'Geographic Region Entered'. In iosapp 2.0, the state is
                #changed without a trigger being posted and will be picked
                #up here anyway.
                elif (current_state != self.state_last_poll.get(devicename)):
                    self.state_change_flag[devicename] = True
                    update_via_iosapp_flag             = True
                    update_reason = "State Change {} to {}".format(
                         self.state_last_poll.get(devicename), current_state)
                    self._save_event(devicename, update_reason)

                #In iosapp 2.0+, the trigger and timestamp might not exist.
                #In that case, don't do anything.
                #elif (dev_trigger == '' and dev_timestamp_time == ZERO_HHMMSS):
                #    continue

                #Skip if timestamp has not changed from previous iteration.
                #Also, there will be multiple 'Geographic Enter/Exit'
                #triggers if zones overlap (home & stationary)

                #Trigger is used to communicate the need that an update is not
                #needed for this device with another group (instance of iCloud)
                #This group is part of the trigger value and if this group is
                #in the trigger value, the devie does not need to be updated
                #again. If this group is not in the trigger, it was updated
                #somewhere else and the info should be updated again. The group
                #name is added when the attributes are updated. If there is
                #no communication between groups/instances, this update will
                #cause the other instance to do an update which will cause this
                #instance to do an update and so on.
                elif dev_trigger.find(self.group) == -1:
                    update_via_iosapp_flag = True
                    update_reason = "{} Trigger change, location time {}".format(
                        dev_trigger, dev_timestamp_time)
                    self._save_event(devicename, update_reason)

                    log_msg = ("Update triggered, Group {} not in trigger {}").\
                            format(self.group, dev_trigger)
                    self._LOGGER_debug_msg(log_msg)
                    log_msg = ("Timestamps, device={}, last={}").format(
                            dev_timestamp,
                            self.last_dev_timestamp.get(group_devicename))
                    self._LOGGER_debug_msg(log_msg)

                if update_via_iosapp_flag:
                    #self._trace_device_attributes(
                    #        devicename, '5sPoll', update_reason, dev_attrs)

                    self.last_dev_timestamp[group_devicename] = dev_timestamp

                    #Discard Background Fetch if over 2 min old or in a zone
                    #but updatetimestamp so we don't keep checking it
                    if (dev_trigger in
                            ('Background Fetch', 'Manual',
                                'Significant Location Update')):
                        update_via_ios_flag = self._check_use_iosapp_trigger(
                                devicename, dev_trigger,
                                dev_timestamp)

                        #If in a zone and got these triggers, reset gps to the
                        #center of the zone
                        if update_via_ios_flag:
                            dist = self._current_zone_distance(devicename,
                                    dev_latitude, dev_longitude)

                            #set to last gps if in a zone
                            if dist < .05:
                                event_msg = ("GPS distance from zone: {} km, "
                                "moving back into -{}- zone").format(dist,
                                      current_state)
                                self._save_event(devicename, event_msg)
                                self._LOGGER_debug_msg(event_msg)

                                dev_data[ATTR_LATITUDE]  = self.last_lat.get(devicename)
                                dev_latitude             = self.last_lat.get(devicename)
                                dev_data[ATTR_LONGITUDE] = self.last_long.get(devicename)
                                dev_longitude            = self.last_long.get(devicename)

                            #discard if between 0-1km away
                            elif dist <= 1:
                                self._save_event(devicename,
                                    "Discarding, distance < 1 km without Exit "
                                    "Zone trigger")
                                update_via_ios_flag = False

                            #update via icloud to verify location if between 1-2km away
                            elif dist <= 2:
                                update_via_ios_flag    = False
                                update_via_icloud_flag = True

                if update_via_iosapp_flag:
                    self.state_this_poll[devicename]    = current_state
                    self.iosapp_update_flag[devicename] = True
                    self._update_device_iosapp_trigger(
                            update_reason, devicename, dev_data)

                elif update_via_icloud_flag:
                    self._update_device_icloud(update_reason, devicename)

                if self.device_being_updated_flag.get(devicename):
                    self._save_event(devicename, "Retring last update")
                    self._retry_update(devicename)

                if update_via_iosapp_flag or update_via_icloud_flag:
                    self.device_being_updated_flag[devicename] = False
                    self.state_change_flag[devicename]         = False
                    self.log_debug_msgs_trace_flag             = False
                    self.update_in_process_flag                = False

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = ("Device Update Error, Error={}").format(ValueError)
            self._LOGGER_error_msg(log_msg)

        self.update_in_process_flag    = False
        self.log_debug_msgs_trace_flag = False

        #Cycle thru all devices and check to see if devices need to be
        #updated via every 15 seconds
        if (((this_5sec_loop_second) % 15) == 0):
            self._polling_loop_15_sec_icloud(now)

#--------------------------------------------------------------------
    def _retry_update(self, devicename):
        #This flag will be 'true' if the last update for this device
        #was not completed. Do another update now.
        self.device_being_updated_retry_cnt[devicename] = 0
        while (self.device_being_updated_flag.get(devicename) and
            self.device_being_updated_retry_cnt.get(devicename) < 4):
            self.device_being_updated_retry_cnt[devicename] += 1

            log_msg = ((
                "{}:{}({}) Retrying Update, Update was not "
                "completed in last cycle, Retry #{}").format(
                self.friendly_name.get(devicename), self.base_zone,
                self.device_type.get(devicename),
                self.device_being_updated_retry_cnt.get(devicename)))
            self._LOGGER_info_msg(log_msg)

            self.device_being_updated_flag[devicename] = True
            self.log_debug_msgs_trace_flag = True

            self._wait_if_update_in_process()
            update_reason = "Device-retry {}".format(
                self.device_being_updated_retry_cnt.get(devicename))

            self._update_device_icloud(update_reason, devicename)

#########################################################
#
#   Cycle through all iCloud devices and update the information for the devices
#   being tracked
#     ●►●◄►●▬▲▼◀►►●◀ oPhone=►▶
#########################################################
    def _update_device_iosapp_trigger(self, update_reason, devicename,
                dev_data):
        """

        """

        if self.restart_icloud_group_inprocess_flag:
            return

        fct_name = "_update_device_ios_trigger"

        self.any_device_being_updated_flag = True

        try:

            if self.next_update_time.get(devicename) == 'Paused':
                return

            self._save_event(devicename, "Update via IOS trigger")

            self.update_timer[devicename] = time.time()

            current_state = self._get_current_state(devicename, IOSAPP_DT_ENTITY)
            current_state = current_state.lower()

            log_msg = (
                    "▼▼▼(iosapp)▼▼▼ {}:{}:{} ▼▼▼▼▼▼ Old State={} ▼▼▼▼▼▼ {} "
                    "▼▼▼▼▼▼ <WARN>").format(
                    self.group, devicename, self.base_zone,
                    self.state_this_poll.get(devicename), update_reason)
            self._LOGGER_debug_msg(log_msg)

            self._trace_device_attributes(
                 devicename, 'dev_data', fct_name, dev_data)

            log_msg = ("= = = Prep Data From Device = = = (Now={})").format(
                     self.this_update_seconds)
            self._LOGGER_debug_msg(log_msg)

            self._save_event(devicename, 'Preparing Location Data')

            latitude            = round(dev_data.get(ATTR_LATITUDE), 6)
            longitude           = round(dev_data.get(ATTR_LONGITUDE), 6)
            timestamp           = self._timestamp_to_time_dev(
                                    dev_data.get(ATTR_TIMESTAMP))
            gps_accuracy        = dev_data.get(ATTR_GPS_ACCURACY)
            battery             = dev_data.get(ATTR_BATTERY)
            battery_status      = dev_data.get(ATTR_BATTERY_STATUS)
            device_status       = dev_data.get(ATTR_DEVICE_STATUS)
            low_power_mode      = dev_data.get(ATTR_LOW_POWER_MODE)
            altitude            = dev_data.get(ATTR_ALTITUDE)
            #speed               = dev_data.get(ATTR_SPEED)

            location_isold_attr = 'False'
            location_isold_flag = False
            self.location_isold_cnt[devicename]    = 0
            self.location_isold_msg[devicename]    = False
            self.poor_gps_accuracy_cnt[devicename] = 0

            #--------------------------------------------------------
            try:
                event_msg = "IOS App Data Prepared ({}, {})".format(
                        latitude, longitude)
                self._save_event(devicename, event_msg)

                if self.device_being_updated_flag.get(devicename):
                    update_msg = "Last update not completed, retrying"
                else:
                    update_msg = "Updating"
                update_msg = "● {} {} ●".format(update_msg,
                    self.friendly_name.get(devicename))

                attrs  = {}
                attrs[ATTR_INFO] = update_msg

                self._update_device_sensors(devicename, attrs)
                self.device_being_updated_flag[devicename] = True

            except Exception as err:
                _LOGGER.exception(err)
                attrs = self._internal_error_msg(
                        fct_name, err, 'UpdateAttrs1')

            try:
                #Calculate polling interval and setup location attributes
                attrs = self._determine_interval(devicename,
                              latitude, longitude, battery,
                              gps_accuracy, location_isold_flag,
                              timestamp)

                #Error in getting interval, no changed made
                if attrs == '':
                    return
            except Exception as err:
                attrs = self._internal_error_msg(
                        fct_name, err, 'DetInterval')
                self.any_device_being_updated_flag = False
                return

            try:
                #Note: Final prep and update device attributes via
                #device_tracker.see. The gps location, battery, and
                #gps accuracy are not part of the attrs variable and are
                #reformatted into device attributes by 'See'. The gps
                #location goes to 'See' as a "(latitude, longitude)" pair.
                #'See' converts them to ATTR_LATITUDE and ATTR_LONGITUDE
                #and discards the 'gps' item.

                log_msg = ("►►LOCATION ATTRIBUTES, State={}, Attrs={}").\
                            format(self.state_last_poll.get(devicename), attrs)
                self._LOGGER_debug_msg(log_msg)

                self.poll_count_iosapp[devicename] += 1
                self.last_lat[devicename]   = latitude
                self.last_long[devicename]  = longitude

                if altitude is None:
                    altitude = 0

                attrs[ATTR_LAST_LOCATED]   = timestamp
                attrs[ATTR_DEVICE_STATUS]  = device_status
                attrs[ATTR_LOW_POWER_MODE] = low_power_mode
                attrs[ATTR_BATTERY_STATUS] = battery_status
                attrs[ATTR_ALTITUDE]       = round(altitude, 2)
                attrs[ATTR_POLL_COUNT]     = self._format_poll_count(devicename)
                attrs[ATTR_BASE_ZONE]      = self.base_zone_name
                attrs[CONF_GROUP]          = self.mode_short_name+"::"+\
                                             self.group
                attrs[ATTR_TRACKING]       = ("{} ({}..{})").format(
                                              self.track_devicename_list,
                                              self.mode_short_name, self.group)
                attrs[ATTR_AUTHENTICATED]  = self.authenticated_time
                #attrs[ATTR_ALIAS]          = self.devicename_iosapp.get(devicename)

                #trigger, once device is processed, will be
                #original trigger value from dev_data when polled
                trigger = self.trigger.get(devicename)
                if self.state_change_flag.get(devicename):
                    attrs[ATTR_TRIGGER] = 'State Change'
                    ts = dt_util.now().strftime(ATTR_TIMESTAMP_FORMAT)
                    attrs[ATTR_TIMESTAMP]  = ts[0:23]

                #save group in trigger so an update will not be triggered
                #in the next cycle. It is used by another instane to prevent
                #a retrigger loop
                elif self.trigger.get(devicename).find(self.group) == -1:
                    #initialize trigger with 'mode:'
                    if trigger.find(':') == -1:
                        trigger = self.mode_short_name + ':'
                    trigger = ("{}:{}").format(trigger, self.group)

                attrs[ATTR_TRIGGER] = trigger

            except Exception as err:
                _LOGGER.exception(err)
                #attrs = self._internal_error_msg(
                #        fct_name, err, 'SetAttrsDev')

            try:
                kwargs = self._setup_base_kwargs(devicename,
                    latitude, longitude, battery, gps_accuracy)

                self._update_device_sensors(devicename, kwargs)
                self._update_device_sensors(devicename, attrs)
                self._update_device_attributes(devicename, kwargs,
                        attrs, 'Final Update')

                self.seen_this_device_flag[devicename]     = True
                self.device_being_updated_flag[devicename] = False

            except Exception as err:
                _LOGGER.exception(err)
                log_msg = ("Error Updating Device {}:{}({})").format(\
                            devicename,  self.base_zone, err)
                self._LOGGER_error_msg(log_msg)

            try:
                self._save_event(devicename, "Update via IOS trigger completed")

                log_msg=(
                    "{}:{}({}) Update completed using iosapp data, Zone={}, "
                    "Interval={}, Distance={}, TravelTime={}, "
                    "NextUpdate={}").format(
                    self.friendly_name.get(devicename),  self.base_zone,
                    self.device_type.get(devicename),
                    self.state_this_poll.get(devicename), attrs[ATTR_INTERVAL],
                    attrs[ATTR_ZONE_DISTANCE], attrs[ATTR_WAZE_TIME],
                    attrs[ATTR_NEXT_UPDATE_TIME])
                self._LOGGER_info_msg(log_msg)

                log_msg=(
                    "▲▲▲(iosapp)▲▲▲ {}:{}:{} ▲▲▲▲▲▲ New State={} ▲▲▲▲▲▲ {} "
                    "▲▲▲▲▲▲ <WARN>").format(
                    self.group, devicename,  self.base_zone,
                    self.state_this_poll.get(devicename), update_reason)
                self._LOGGER_debug_msg(log_msg)

                dev_attrs = self._get_device_attributes(devicename)
                #self._trace_device_attributes(
                #     devicename, 'after Final', fct_name, dev_attrs)

            except KeyError as err:
                self._internal_error_msg(fct_name, err, 'iosUpdateMsg')

        except Exception as err:
            _LOGGER.exception(err)
            self._internal_error_msg(fct_name, err, 'OverallUpdate')
            self.device_being_updated_flag[devicename] = False

        self.any_device_being_updated_flag = False
        self.iosapp_location_update_secs[devicename] = 0

#########################################################
#
#   This function is called every 15 seconds by HA. Cycle through all
#   of the iCloud devices to see if any of the ones being tracked need
#   to be updated. If so, we might as well update the information for
#   all of the devices being tracked since PyiCloud gets data for
#   every device in the account.
#
#########################################################
    def _polling_loop_15_sec_icloud(self, now):
        """Keep the API alive. Will be called by HA every 15 seconds"""

        if self.any_device_being_updated_flag:
            return

        fct_name = "_polling_loop_15_sec_icloud"

        self.this_update_seconds = self._time_now_secs()
        this_update_time = dt_util.now().strftime(self.um_time_strfmt)

        try:
            #Set update in process flag used in the 'icloud_update' external
            #command service call. Otherwise, the service call might be
            #overwritten if we are doing an update when it was started.
            for devicename in self.tracked_devices:
                if (self.tracking_device_flag.get(devicename) is False or
                   self.next_update_time.get(devicename) == 'Paused'):
                    continue

                self.iosapp_update_flag[devicename] = False
                update_device_flag = False

                # If the state changed since last poll, force an update
                # This can be done via device_tracker.see service call
                # with a different location_name in an automation or
                # from entering a zone via the IOS App.
                current_state = self._get_current_state(devicename).lower()

                if current_state != self.state_last_poll.get(devicename):
                    log_msg = ("{}:{}({}) Zone Change Detected, "
                        "From={}, To={}").format(
                        self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename),
                        self.state_last_poll.get(devicename), current_state)
                    self._LOGGER_info_msg(log_msg)

                    update_reason = "State Change {} to {}".format(
                           self.state_last_poll.get(devicename), current_state)
                    event_msg = ("Update via {}, {}").format(
                                self.mode_short_name, update_reason)
                    self._save_event(devicename, event_msg)

                    update_device_flag = True

                if update_device_flag:
                    if 'nearzone' in current_state:
                        current_state = 'near_zone'

                    self.state_this_poll[devicename]     = current_state
                    self.next_update_seconds[devicename] = 0

                    attrs  = {}
                    attrs[ATTR_INTERVAL]           = '0 sec'
                    attrs[ATTR_NEXT_UPDATE_TIME]   = ZERO_HHMMSS

                    self._update_device_sensors(devicename, attrs)

                #This flag will be 'true' if the last update for this device
                #was not completed. Do another update now.
                if (self.device_being_updated_flag.get(devicename) and
                    self.device_being_updated_retry_cnt.get(devicename) > 4):
                    self.device_being_updated_flag[devicename] = False
                    self.device_being_updated_retry_cnt[devicename] = 0
                    self.log_debug_msgs_trace_flag = False

                    log_msg = ("{}:{}({}) Canceling Update Retry").format(
                          self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename))
                    self._LOGGER_info_msg(log_msg)


                if self.device_being_updated_flag.get(devicename):
                    self.device_being_updated_retry_cnt[devicename] += 1

                    log_msg = ("{}:{}({}) Retrying Update, Update was not "
                            "completed in last cycle").format(
                            self.friendly_name.get(devicename), self.base_zone,
                            self.device_type.get(devicename))
                    self._LOGGER_info_msg(log_msg)

                    event_msg = ("Retrying {} Update").format(self.mode_short_name)
                    self._save_event(devicename, event_msg)

                    update_reason = "{} Update - Retrying, Cnt={}".format(
                        self.mode_short_name,
                        self.device_being_updated_retry_cnt.get(devicename))
                    update_device_flag = True
                    self.log_debug_msgs_trace_flag = True

                elif (self.this_update_seconds >=
                            self.next_update_seconds.get(devicename)):

                    update_reason = ("{} Update via NextUpdtTime").format(
                            self.mode_short_name)
                    update_device_flag = True
                    self.log_debug_msgs_trace_flag = False
                    event_msg = ("Update via {}, nextUpdateTime reached").\
                            format(self.mode_short_name)
                    self._save_event(devicename, event_msg)

                if update_device_flag:
                    if self.icloud_reauthorizing_account():
                        #_LOGGER.error("iCloud/FmF Acount Reauthorization "
                        #                "Needed")
                        attrs  = {}
                        attrs[ATTR_INFO] = '●●Authorize iCloud/FmF Acct●●'
                        devicename = list(self.tracked_devices.keys())[0]
                        self._update_device_sensors(devicename, attrs)

                        self._notify_device(
                                'Reauthorization needed for account {}'.\
                                    format(self.group))
                        return

                    self._wait_if_update_in_process()
                    self.update_in_process_flag = True
                    if self.CURRENT_MODE_IOSAPP:
                        self._request_iosapp_location_update(devicename)
                    else:
                        self._update_device_icloud(update_reason)

                self.update_in_process_flag = False

        except Exception as err:       #ValueError:
            _LOGGER.exception(err)
            log_msg = ("►►ICLOUD/FmF API ERROR, Error={}").format(ValueError)
            self._LOGGER_error_msg(log_msg)

            self.api.authenticate()           #Reset iCloud
            self.authenticated_time = \
                            dt_util.now().strftime(self.um_date_time_strfmt)
            self._update_device_icloud('iCloud/FmF Reauth')    #Retry update devices
            self.update_in_process_flag = False
            self.log_debug_msgs_trace_flag = False


#########################################################
#
#   Cycle through all iCloud devices and update the information for the devices
#   being tracked
#     ●►●◄►●▬▲▼◀►►●◀ oPhone=►▶
#########################################################
    def _update_device_icloud(self, update_reason = 'CheckiCloud',
            arg_devicename=None):
        """
        Request device information from iCloud (if needed) and update
        device_tracker information.
        """

        if self.CURRENT_MODE_IOSAPP:
            return
        elif self.restart_icloud_group_inprocess_flag:
            return
        elif self.any_device_being_updated_flag:
            return

        fct_name = "_update_device_icloud"


        self.any_device_being_updated_flag = True
        refresh_fmf_location_data     = True
        try:
            for devicename in self.tracked_devices:
                if arg_devicename and devicename != arg_devicename:
                    continue

                if self.next_update_time.get(devicename) == 'Paused':
                    continue

                if update_reason == 'Initializing Device Data':
                    event_msg = ("Update via {} - Initialization").\
                                format(self.mode_short_name)
                    self._save_event(devicename, event_msg)
                #If the device is in a zone, and was in the same zone on the
                #last poll of another device on the account and this device
                #update time has not been reached, do not update device
                #information. Do this in case this device currently has bad gps
                #and really doesn't need to be polled atthis time anyway.
                if (self._is_inzone(devicename) and
                        self._was_inzone(devicename) and
                        self.this_update_seconds <
                            self.next_update_seconds.get(devicename)):
                    do_not_update_flag = True

                    log_msg = (
                        "{}:{}({}) not updated, in zone {}. "
                        "Next update at {}").format(
                        self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename),
                        self.state_this_poll.get(devicename),
                        self.next_update_time.get(devicename))
                    self._LOGGER_info_msg(log_msg)
                    event_msg = "Update cancelled, already in Zone {}".format(
                        self.state_this_poll.get(devicename))
                    self._save_event(devicename, event_msg)

                    continue

                self.update_timer[devicename] = time.time()
                self.iosapp_location_update_secs[devicename] = 0

                log_msg = (
                        "▼▼▼({})▼▼▼ {}:{}:{} ▼▼▼▼▼▼ Old State={} ▼▼▼▼▼▼ {} "
                        "▼▼▼▼▼▼ <WARN>").format(self.mode_short_name,
                        self.group, devicename, self.base_zone,
                         self.state_this_poll.get(devicename), update_reason)
                self._LOGGER_debug_msg(log_msg)
                log_msg = ("{}:{}({}) Updating, {}").format(
                        self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename),
                        update_reason)
                self._LOGGER_info_msg(log_msg)

                do_not_update_flag = False
                loc_timestamp      = 0

                if self.CURRENT_MODE_FMF:
                    dev_data = self._setup_data_fmf(devicename,
                                            refresh_fmf_location_data)
                    refresh_fmf_location_data = False

                elif self.CURRENT_MODE_FMPHN:
                    dev_data = self._setup_data_icloud(devicename)

                #An error ocurred accessing the iCloud acount
                if dev_data[0] == False:
                    log_msg = ("Error, no location data for {}:{}").format(
                                self.group, devicename)
                    self._LOGGER_error_msg(log_msg)
                    self._save_event(devicename, log_msg)
                    break

                #icloud date overrules device data which may be stale
                latitude            = round(float(dev_data[1]), 6)
                longitude           = round(float(dev_data[2]), 6)
                location_isold_attr = dev_data[3]
                timestamp           = dev_data[4]
                gps_accuracy        = int(dev_data[5])
                battery             = dev_data[6]
                battery_status      = dev_data[7]
                device_status       = dev_data[8]
                low_power_mode      = dev_data[9]
                location_isold_flag = dev_data[10]
                loc_attr_timestamp  = dev_data[11]
                altitude            = dev_data[12]

                event_msg = "Location Data Prepared ({}, {})".format(
                    latitude, longitude)
                self._save_event(devicename, event_msg)

                #Discard if old location and less than 1km from home, except
                #for every 10th msg. Then set interval to 5 min.
                if (location_isold_flag and
                        self.location_isold_cnt.get(devicename) < 8):
                    age_str = self._secs_to_time_str(
                            self._secs_since(loc_attr_timestamp))
                    update_reason = "Old Location, #{}, Age {}".format(
                            self.location_isold_cnt.get(devicename), age_str)
                    if ((self.location_isold_cnt.get(devicename) % 10) == 0):
                        pass
                    else:
                        do_not_update_flag = True
                        log_msg = (
                            "{}:{}({}) not updated, old iCloud location data, "
                            "Age {}, Retry #{}").format(
                            self.friendly_name.get(devicename), self.base_zone,
                            self.device_type.get(devicename),
                            age_str, self.location_isold_cnt.get(devicename))
                        self._LOGGER_info_msg(log_msg)

                        event_msg = ("Update cancelled, Old location data, "
                            "Age {}, Retry #{}").format(age_str,
                            self.location_isold_cnt.get(devicename))
                        self._save_event(devicename, event_msg)

                #Discard if poor gps
                elif (self.poor_gps_accuracy_flag.get(devicename) and
                        self.poor_gps_accuracy_cnt.get(devicename) < 8):
                    do_not_update_flag = True
                    update_reason = "Poor GPS, #{}, ({})".format(
                        self.poor_gps_accuracy_cnt.get(devicename),
                        gps_accuracy)

                    log_msg = (
                        "{}({}:{}) not updated, Poor GPS accuracy "
                        "({}), Retry #{}.").format(
                        self.friendly_name.get(devicename),
                        self.device_type.get(devicename),  self.base_zone,
                        gps_accuracy,
                        self.poor_gps_accuracy_cnt.get(devicename))
                    self._LOGGER_info_msg(log_msg)

                    event_msg = ("Update cancelled, poor "
                                      "GPS accuracy ({})").format(gps_accuracy)
                    self._save_event(devicename, event_msg)

                if do_not_update_flag:
                    self._update_poll_count_ignore_attribute(devicename,
                            update_reason)

                    log_msg=(
                        "▲▲▲({})▲▲▲ {}:{}:{} ▲▲▲▲▲▲ New State={} ▲▲▲▲▲▲ {} "
                        "▲▲▲▲▲▲ <WARN>").format(self.mode_short_name,
                        self.group, devicename, self.base_zone,
                        self.state_this_poll.get(devicename), update_reason)
                    self._LOGGER_debug_msg(log_msg)
                    continue

                #--------------------------------------------------------
                try:
                    if self.device_being_updated_flag.get(devicename):
                        update_msg = "Last update not completed, retrying"
                    else:
                        update_msg = "Updating"
                    update_msg = "● {} {} ●".format(update_msg,
                                self.friendly_name.get(devicename))

                    attrs  = {}
                    attrs[ATTR_INFO] = update_msg

                    self._update_device_sensors(devicename, attrs)

                    #set device being updated flag. This is checked in the
                    #'_polling_loop_15_sec_icloud' loop to make sure the last update
                    #completed successfully (Waze has a compile error bug that will
                    #kill update and everything will sit there until the next poll.
                    #if this is still set in '_polling_loop_15_sec_icloud', repoll
                    #immediately!!!
                    self.device_being_updated_flag[devicename] = True

                except Exception as err:
                    attrs = self._internal_error_msg(
                                fct_name, err, 'UpdateAttrs1')

                try:
                    #Calculate polling interval and setup location attributes
                    attrs = self._determine_interval(devicename,
                                latitude, longitude, battery,
                                gps_accuracy, location_isold_flag,
                                timestamp)

                    #Error in getting interval, no changed made
                    if attrs == '':
                        continue
                except Exception as err:
                    attrs = self._internal_error_msg(
                                fct_name, err, 'DetInterval')
                    continue

                try:
                    #Note: Final prep and update device attributes via
                    #device_tracker.see. The gps location, battery, and
                    #gps accuracy are not part of the attrs variable and are
                    #reformatted into device attributes by 'See'. The gps
                    #location goes to 'See' as a "(latitude, longitude)" pair.
                    #'See' converts them to ATTR_LATITUDE and ATTR_LONGITUDE
                    #and discards the 'gps' item.

                    log_msg = ("►►LOCATION ATTRIBUTES, State={}, Attrs={}").\
                                format(self.state_last_poll.get(devicename), attrs)
                    self._LOGGER_debug_msg(log_msg)

                    self.poll_count_icloud[devicename] += 1

                    if not location_isold_flag:
                        self.last_lat[devicename]   = latitude
                        self.last_long[devicename]  = longitude

                    if altitude is None:
                        altitude = -2

                    attrs[ATTR_LAST_LOCATED]   = timestamp
                    attrs[ATTR_DEVICE_STATUS]  = device_status
                    attrs[ATTR_LOW_POWER_MODE] = low_power_mode
                    attrs[ATTR_BATTERY_STATUS] = battery_status
                    attrs[ATTR_ALTITUDE]       = round(altitude, 2)
                    attrs[ATTR_POLL_COUNT]     = self._format_poll_count(devicename)
                    attrs[ATTR_BASE_ZONE]      = self.base_zone_name
                    attrs[CONF_GROUP]          = self.mode_short_name+"::"+\
                                                 self.group
                    attrs[ATTR_TRACKING]       = ("{} ({}..{})").format(
                                                  self.track_devicename_list,
                                                  self.mode_short_name,
                                                  self.group)
                    attrs[ATTR_AUTHENTICATED]  = self.authenticated_time
                    #attrs[ATTR_ALIAS]      = self.devicename_iosapp.get(devicename)

                    #trigger, once device is processed, will be
                    #original trigger value from dev_data when polled
                    trigger = self.trigger.get(devicename)
                    if self.state_change_flag.get(devicename):
                        attrs[ATTR_TRIGGER] = 'State Change'
                        ts = dt_util.now().strftime(ATTR_TIMESTAMP_FORMAT)
                        attrs[ATTR_TIMESTAMP]  = ts[0:23]

                    #save group in trigger so an update will not be triggered
                    #in the next cycle. It is used by another instane to prevent
                    #a retrigger loop (initialize trigger with 'mode:')
                    elif self.trigger.get(devicename).find(self.group) == -1:
                        if trigger.find(':') == -1:
                            trigger = self.mode_short_name + ':'
                        trigger = ("{}:{}").format(trigger, self.group)

                    attrs[ATTR_TRIGGER] = trigger
                    attrs[ATTR_POLL_COUNT] = self._format_poll_count(devicename)

                except Exception as err:
                    attrs = self._internal_error_msg(fct_name, err, 'SetAttrs')

                try:
                    kwargs = self._setup_base_kwargs(devicename,
                        latitude, longitude, battery, gps_accuracy)

                    self._update_device_sensors(devicename, kwargs)
                    self._update_device_sensors(devicename, attrs)
                    self._update_device_attributes(devicename, kwargs,
                            attrs, 'Final Update')

                    self.seen_this_device_flag[devicename]     = True
                    self.device_being_updated_flag[devicename] = False

                except Exception as err:
                    log_msg = ("Error Updating Device {}:{}({})").format(\
                                devicename,  self.base_zone, err)
                    self._LOGGER_error_msg(log_msg)

                    _LOGGER.exception(err)

                try:
                    event_msg = ("Update via {} completed, next "
                            "update at {}").format(self.mode_short_name,
                            attrs[ATTR_NEXT_UPDATE_TIME])
                    self._save_event(devicename, event_msg)

                    log_msg=(
                        "{}:{}({}) Update completed using {} data, Zone={}, "
                        "Interval={}, Distance={}, TravelTime={}, "
                        "NextUpdate={}").format(
                        self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename),
                        self.mode_short_name,
                        self.state_this_poll.get(devicename),
                        attrs[ATTR_INTERVAL],
                        attrs[ATTR_ZONE_DISTANCE], attrs[ATTR_WAZE_TIME],
                        attrs[ATTR_NEXT_UPDATE_TIME])
                    self._LOGGER_info_msg(log_msg)
                    log_msg=(
                        "▲▲▲({})▲▲▲ {}:{}:{} ▲▲▲▲▲▲ New State={} ▲▲▲▲▲▲ {} "
                        "▲▲▲▲▲▲ <WARN>").format(self.mode_short_name,
                        self.group, devicename, self.base_zone,
                        self.state_this_poll.get(devicename), update_reason)
                    self._LOGGER_debug_msg(log_msg)

                except KeyError as err:
                    self._internal_error_msg(fct_name, err, 'icloudUpdateMsg')

        except Exception as err:
            self._internal_error_msg(fct_name, err, 'OverallUpdate')
            _LOGGER.exception(err)
            self.device_being_updated_flag[devicename] = False

        self.any_device_being_updated_flag = False

#########################################################
#
#   Get attribute information from the device
#
#########################################################
    def _setup_data_fmf(self, devicename, refresh_fmf_location_data):
        '''
        Get the location data from Find My Friends.

        location_data={
            'locationStatus': None,
            'location': {
                'isInaccurate': False,
                'altitude': 0.0,
                'address': {'formattedAddressLines': ['123 Main St',
                    'Your City, NY', 'United States'],
                    'country': 'United States',
                    'streetName': 'Main St,
                    'streetAddress': '123 Main St',
                    'countryCode': 'US',
                    'locality': 'Your City',
                    'stateCode': 'NY',
                    'administrativeArea': 'New York'},
                'locSource': None,
                'latitude': 12.34567890,
                'floorLevel': 0,
                'horizontalAccuracy': 65.0,
                'labels': [{'id': '79f8e34c-d577-46b4-a6d43a7b891eca843',
                    'latitude': 12.34567890,
                    'longitude': -45.67890123,
                    'info': None,
                    'label': '_$!<home>!$_',
                    'type': 'friend'}],
                'tempLangForAddrAndPremises': None,
                'verticalAccuracy': 0.0,
                'batteryStatus': None,
                'locationId': 'a6b0ee1d-be34-578a-0d45-5432c5753d3f',
                'locationTimestamp': 0,
                'longitude': -45.67890123,
                'timestamp': 1562512615222},
            'id': 'NDM0NTU2NzE3',
            'status': None}
        '''

        fct_name = "_setup_data_fmf"
        from .pyicloud_ic3 import PyiCloudNoDevicesException

        try:
            log_msg = ("= = = Prep Data From Find My Friends = = = (Now={})").\
                    format(     self.this_update_seconds)
            self._LOGGER_debug_msg(log_msg)
            self._save_event(devicename, 'Preparing FmF Location Data')

            if self._refresh_fmf_location_data() == False:
                #No icloud data, reauthenticate (status=None)
                try:
                    log_msg = ("FmF Reauthentication for {}:{}:{}").\
                                format(self.group, devicename,
                                self.fmf_devicename_email.get(devicename))
                    self._LOGGER_info_msg(log_msg)
                    self.api.authenticate()

                    self.authenticated_time = \
                            dt_util.now().strftime(self.um_date_time_strfmt)
                    self._trace_device_attributes(
                        devicename, 'FmF Status Reauth', fct_name, status)

                except:
                    log_msg = ("FmF Reauthentication unsuccessful for "
                            "{}:{}:{}").format(self.group, devicename,
                            self.fmf_devicename_email.get(devicename))
                    self._LOGGER_info_msg(log_msg)
                    log_msg = ("Verify the the account/password using the "
                           "Find-My-Friends app for {}").format(self.acountname)
                    self._LOGGER_error_msg(log_msg)

                    return ICLOUD_LOCATION_DATA_ERROR

            #Successful authentication, get locateion data again
            if self._refresh_fmf_location_data() == False:
                log_msg = ("FmF Reauthentication Error, no location data available")
                self._LOGGER_error_msg(log_msg)
                log_msg = ("Verify the ability to locate friends using the "
                           "Find-My-Friends app for {}").format(self.acountname)
                self._LOGGER_error_msg(log_msg)

                self.authenticated_time = ''
                return ICLOUD_LOCATION_DATA_ERROR

        except PyiCloudNoDevicesException:
            self._LOGGER_error_msg("No FmF Devices found")
            return ICLOUD_LOCATION_DATA_ERROR

        except Exception as err:
            self._LOGGER_error_msg("FmF Location Data Error")
            _LOGGER.exception(err)
            return ICLOUD_LOCATION_DATA_ERROR

        try:
            if devicename not in self.fmf_location_data:
                log_msg = ("FmF Reauthentication Error, no location data available")
                self._LOGGER_error_msg(log_msg)
                log_msg = ("Verify the ability to locate friends using the "
                           "Find-My-Friends app for {}").format(self.acountname)
                self._LOGGER_error_msg(log_msg)

                self.authenticated_time = ''
                return ICLOUD_LOCATION_DATA_ERROR


            location_data = self.fmf_location_data.get(devicename)
            if location_data == None:
                log_msg = ("No location data available for {}:{}").format(
                           self.acountname, devicename)
                self._LOGGER_error_msg(log_msg)
                return ICLOUD_LOCATION_DATA_ERROR

            location       = location_data.get('location')
            battery        = 0
            battery_status = location.get('batteryStatus')
            device_status  = 0
            low_power_mode = None
            loc_attr_timestamp = int(location.get('timestamp')) / 1000
            loc_timestamp = self._secs_to_time(loc_attr_timestamp)

            latitude      = round(location.get(ATTR_LATITUDE), 6)
            longitude     = round(location.get(ATTR_LONGITUDE), 6)
            gps_accuracy  = int(location.get('horizontalAccuracy'))
            altitude      = int(location.get(ATTR_ALTITUDE))
            location_isold_attr = False

            try:
                location_isold_flag = self._check_isold_status(
                    devicename, location_isold_attr, loc_timestamp,
                    loc_attr_timestamp)

                log_msg = ("►►LOCATION DATA ~~{}:{}~~, TimeStamp={}, "
                          "GPS=({}, {}), isOldFlag={}, GPSAccuracy={}").\
                    format(devicename, self.base_zone, loc_timestamp,
                    longitude, latitude, location_isold_flag, gps_accuracy)
                self._LOGGER_debug_msg(log_msg)

                self._check_poor_gps(devicename, gps_accuracy)

            except Exception as err:
                _LOGGER.exception(err)
                location_isold_flag = False
                self.poor_gps_accuracy_cnt[devicename]  = 0
                self.poor_gps_accuracy_flag[devicename] = False
                x = self._internal_error_msg(fct_name, err, 'OldLocGPS')

            return (True, latitude, longitude, location_isold_attr,
                    loc_timestamp, gps_accuracy, battery, battery_status,
                    device_status, low_power_mode,
                    location_isold_flag, loc_attr_timestamp, altitude)


        except Exception as err:
            _LOGGER.exception(err)
            self._LOGGER_error_msg("iCloud Location Data Error")
            return ICLOUD_LOCATION_DATA_ERROR


#----------------------------------------------------------------------------
    def _refresh_fmf_location_data(self):
        '''
        Refresh the FmF friends data after an authentication.
        If no location data was returned from pyicloid_ic3,
        return with False
        '''

        self._LOGGER_debug_msg("►►Refresh FmF Location Data")

        refresh_successful = False
        try:
            fmf = self.api.friends
            self.fmf_location_data = {}

            for location_data in fmf.locations:
                id_location = location_data.get('id')
                if self.fmf_id.get(id_location):
                    devicename = self.fmf_id[id_location]
                    self.fmf_location_data[devicename] = location_data
                    refresh_successful = True

                    log_msg = ("Loading Data, id={}, devicename={}").\
                            format(id_location, devicename)
                    self._LOGGER_debug_msg(log_msg)
        except:
            pass

        return refresh_successful

#----------------------------------------------------------------------------
    def _setup_data_icloud(self, devicename):
        '''
        Extract the data needed to determine location, direction, interval,
        etc. from the iCloud data set.

        Sample data set is:
       'batteryLevel': 0.6100000143051147, 'deviceDisplayName': 'iPhone XS',
       'deviceStatus': '200', CONF_NAME: 'Lillian-iPhone',
       'deviceModel': 'iphoneXS-1-4-0', 'rawDeviceModel': 'iPhone11,2',
       'deviceClass': 'iPhone', 'id': 't0v3GV....FFZav2IsE'
       'lowPowerMode': False, 'batteryStatus': 'Charging', 'fmlyShare': True,
       'location': {ATTR_ISOLD: False, 'isInaccurate': False, 'altitude': 0.0,
       'positionType': 'Wifi', 'latitude': 12.345678, 'floorLevel': 0,
       'horizontalAccuracy': 65.0, 'locationType': '',
       'timeStamp': 1550850915898, 'locationFinished': False,
       'verticalAccuracy': 0.0, 'longitude': -23.456789},
       'locationCapable': True, 'locationEnabled': True, 'isLocating': False,
       'remoteLock': None, 'activationLocked': True, 'lockedTimestamp': None,
       'lostModeCapable': True, 'lostModeEnabled': False,
       'locFoundEnabled': False, 'lostDevice': None, 'lostTimestamp': '',
       'remoteWipe': None, 'wipeInProgress': False, 'wipedTimestamp': None,
       'isMac': False
        '''

        fct_name = "_setup_data_icloud"
        from .pyicloud_ic3 import PyiCloudNoDevicesException

        try:
            log_msg = ("= = = Prep Data From iCloud = = = (Now={})").format(
                     self.this_update_seconds)
            self._LOGGER_debug_msg(log_msg)

            self._save_event(devicename, 'Preparing iCloud Location Data')

            #Get device attributes from iCloud
            device   = self.icloud_api_devices.get(devicename)
            status   = device.status(DEVICE_STATUS_SET)

            self._trace_device_attributes(
                devicename, 'iCloud Status', fct_name, status)

        except Exception as err:
#                   No icloud data, reauthenticate (status=None)
            self.api.authenticate()
            self.authenticated_time = \
                    dt_util.now().strftime(self.um_date_time_strfmt)
            device   = self.icloud_api_devices.get(devicename)
            status = device.status(DEVICE_STATUS_SET)

            log_msg = ("Reauthenticated iCloud account for {}:{}:{}").\
                        format(self.group, devicename, self.base_zone)
            self._LOGGER_info_msg(log_msg)
            self._trace_device_attributes(
                devicename, 'iCloud Status Reauth', fct_name, status)

            if status is None:
                log_msg = ("iCloud Reauthentication Error, "
                    "no data available for {}, Aborting").\
                    format(devicename)
                self._LOGGER_error_msg(log_msg)

                self.authenticated_time = ''
                return ICLOUD_LOCATION_DATA_ERROR
                #return (False, 0, 0, '', ZERO_HHMMSS, 0, 0, '', '', '', \
                #        False, ZERO_HHMMSS, 0)
        try:
            location       = status['location']
            battery        = int(status.get('batteryLevel', 0) * 100)
            battery_status = status['batteryStatus']
            device_status  = DEVICE_STATUS_CODES.get(
                                status['deviceStatus'], 'error')
            low_power_mode = status['lowPowerMode']

            self._trace_device_attributes(
                devicename, 'iCloud Loc', fct_name, location)

            if location:
                loc_attr_timestamp = location[ATTR_LOC_TIMESTAMP] / 1000
                loc_timestamp = self._secs_to_time(loc_attr_timestamp)

                latitude      = round(location[ATTR_LATITUDE], 6)
                longitude     = round(location[ATTR_LONGITUDE], 6)
                gps_accuracy  = int(location['horizontalAccuracy'])
                altitude      = int(location[ATTR_ALTITUDE])
                location_isold_attr = location[ATTR_ISOLD]

                try:
                    location_isold_flag = self._check_isold_status(
                        devicename, location_isold_attr, loc_timestamp,
                        loc_attr_timestamp)

                    log_msg = ("►►LOCATION DATA ~~{}~~, TimeStamp={}, "
                              "GPS=({}, {}), isOldFlag={}, GPSAccuracy={}").\
                        format(devicename, loc_timestamp,
                        longitude, latitude, location_isold_flag, gps_accuracy)
                    self._LOGGER_debug_msg(log_msg)

                    self._check_poor_gps(devicename, gps_accuracy)

                except Exception as err:
                    _LOGGER.exception(err)
                    location_isold_flag = False
                    self.poor_gps_accuracy_cnt[devicename]  = 0
                    self.poor_gps_accuracy_flag[devicename] = False
                    x = self._internal_error_msg(fct_name, err, 'OldLocGPS')

            else:
                loc_timestamp       = 'No Location Data'
                latitude            = 0
                longitude           = 0
                location_isold_attr = False
                gps_accuracy        = 0
                location_isold_flag = False
                self.state_last_poll[devicename] = 'not_set'

            return (True, latitude, longitude, location_isold_attr,
                    loc_timestamp, gps_accuracy, battery, battery_status,
                    device_status, low_power_mode,
                    location_isold_flag, loc_attr_timestamp, altitude)

        except PyiCloudNoDevicesException:
            self._LOGGER_error_msg("No iCloud Devices found")

        except Exception as err:
            _LOGGER.exception(err)
            self._LOGGER_error_msg("iCloud Location Data Error")
            return ICLOUD_LOCATION_DATA_ERROR
            #return (False, 0, 0, '', ZERO_HHMMSS, 0, 0, '', '', '', \
            #            False, ZERO_HHMMSS, 0)

#########################################################
#
#   iCloud is disable so trigger the iosapp to send a
#   Background Fetch location transaction
#
#########################################################
    def _request_iosapp_location_update(self, devicename):
        #service: notify.ios_<your_device_id_here>
        #  data:
        #    message: "request_location_update"


        if (self.iosapp_location_update_cnt.get(devicename) > \
                self.max_iosapp_locate_cnt):
            return

        request_msg_suffix = ''

        #if time > 0, then waiting for requested update to occur, update age
        if self.iosapp_location_update_secs.get(devicename) > 0:
            age = self._secs_since(
                self.iosapp_location_update_secs.get(devicename))
            request_msg_suffix = ' {} ago'.format(self._secs_to_time_str(age))
        else:

            self.iosapp_location_update_secs[devicename] = \
                    self.this_update_seconds
            self.iosapp_location_update_cnt[devicename] += 1
            self.poll_count_icloud[devicename] += 1

            entity_id    = "ios_{}".format(devicename)
            service_data = {"message": "request_location_update"}
            self.hass.services.call("notify", entity_id, service_data)

            event_msg = 'Request IOS App Location Update (#{})'.format(
                    self.iosapp_location_update_cnt.get(devicename))
            self._save_event(devicename, event_msg)

            log_msg = "{}:{}({}) {}".format(
                        self.friendly_name.get(devicename), self.base_zone,
                        self.device_type.get(devicename), event_msg)
            self._LOGGER_debug_msg(log_msg)

        attrs = {}
        attrs[ATTR_POLL_COUNT] = self._format_poll_count(devicename)
        attrs[ATTR_INFO]       = '● Location update requested (#{}){} ●'.\
                format(self.iosapp_location_update_cnt.get(devicename),
                    request_msg_suffix)
        self._update_device_sensors(devicename, attrs)


#########################################################
#
#   Calculate polling interval based on zone, distance from home and
#   battery level. Setup triggers for next poll
#
#########################################################
    def _determine_interval(self, devicename, latitude, longitude,
                                battery, gps_accuracy,
                                location_isold_flag, loc_timestamp):
        """Calculate new interval. Return location based attributes"""

        fct_name = "_determine_interval"

        try:
            location_data = self._get_device_distance_data(devicename,
                                        latitude, longitude, gps_accuracy,
                                        location_isold_flag)

            log_msg = ("Location_data={}").format(
                        location_data)
            self._LOGGER_debug_msg(log_msg)

            #Abort and Retry if Internal Error
            if (location_data[0] == 'ERROR'):
                return location_data[1]     #(attrs)

            current_zone              = location_data[0]
            dir_of_travel             = location_data[1]
            dist_from_home            = location_data[2]
            dist_from_home_moved      = location_data[3]
            dist_last_poll_moved      = location_data[4]
            waze_dist_from_home       = location_data[5]
            calc_dist_from_home       = location_data[6]
            waze_dist_from_home_moved = location_data[7]
            calc_dist_from_home_moved = location_data[8]
            waze_dist_last_poll_moved = location_data[9]
            calc_dist_last_poll_moved = location_data[10]
            waze_time_from_home       = location_data[11]
            last_dist_from_home       = location_data[12]
            last_dir_of_travel        = location_data[13]
            dir_of_trav_msg           = location_data[14]
            timestamp                 = location_data[15]


        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetLocation')
            return attrs_msg

        try:
            log_msg = ("►►DETERMINE INTERVAL Entered ~~{}~~, "
                          "location_data={}").format(devicename, location_data)
            self._LOGGER_debug_msg(log_msg)

    #       the following checks the distance from home and assigns a
    #       polling interval in minutes.  It assumes a varying speed and
    #       is generally set so it will poll one or twice for each distance
    #       group. When it gets real close to home, it switches to once
    #       each 15 seconds so the distance from home will be calculated
    #       more often and can then be used for triggering automations
    #       when you are real close to home. When home is reached,
    #       the distance will be 0.

            calc_interval = round(self._km_to_mi(dist_from_home) / 1.5, 0) * 60
            if self.waze_status == WAZE_USED:
                waze_interval = \
                    round(waze_time_from_home * 60 * \
                            self.travel_time_factor , 0)
            else:
                waze_interval = 0
            interval = 15
            interval_multiplier = 1

            inzone_flag          = (self._is_inzoneZ(current_zone))
            not_inzone_flag      = (self._isnot_inzoneZ(current_zone))
            was_inzone_flag      = (self._was_inzone(devicename))
            wasnot_inzone_flag   = (self._wasnot_inzone(devicename))
            inzone_home_flag     = (current_zone == self.base_zone)     #'home')
            was_inzone_home_flag = \
                (self.state_last_poll.get(devicename) == self.base_zone) #'home')
            near_zone_flag       = (current_zone == 'near_zone')

            log_msg = (
                "Zone={} ,IZ={}, NIZ={}, WIZ={}, WNIZ={}, IZH={}, WIZH={}, "
                "NZ={}").format(
                current_zone, inzone_flag, not_inzone_flag, was_inzone_flag,
                wasnot_inzone_flag, inzone_home_flag, was_inzone_home_flag,
                near_zone_flag)
            self._LOGGER_debug_msg(log_msg)

            log_method  = ''
            log_msg     = ''
            log_value   = ''

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetupZone')
            return attrs_msg

        try:
            #Note: If current_state is 'near_zone', it is reset to 'not_home' when
            #updating the device_tracker state so it will not trigger a state chng
            if self.state_change_flag.get(devicename):
                if inzone_flag:
                    if ('stationary' in current_zone):
                        interval = self.stat_zone_inzone_interval
                        log_method = "1sz-Stationary"
                        log_msg    = 'Zone={}'.format(current_zone)
                    else:
                        interval = self.inzone_interval
                        log_method="1ez-EnterZone"

                #entered 'near_zone' zone if close to 'home' and last is 'not_home'
                elif (near_zone_flag and wasnot_inzone_flag and
                        calc_dist_from_home < 2):
                    interval = 15
                    dir_of_travel = 'NearZone'
                    log_method="1nz-EnterHomeNearZone"

                #entered 'near_zone' zone if close to 'home' and last is 'not_home'
                elif (near_zone_flag and was_inzone_flag and
                        calc_dist_from_home < 2):
                    interval = 15
                    dir_of_travel = 'NearZone'
                    log_method="1nhz-EnterNearHomeZone"

                #exited 'home' zone
                elif (not_inzone_flag and was_inzone_home_flag):
                    interval = 240
                    dir_of_travel = 'away_from'
                    log_method="1ehz-ExitHomeZone"

                #exited 'other' zone
                elif (not_inzone_flag and was_inzone_flag):
                    interval = 120
                    dir_of_travel = 'left_zone'
                    log_method="1ez-ExitZone"

                #entered 'other' zone
                else:
                    interval = 240
                    log_method="1zc-ZoneChanged"

                log_msg = 'Zone={}, Last={}, This={}'.format(current_zone,
                            self.state_last_poll.get(devicename),
                            self.state_this_poll.get(devicename))
                self._LOGGER_debug_msg(log_msg)

            #poor gps & cnt > 8
            elif (self.poor_gps_accuracy_flag.get(devicename) and
                    self.poor_gps_accuracy_cnt.get(devicename) >= 8):
                self.poor_gps_accuracy_cnt[devicename] = 0
                interval   = 60      #poor accuracy, try again in 1 minute
                log_method = '2c-PoorGPSCnt'

            #inzone & poor gps & do not ignore gps when inzone
            elif (self.poor_gps_accuracy_flag.get(devicename) and
                    (inzone_flag and not
                        self.ignore_gps_accuracy_inzone_flag) and
                    dist_from_home > 2):
                interval   = 60      #poor accuracy, try again in 1 minute
                log_method = '2-PoorGPS'

            elif self.overrideinterval_seconds.get(devicename) > 0:
                interval   = self.overrideinterval_seconds.get(devicename)
                log_method = '3-Override'

            elif ('stationary' in current_zone):
                interval = self.stat_zone_inzone_interval
                log_method = "4sz-Stationary"
                log_msg    = 'Zone={}'.format(current_zone)

            elif (inzone_home_flag or
                    (dist_from_home < .05 and dir_of_travel == 'towards')):
                interval   = self.inzone_interval
                log_method = '4iz-InZone'
                log_msg    = 'Zone={}'.format(current_zone)

            elif current_zone == 'near_zone':
                interval = 15
                log_method = '4nz-NearZone'
                log_msg    = 'Zone={}, Dir={}'.format(
                                    current_zone, dir_of_travel)

            #in another zone and inzone time > travel time
            elif (inzone_flag and self.inzone_interval > waze_interval):
                interval   = self.inzone_interval
                log_method = '4iz-InZone'
                log_msg    = 'Zone={}'.format(current_zone)

            elif dir_of_travel in ('left_zone', 'not_set'):
                interval = 150
                if inzone_home_flag:
                    dir_of_travel = 'away_from'
                else:
                    dir_of_travel = 'not_set'
                log_method = '5-NeedInfo'
                log_msg    = 'ZoneLeft={}'.format(current_zone)

            elif dist_from_home < 2.5 and self.went_3km.get(devicename):
                interval   = 15             #1.5 mi=real close and driving
                log_method = '10a-Dist < 2.5km(1.5mi)'

            elif dist_from_home < 3.5:      #2 mi=30 sec
                interval   = 30
                log_method = '10b-Dist < 3.5km(2mi)'

            elif waze_time_from_home > 5 and waze_interval > 0:
                interval   = waze_interval
                log_method = '10c-WazeTime'
                log_msg    = 'TimeFmHome={}'.format(waze_time_from_home)

            elif dist_from_home < 5:        #3 mi=1 min
                interval   = 60
                log_method = '10d-Dist < 5km(3mi)'

            elif dist_from_home < 8:        #5 mi=2 min
                interval   = 120
                log_method = '10e-Dist < 8km(5mi)'

            elif dist_from_home < 12:       #7.5 mi=3 min
                interval   = 180
                log_method = '10f-Dist < 12km(7mi)'

            elif location_isold_flag:
                interval     = 300
                log_method   = '5ol-LoctionOld'
                log_msg      = 'Cnt={}'.format(
                                    self.location_isold_cnt.get(devicename))

            elif dist_from_home < 20:       #12 mi=10 min
                interval   = 600
                log_method = '10g-Dist < 20km(12mi)'

            elif dist_from_home < 40:       #25 mi=15 min
                interval   = 900
                log_method = '10h-Dist < 40km(25mi)'

            elif dist_from_home > 150:      #90 mi=1 hr
                interval   = 3600
                log_method = '10i-Dist > 150km(90mi)'

            else:
                interval   = calc_interval
                log_method = '20-Calculated'
                log_msg    = 'Value={}/1.5'.format(self._km_to_mi(dist_from_home))

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetInterval')


        try:
            #if haven't moved far for 8 minutes, put in stationary zone
            #determined in get_dist_data with dir_of_travel
            if dir_of_travel == 'stationary':
                interval = self.stat_zone_inzone_interval
                log_method = "21-Stationary"

                if self.in_stationary_zone_flag.get(devicename) is False:
                    rtn_code = self._update_stationary_zone(devicename,
                            latitude, longitude, False)

                    self.zone_current[devicename] = \
                            self._stationary_zone_name(devicename)
                    self.zone_timestamp[devicename] = \
                                dt_util.now().strftime(
                                        self.um_date_time_strfmt)
                    self.in_stationary_zone_flag[devicename] = rtn_code
                    if rtn_code:
                        self._save_event(devicename, "Set up Stationary Zone")
                        log_method_im   = "●Set.Stationary.Zone"
                        current_zone    = 'stationary'
                        dir_of_travel   = 'in_zone'
                        inzone_flag     = True
                        not_inzone_flag = False
                    else:
                        dir_of_travel = 'not_set'

            if dir_of_travel in ('', 'away_from') and interval < 180:
                interval = 180
                log_method_im = '30-Away(<3min)'

            elif (dir_of_travel == 'away_from' and
                    not self.distance_method_waze_flag):
                interval_multiplier = 2    #calc-increase timer
                log_method_im = '30-Away(Calc)'

            elif (dir_of_travel == 'not_set' and interval > 180):
                interval = 180

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetStatZone')


        try:
            #if triggered by ios app (Zone Enter/Exit, Manual, Fetch, etc.)
            #and interval < 3 min, set to 3 min. Leave alone if > 3 min.
            if (self.iosapp_update_flag.get(devicename) and
                    interval < 180 and
                    self.overrideinterval_seconds.get(devicename) == 0):
                interval   = 180
                log_method = '0-iosAppTrigger'

            #no longer in stationary, reset old Stationary Zone location info
            if (not_inzone_flag and
                    self.in_stationary_zone_flag.get(devicename)):
                self.in_stationary_zone_flag[devicename] = False

                rtn_code = self._update_stationary_zone(devicename,
                    self.stat_zone_base_latitude,
                    self.stat_zone_base_longitude, True)
                    #latitude, longitude, True)
                self._save_event(devicename, "Left Stationary Zone")

            #if changed zones on this poll reset multiplier
            if self.state_change_flag.get(devicename):
                interval_multiplier = 1

            #Check accuracy again to make sure nothing changed, update counter
            if self.poor_gps_accuracy_flag.get(devicename):
                interval_multiplier = 1

        except Exception as err:
            attrs_msg = self._internal_error_msg(
                    fct_name, err, 'ResetStatZone')
            return attrs_msg


        try:
            #Real close, final check to make sure interval is not adjusted
            if interval <= 60 or \
                    (battery > 0 and battery <= 33 and interval >= 120):
                interval_multiplier = 1

            interval     = interval * interval_multiplier
            interval, x  = divmod(interval, 15)
            interval     = interval * 15
            interval_str = self._secs_to_time_str(interval)

            interval_debug_msg = ("●Interval={} ({}, {}), ●DirOfTrav={}, "
                        "●State={}->{}, Zone={}").format(
                        interval_str, log_method, log_msg, dir_of_trav_msg,
                        self.state_last_poll.get(devicename),
                        self.state_this_poll.get(devicename), current_zone)
            event_msg = ("Interval basis: {}, {}, Dir={}").format(
                        log_method, log_msg, dir_of_travel)
            self._save_event(devicename, event_msg)

            if interval_multiplier != 1:
               interval_debug_msg = "{}, Multiplier={}({})".format(\
                        interval_debug_msg, interval_multiplier, log_method_im)

            #check if next update is past midnight (next day), if so, adjust it
            next_poll = round((self.this_update_seconds + interval)/15, 0) * 15

            # Update all dates and other fields
            self.interval_seconds[devicename]    = interval
            self.last_update_seconds[devicename] = self.this_update_seconds
            self.next_update_seconds[devicename] = next_poll
            self.last_update_time[devicename]    = \
                        self._secs_to_time(self.this_update_seconds)
            self.next_update_time[devicename]    = \
                        self._secs_to_time(next_poll)
            self.interval_str[devicename]        = interval_str

            #if more than 3km(1.8mi) then assume driving, used later above
            if dist_from_home > 3:                # 1.8 mi
                self.went_3km[devicename] = True
            elif dist_from_home < .03:            # home, reset flag
                 self.went_3km[devicename] = False

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetTimes')


        try:
            info = self._setup_info_attr(devicename, battery,
                                gps_accuracy, dist_last_poll_moved,
                                current_zone, location_isold_flag)
        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'InfoAttr')


        try:
            log_msg = ("►►INTERVAL FORMULA, {}").format(interval_debug_msg)
            self._LOGGER_debug_msg(log_msg)

            if 'interval' not in self.debug_control:
                interval_debug_msg = ''

            log_msg = ("►►DETERMINE INTERVAL <COMPLETE>,  ~~{}~~, "
                      "This poll: {}({}), Last Update: {}({}), "
                      "Next Update: {}({}),  Interval: {}*{}, "
                      "OverrideInterval={}, DistTraveled={}, CurrZone={}").\
                      format(devicename,
                      self._secs_to_time(self.this_update_seconds),
                      self.this_update_seconds,
                      self.last_update_time.get(devicename),
                      self.last_update_seconds.get(devicename),
                      self.next_update_time.get(devicename),
                      self.next_update_seconds.get(devicename),
                      self.interval_str.get(devicename),
                      interval_multiplier,
                      self.overrideinterval_seconds.get(devicename),
                      dist_last_poll_moved, current_zone)
            self._LOGGER_debug_msg(log_msg)

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'ShowMsgs')


        try:
            #if 'NearZone' zone, do not change the state
            if near_zone_flag:
                current_zone = 'not_home'

            log_msg = ("►►DIR OF TRAVEL ATTRS, Direction={}, LastDir={}, "
                           "Dist={}, LastDist={}, SelfDist={}, Moved={},"
                           "WazeMoved={}").format(
                           dir_of_travel, last_dir_of_travel, dist_from_home,
                           last_dist_from_home, self.dist.get(devicename),
                           dist_from_home_moved, waze_dist_from_home_moved)
            self._LOGGER_debug_msg(log_msg)

            #if poor gps and moved less than 1km, redisplay last distances
            if (self.poor_gps_accuracy_flag.get(devicename) and
                            dist_last_poll_moved < 1):
                dist_from_home      = self.dist.get(devicename)
                waze_dist_from_home = self.waze_dist.get(devicename)
                calc_dist_from_home = self.calc_dist.get(devicename)
                waze_time_msg       = self.waze_time.get(devicename)

            else:
                waze_time_msg       = self._format_waze_time_msg(devicename,
                                                    waze_time_from_home,
                                                    waze_dist_from_home)

                #save for next poll if poor gps
                self.dist     [devicename] = dist_from_home
                self.waze_dist[devicename] = waze_dist_from_home
                self.waze_time[devicename] = waze_time_msg
                self.calc_dist[devicename] = calc_dist_from_home

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetDistDir')

        speed_data = self._get_speed(devicename, waze_dist_from_home,
                                dist_last_poll_moved)

        speed         = self._km_to_mi(speed_data[0], 0)
        speed_high    = self._km_to_mi(speed_data[1], 0)
        speed_average = self._km_to_mi(speed_data[2], 0)

        try:
            #Save last and new state, set attributes
            #If first time thru, set the last state to the current state
            #so a zone change will not be triggered next time
            if self.state_last_poll.get(devicename) == 'not_set':
                self.state_last_poll[devicename] = current_zone

            #When put into stationary zone, also set last_poll so it
            #won't trigger again on next cycle as a state change
            elif (self.state_last_poll.get(devicename) == 'not_home' and
                    'stationary' in current_zone):
                self.state_last_poll[devicename] = 'stationary'
            else:
                self.state_last_poll[devicename] = \
                        self.state_this_poll.get(devicename)
            self.state_this_poll[devicename] = current_zone


            attrs = {}
            attrs[ATTR_ZONE]              = self.zone_current.get(devicename)
            attrs[ATTR_ZONE_TIMESTAMP]    = \
                        str(self.zone_timestamp.get(devicename))
            attrs[ATTR_LAST_ZONE]         = self.zone_last.get(devicename)
            attrs[ATTR_LAST_UPDATE_TIME]  = \
                        self._secs_to_time(self.this_update_seconds)

            #if (self.CURRENT_MODE_IOSAPP and
            #    self.iosapp_location_update_cnt.get(devicename) > \
            #            self.max_iosapp_locate_cnt):
            #    attrs[ATTR_INTERVAL]          = "●iCloudOff●"
            #    attrs[ATTR_NEXT_UPDATE_TIME]  = ""
            #else:
            attrs[ATTR_INTERVAL]          = interval_str
            attrs[ATTR_NEXT_UPDATE_TIME]  = \
                        self._secs_to_time(next_poll)

            attrs[ATTR_WAZE_TIME]     = ''
            if self.waze_status == WAZE_USED:
                attrs[ATTR_WAZE_TIME]     = waze_time_msg
                attrs[ATTR_WAZE_DISTANCE] = self._km_to_mi(waze_dist_from_home)
            elif self.waze_status == WAZE_NOT_USED:
                attrs[ATTR_WAZE_DISTANCE] = 'WazeOff'
            elif self.waze_status == WAZE_ERROR:
                attrs[ATTR_WAZE_DISTANCE] = 'NoRoutes'
            elif self.waze_status == WAZE_OUT_OF_RANGE:
                if waze_dist_from_home < 1:
                    attrs[ATTR_WAZE_DISTANCE] = ''
                elif waze_dist_from_home < self.waze_min_distance:
                    attrs[ATTR_WAZE_DISTANCE] = 'DistLow'
                else:
                    attrs[ATTR_WAZE_DISTANCE] = 'DistHigh'
            elif dir_of_travel == 'in_zone':
                attrs[ATTR_WAZE_DISTANCE] = ''
            elif self.waze_status == WAZE_PAUSED:
                attrs[ATTR_WAZE_DISTANCE] = 'Paused'
            elif waze_dist_from_home > 0:
                attrs[ATTR_WAZE_TIME]     = waze_time_msg
                attrs[ATTR_WAZE_DISTANCE] = self._km_to_mi(waze_dist_from_home)
            else:
                attrs[ATTR_WAZE_DISTANCE] = ''

            attrs[ATTR_ZONE_DISTANCE]   = self._km_to_mi(dist_from_home)
            attrs[ATTR_CALC_DISTANCE]   = self._km_to_mi(calc_dist_from_home)
            attrs[ATTR_DIR_OF_TRAVEL]   = dir_of_travel
            attrs[ATTR_TRAVEL_DISTANCE] = self._km_to_mi(dist_last_poll_moved)
            attrs[ATTR_SPEED]           = speed
            attrs[ATTR_SPEED_HIGH]      = speed_high
            attrs[ATTR_SPEED_AVERAGE]   = speed_average

            #save for event log
            self.last_tavel_time[devicename]   = waze_time_msg
            self.last_distance_str[devicename] = '{} {}'.format(
                    self._km_to_mi(dist_from_home), self.unit_of_measurement)

            attrs[ATTR_INFO] = interval_debug_msg + info

            self._trace_device_attributes(
                devicename, 'Results', fct_name, attrs)

            return attrs

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetAttrs')
            _LOGGER.exception(err)
            return attrs_msg

#########################################################
#
#   UPDATE DEVICE LOCATION & INFORMATION ATTRIBUTE FUNCTIONS
#
#########################################################

    def _get_device_distance_data(self, devicename, latitude, longitude,
                                gps_accuracy, location_isold_flag):
        """ Determine the location of the device.
            Returns:
                - current_zone (current zone from lat & long)
                  set to 'home' if distance < home zone radius
                - dist_from_home (mi or km)
                - dist_traveled (since last poll)
                - dir_of_travel (towards, away_from, stationary, in_zone,
                                       left_zone, near_home)
        """

        fct_name = '_get_device_distance_data'

        try:
            log_msg = (
                "►►GET DEVICE DISTANCE DATA Entered ~~{}~~").format(devicename)
            self._LOGGER_debug_msg(log_msg)

            last_dir_of_travel  = 'not_set'
            last_dist_from_home = 0
            last_waze_time      = 0
            last_lat            = self.zone_home_lat
            last_long           = self.zone_home_long
            dev_timestamp       = ZERO_HHMMSS

            attrs = self._get_device_attributes(devicename)

            self._trace_device_attributes(
                devicename, 'Read', fct_name, attrs)

            #Not available if first time after reset
            if self.state_last_poll.get(devicename) != 'not_set':
                log_msg = ("Distance info available")
                dev_timestamp   = attrs[ATTR_TIMESTAMP]
                dev_timestamp   = \
                        self._timestamp_to_time_dev(dev_timestamp)

                last_dist_from_home_s  = attrs[ATTR_ZONE_DISTANCE]
                last_dist_from_home    = \
                            self._mi_to_km(float(last_dist_from_home_s))

                last_waze_time     = attrs[ATTR_WAZE_TIME]
                last_dir_of_travel = attrs[ATTR_DIR_OF_TRAVEL]
                last_dir_of_travel = last_dir_of_travel.replace('*', '', 99)
                last_dir_of_travel = last_dir_of_travel.replace('?', '', 99)
                last_lat           = self.last_lat.get(devicename)
                last_long          = self.last_long.get(devicename)

            #get last interval
            interval_str = self.interval_str.get(devicename)
            interval     = self._time_str_to_secs(interval_str)

            this_lat  = latitude
            this_long = longitude

        except Exception as err:
            _LOGGER.exception(err)
            attrs = self._internal_error_msg(fct_name, err, 'SetupLocation')
            return ('ERROR', attrs)

        try:
            current_zone = self._get_current_zone(devicename,
                    this_lat, this_long)

            log_msg = ("►►LAT-LONG GPS INITIALIZED >>> {}, LastDirOfTrav={}, "
                  "LastGPS=({}, {}), ThisGPS=({}, {}, UsingGPS=({}, {}), "
                  "GPS.Accur={}, GPS.Threshold={}").format(
                  current_zone, last_dir_of_travel,
                  last_lat, last_long, this_lat, this_long,
                  latitude, longitude,
                  gps_accuracy, self.gps_accuracy_threshold)
            self._LOGGER_debug_msg(log_msg)

            # Get Waze distance & time
            #   Will return [error, 0, 0, 0] if error
            #               [out_of_range, dist, time, info] if
            #                           last_dist_from_home >
            #                           last distance from home
            #               [ok, 0, 0, 0]  if zone=home
            #               [ok, distFmHome, timeFmHome, info] if OK

            calc_dist_from_home = \
                        self._calc_distance(this_lat, this_long,
                                    self.zone_home_lat, self.zone_home_long)
            calc_dist_last_poll_moved = \
                        self._calc_distance(last_lat, last_long,
                                    this_lat, this_long)
            calc_dist_from_home_moved = \
                        (calc_dist_from_home - last_dist_from_home)
            calc_dist_from_home = \
                        self._round_to_zero(calc_dist_from_home)
            calc_dist_last_poll_moved = \
                        self._round_to_zero(calc_dist_last_poll_moved)
            calc_dist_from_home_moved = \
                        self._round_to_zero(calc_dist_from_home_moved)

            if self.distance_method_waze_flag:
                #If waze paused via icloud_command, default to pause
                if self.waze_manual_pause_flag:
                    self.waze_status = WAZE_PAUSE
                else:
                    self.waze_status = WAZE_USED
            else:
                self.waze_status = WAZE_NOT_USED

            #Make sure distance and zone are correct for 'home', initialize
            if calc_dist_from_home < .05 or current_zone == self.base_zone:     #'home'
                current_zone              = self.base_zone      #'home'
                calc_dist_from_home       = 0
                calc_dist_last_poll_moved = 0
                calc_dist_from_home_moved = 0
                self.waze_status          = WAZE_PAUSED

            #Near home & towards or in near_zone
            elif (calc_dist_from_home < 1 and
                    last_dir_of_travel in ('towards', 'near_zone')):
                self.waze_status = WAZE_PAUSED

                log_msg = "Using Calc Method (near Home & towards or Waze off)"
                self._LOGGER_debug_msg(log_msg)
                event_msg = ("Using Calc method, near Home or Waze off")
                self._save_event(devicename, event_msg)

            #Initialize Waze default fields
            waze_dist_from_home       = calc_dist_from_home
            waze_time_from_home       = 0
            waze_dist_last_poll_moved = calc_dist_last_poll_moved
            waze_dist_from_home_moved = calc_dist_from_home_moved
            self.waze_history_data_used_flag[devicename] = False

            #Use Calc if close to home, Waze not accurate when close
            if self.waze_status == WAZE_USED:
                try:
                    #See if another device is close with valid Waze data.
                    #If so, use it instead of calling Waze again.
                    waze_dist_time_info = self._get_waze_from_data_history(
                            devicename, calc_dist_from_home,
                            this_lat, this_long)

                    #No Waze data from close device. Get it from Waze
                    if waze_dist_time_info is None:
                        self._save_event(devicename, "Calling Waze")
                        waze_dist_time_info = self._get_waze_data(devicename,
                                                        this_lat, this_long,
                                                        last_lat, last_long,
                                                        current_zone,
                                                        last_dist_from_home)

                    self.waze_status = waze_dist_time_info[0]

                    if self.waze_status != WAZE_ERROR:
                        waze_dist_from_home       = waze_dist_time_info[1]
                        waze_time_from_home       = waze_dist_time_info[2]
                        waze_dist_last_poll_moved = waze_dist_time_info[3]
                        waze_dist_from_home_moved = round(waze_dist_from_home
                                                    - last_dist_from_home, 2)
                        event_msg = ("Waze successful, distance {} {}, "
                                "time {} min").format(
                                self._km_to_mi(waze_dist_from_home),
                                self.unit_of_measurement,
                                waze_time_from_home)
                        self._save_event(devicename, event_msg)
                        #Save new Waze data or retimestamp data from another
                        #device.
                        self.waze_distance_history[devicename] = \
                                [self._time_now_secs(),
                                this_lat, this_long, waze_dist_time_info]

                    else:
                        self._save_event(devicename,
                                "Waze error, no data returned")
                        self.waze_distance_history[devicename] = []

                except Exception as err:
                    self.waze_distance_history[devicename] = []
                    self.waze_status = WAZE_ERROR

        except Exception as err:
            attrs = self._internal_error_msg(fct_name, err, 'WazeError')
            return ('ERROR', attrs)

        try:
            #don't reset data if poor gps, use the best we have
            if current_zone == self.base_zone:      #'home':
                distance_method      = 'Home/Calc'
                dist_from_home       = 0
                dist_last_poll_moved = 0
                dist_from_home_moved = 0
            elif self.waze_status == WAZE_USED:
                distance_method      = 'Waze'
                dist_from_home       = waze_dist_from_home
                dist_last_poll_moved = waze_dist_last_poll_moved
                dist_from_home_moved = waze_dist_from_home_moved
            else:
                distance_method      = 'Calc'
                dist_from_home       = calc_dist_from_home
                dist_last_poll_moved = calc_dist_last_poll_moved
                dist_from_home_moved = calc_dist_from_home_moved

            if dist_from_home > 99: dist_from_home = int(dist_from_home)
            if dist_last_poll_moved > 99: dist_last_poll_moved = int(dist_last_poll_moved)
            if dist_from_home_moved > 99: dist_from_home_moved = int(dist_from_home_moved)

            dist_from_home_moved = self._round_to_zero(dist_from_home_moved)

            log_msg = ("►►DISTANCES CALCULATED, "
                  "Zone={}, Method={},LastDistFmHome={}, WazeStatus={}").\
                  format(current_zone, distance_method,
                         last_dist_from_home, self.waze_status)
            self._LOGGER_debug_msg(log_msg)
            log_msg = ("►►DISTANCES ...Waze, "
                  "Dist={}, LastPollMoved={}, FmHomeMoved={}, "
                  "Time={}, Status={}").format(
                  waze_dist_from_home, waze_dist_last_poll_moved,
                  waze_dist_from_home_moved, waze_time_from_home,
                  self.waze_status)
            self._LOGGER_debug_msg(log_msg)
            log_msg = ("►►DISTANCES ...Calc, "
                  "Dist={}, LastPollMoved={}, FmHomeMoved={}").format(
                  calc_dist_from_home, calc_dist_last_poll_moved,
                  calc_dist_from_home_moved)
            self._LOGGER_debug_msg(log_msg)

            #if didn't move far enough to determine towards or away_from,
            #keep the current distance and add it to the distance on the next
            #poll
            if (dist_from_home_moved > -.3 and dist_from_home_moved < .3):
                dist_from_home_moved += \
                        self.dist_from_home_small_move_total.get(devicename)
                self.dist_from_home_small_move_total[devicename] = \
                        dist_from_home_moved
            else:
                 self.dist_from_home_small_move_total[devicename] = 0
        except Exception as err:
            attrs = self._internal_error_msg(fct_name, err, 'CalcDist')
            return ('ERROR', attrs)


        try:
            section = "dir_of_trav"
            dir_of_travel   = ''
            dir_of_trav_msg = ''
            if current_zone not in ('not_home', 'near_zone'):
                dir_of_travel   = 'in_zone'
                dir_of_trav_msg = ("Zone={}").format(current_zone)

            elif last_dir_of_travel == "in_zone":
                dir_of_travel   = 'left_zone'
                dir_of_trav_msg = ("LastZone={}").format(last_dir_of_travel)

            elif dist_from_home_moved <= -.3:            #.18 mi
                dir_of_travel   = 'towards'
                dir_of_trav_msg = ("Dist={}").format(dist_from_home_moved)

            elif dist_from_home_moved >= .3:             #.18 mi
                dir_of_travel   = 'away_from'
                dir_of_trav_msg = ("Dist={}").format(dist_from_home_moved)

            elif self.poor_gps_accuracy_flag.get(devicename):
                dir_of_travel   = 'Poor.GPS'
                dir_of_trav_msg = ("Poor.GPS={}").format(gps_accuracy)

            else:
                #didn't move far enough to tell current direction
                dir_of_travel   = ("{}?").format(last_dir_of_travel)
                dir_of_trav_msg = ("Moved={}").format(dist_last_poll_moved)

            #If moved more than stationary zone limit (~.06km(200ft)),
            #reset check StatZone 5-min timer and check again next poll
            #Use calc distance rather than waze for better accuracy
            section = "test if home"
            if (calc_dist_from_home > self.stat_min_dist_from_home and
                current_zone == 'not_home'):

                section = "test moved"
                reset_stat_zone_flag = False
                if devicename not in self.stat_zone_moved_total:
                    reset_stat_zone_flag = True

                elif (calc_dist_last_poll_moved > self.stat_dist_move_limit):
                    reset_stat_zone_flag = True

                if reset_stat_zone_flag:
                    section = "test moved-reset stat zone "
                    self.stat_zone_moved_total[devicename] = 0
                    self.stat_zone_timer[devicename] = \
                        self.this_update_seconds + self.stat_zone_still_time

                    log_msg = ("►►STATIONARY ZONE, Reset timer, "
                            "Moved={}, Timer={}").format(
                            calc_dist_last_poll_moved,
                            self._secs_to_time(
                                self.stat_zone_timer.get(devicename)))
                    self._LOGGER_debug_msg(log_msg)

                #If moved less than the stationary zone limit, update the
                #distance moved and check to see if now in a stationary zone
                elif devicename in self.stat_zone_moved_total:
                    section = "test moved-else "
                    self.stat_zone_moved_total[devicename] += \
                            calc_dist_last_poll_moved
                    section = "test moved-else-logmsg"
                    log_msg = ("►►STATIONARY ZONE, Small movement check, "
                            "TotalMoved={}, Timer={}").format(
                            self.stat_zone_moved_total.get(devicename),
                            self._secs_to_time(
                                self.stat_zone_timer.get(devicename)))
                    self._LOGGER_debug_msg(log_msg)

                    #If the stationary has moved less than the limit and
                    #reached the timer time or the update was triggered by the
                    #ios app and the currentstate is already 'stationary' (it will
                    #be 'stationary' if the stationary zone already exists), then
                    #set the dir_of_travel to 'stationary' whicn will create the
                    #actual stationary zone in determine_interval.
                    section = "test moved-else-test set stat"
                    if ((self.this_update_seconds >= \
                            self.stat_zone_timer.get(devicename) and
                        self.stat_zone_moved_total.get(devicename) <= \
                            self.stat_dist_move_limit) or
                        (self.iosapp_update_flag.get(devicename) and
                            self.state_this_poll.get(devicename) == 'stationary')):
                        dir_of_travel   = 'stationary'
                        dir_of_trav_msg = "Age={}s, Moved={}".format(
                            self._secs_to(
                                self.stat_zone_timer.get(devicename)),
                                self.stat_zone_moved_total.get(devicename))
                else:
                    self.stat_zone_moved_total[devicename] = 0

            dir_of_trav_msg = ("{}({})").format(
                        dir_of_travel, dir_of_trav_msg)

            log_msg = ("►►DIR OF TRAVEL DETERMINED, {}").format(
                        dir_of_trav_msg)
            self._LOGGER_debug_msg(log_msg)

            log_msg = ("►►GET DEVICE DISTANCE DATA Complete ~~{}~~, "
                        "CurrentZone={}, DistFmHome={}, DistFmHomeMoved={}, "
                        "DistLastPollMoved={}").format(
                        devicename, current_zone, dist_from_home,
                        dist_from_home_moved, dist_last_poll_moved)
            self._LOGGER_debug_msg(log_msg)

            distance_data = (current_zone, dir_of_travel,
                    dist_from_home, dist_from_home_moved, dist_last_poll_moved,
                    waze_dist_from_home, calc_dist_from_home,
                    waze_dist_from_home_moved, calc_dist_from_home_moved,
                    waze_dist_last_poll_moved, calc_dist_last_poll_moved,
                    waze_time_from_home, last_dist_from_home,
                    last_dir_of_travel, dir_of_trav_msg, dev_timestamp)

            #log_msg = ("►►Distance_data=={}-{}").format(
            #            devicename, distance_data)
            #self._LOGGER_debug_msg(log_msg)

            return  distance_data

        except Exception as err:
            attrs = self._internal_error_msg(fct_name+section, err, 'PrepData')
            _LOGGER.exception(err)
            return ('ERROR', attrs)

#------------------------------------------------------------------------
    def _get_speed(self, devicename, waze_dist_from_home,
                dist_last_poll_moved):
        '''
        Return:
            - speed since the last poll (distance moved/time sine last poll)
            - average speed (distance from last zone/time since exited)
            - high speed
        '''
        #if (devicename != 'gary_iphone'):
        return (0, 0, 0)

        try:
            speed         = self.speed.get(devicename)
            speed_high    = self.speed_high.get(devicename)
            speed_average = self.speed_average.get(devicename)

            _LOGGER.warning("GET SPEED, waze_dist=%s, dist_last_poll_moved=%s, "
                "speed=%s, speed_h=%s, speed_avg=%s",waze_dist_from_home,dist_last_poll_moved,speed,speed_high,speed_average)

            #If using Waze History, use previous speed since times are off
            if self.waze_history_data_used_flag.get(devicename):
                return (speed, speed_high, speed_average)

            #In a zone, save distance from home to use later if not in home zone
            elif self._is_inzone(devicename):
                self.speed[devicename] = 0
                self.last_zone_dist_home[devicename] = waze_dist_from_home
                _LOGGER.warning("Speed, Inzone, dist_fm_home=%s",waze_dist_from_home)
                return (0, speed_high, speed_average)

            #Not in a zone, check if just left home
            elif (self.last_zone_dist_home.get(devicename) == 0):
                self.last_zone_dist_home[devicename] = waze_dist_from_home
                _LOGGER.warning("Speed, LastZoneDist=0, SetToWaze=%s",waze_dist_from_home)

            if self._was_inzone(devicename):
                self.speed_high[devicename]          = 0
                self.speed_average[devicename]       = 0
                self.time_zone_exit_secs[devicename] = self.this_update_seconds
                self.dist_moved_last_zone_exit[devicename] = 0
                _LOGGER.warning("Speed, LeftZone, TimeZoneExit=%ssec",self.this_update_seconds)

            time_since_last_poll_hrs = self._secs_since(
                        self.last_update_seconds.get(devicename)) / 3600
            _LOGGER.warning("Speed, TimeSinceLastPoll=%shrs",time_since_last_poll_hrs)
            if time_since_last_poll_hrs > 0:
                speed = dist_last_poll_moved/time_since_last_poll_hrs
                if (speed > self.speed_high.get(devicename)):
                    speed_high = speed
                _LOGGER.warning("Speed=%s=DistLastPollMoved/TimeSinceLastPoll=(%skm/%shrs)",speed,dist_last_poll_moved,time_since_last_poll_hrs)

            self.dist_moved_last_zone_exit[devicename] += dist_last_poll_moved
            dist_moved_zone_exit = self.dist_moved_last_zone_exit.get(devicename)
            time_since_zone_exit_hrs = self._secs_since(
                        self.time_zone_exit_secs.get(devicename)) / 3600
            _LOGGER.warning("TimeSinceZoneExit=%shrs",time_since_zone_exit_hrs)
            if time_since_zone_exit_hrs > 0:
                speed_average = dist_moved_zone_exit/time_since_zone_exit_hrs
                _LOGGER.warning("SpeedAvg=%s=DistMovedZoneExit/TimeSinceZoneExit=(%skm/%shrs)",speed_average,dist_moved_zone_exit,time_since_zone_exit_hrs)
            self.speed[devicename]         = speed
            self.speed_high[devicename]    = speed_high
            self.speed_average[devicename] = speed_average

            log_msg = ("SpeedCalc: Speed={} (Dist/Time={}:{}), High={}, "
                        "Avg={} (Dist/Time={}:{})").format(
                speed, dist_last_poll_moved, time_since_last_poll_hrs,
                speed_high,
                speed_average, dist_moved_zone_exit, time_since_zone_exit_hrs)
            self._LOGGER_debug_msg(log_msg)
            self._save_event(devicename, log_msg)

        except Exception as err:
            attrs_msg = self._internal_error_msg("GetSpeed", err, 'SetSpeed')
            speed         = -1
            speed_high    = -1
            speed_average = -1
            #_LOGGER.exception(err)

        return (speed, speed_high, speed_average)

#########################################################
#
#    DEVICE ATTRIBUTES ROUTINES
#
#########################################################
    def _get_device_tracker_entity(self, devicename, iosapp_dt_entity):
        '''
        The iosapp device_tracker entity id may be different than the one
        used by the icloud account. Most of the time, it will be the same
        but it can be different based on the 'iosapp_device' configuration
        entry. This will get the right one based on the what function
        wants the data (from the iosapp device tracker or the one
        really associated with the device.
        '''
        iosapp_dt_entity = False
        if (iosapp_dt_entity):
            return self.device_tracker_entity_iosapp.get(devicename)
        else:
            return self.device_tracker_entity.get(devicename)

#--------------------------------------------------------------------
    def _get_current_state(self, devicename, iosapp_dt_entity = False):
        """
        Get current state of the device_tracker entity
        (home, away, other state)
        """

        entity_id = self._get_device_tracker_entity(devicename, iosapp_dt_entity)
        #_LOGGER.error("getcurrentstate e_id=%s",entity_id)
        #entity_id = self._get_device_tracker_entity(devicename, False)
        try:
            device_state = self.hass.states.get(entity_id).state

            if device_state:
                return device_state.lower()

            return 'not_home'

        except Exception as err:
            #_LOGGER.exception(err)
            return 'not_set'

#--------------------------------------------------------------------
    def _get_iosapp_sensor(self, devicename, sensor_entity):
        """
        Get the iosapp sensor data
        """

        entity_id = ("{}_{}").format(
                self.sensor_entity_iosapp.get(devicename), sensor_entity)
        entity_id = entity_id.replace("._",".",99)

        try:
            #_LOGGER.warning("Sensor=%s",entity_id)
            sensor_data = self.hass.states.get(entity_id)
            #_LOGGER.warning("Sensor=%s, Data=%s",entity_id,sensor_data)


            sensor_state = self.hass.states.get(entity_id).state
            sensor_attrs = self.hass.states.get(entity_id).attributes
            if sensor_state:
                sensor_state = sensor_state.lower()
            #_LOGGER.warning("Sensor=%s, State=%s, Attrs=%s",entity_id,sensor_state,sensor_attrs)

            return (sensor_state, sensor_attrs)

        except Exception as err:
            _LOGGER.exception(err)
            return ('not_set', None)
#--------------------------------------------------------------------
    def _get_device_attributes(self, devicename, iosapp_dt_entity = False):
        """ Get attributes of the device """

        try:
            entity_id = self._get_device_tracker_entity(devicename, iosapp_dt_entity)
            #_LOGGER.error("getattribute e_id=%s",entity_id)
            #entity_id = self._get_device_tracker_entity(devicename, False)
            dev_data  = self.hass.states.get(entity_id)
            dev_attrs = dev_data.attributes

            retry_cnt = 0
            while retry_cnt < 99:
                if dev_attrs:
                    break
                retry_cnt += 1
                log_msg = (
                    "No attribute data returned for {}. Retrying #{}").format(
                    devicename, retry_cnt)
                self._LOGGER_debug_msg(log_msg)

        except (KeyError, AttributeError):
            dev_attrs = {}
            pass

        except Exception as err:
            _LOGGER.exception(err)
            dev_attrs = {}
            dev_attrs[ATTR_TRIGGER] = 'Error {}'.format(err)

        return dict(dev_attrs)

#--------------------------------------------------------------------
    def _update_device_attributes(self, devicename, kwargs: str = None,
                        attrs: str = None, fct_name: str = 'Unknown'):
        """
        Update the device and attributes with new information
        On Entry, kwargs = {} or contains the base attributes.

        Trace the interesting attributes if debugging.

        Full set of attributes is:
        'gps': (27.726639, -80.3904565), 'battery': 61, 'gps_accuracy': 65.0
        'dev_id': 'lillian_iphone', 'host_name': 'Lillian',
        'location_name': 'home', 'source_type': 'gps',
        'attributes': {'interval': '2 hrs', 'last_update': '10:55:17',
        'next_update': '12:55:15', 'travel_time': '', 'distance': 0,
        'calc_distance': 0, 'waze_distance': 0, 'dir_of_travel': 'in_zone',
        'travel_distance': 0, 'info': ' ●Battery-61%',
        'group': 'gary_icloud', 'authenticated': '02/22/19 10:55:10',
        'last_located': '10:55:15', 'device_status': 'online',
        'low_power_mode': False, 'battery_status': 'Charging',
        'tracked_devices': 'gary_icloud/gary_iphone,
        gary_icloud/lillian_iphone', 'trigger': 'iCloud',
        'timestamp': '2019-02-22T10:55:17.543', 'poll_count': '1:0:1'}

        {'source_type': 'gps', 'latitude': 27.726639, 'longitude': -80.3904565,
        'gps_accuracy': 65.0, 'battery': 93, 'zone': 'home',
        'last_zone': 'home', 'zone_timestamp': '03/13/19, 9:47:35',
        'trigger': 'iCloud', 'timestamp': '2019-03-13T09:47:35.405',
        'interval': '2 hrs', 'travel_time': '', 'distance': 0,
        'calc_distance': 0, 'waze_distance': '', 'last_located': '9:47:34',
        'last_update': '9:47:35', 'next_update': '11:47:30',
        'poll_count': '1:0:2', 'dir_of_travel': 'in_zone',
        'travel_distance': 0, 'info': ' ●Battery-93%',
        'battery_status': 'NotCharging', 'device_status':
        'online', 'low_power_mode': False,
        'authenticated': '03/13/19, 9:47:26',
        'tracked_devices': 'gary_icloud/gary_iphone, gary_icloud/lillian_iphone',
        'group': 'gary_icloud', 'friendly_name': 'Gary',
        'icon': 'mdi:cellphone-iphone',
        'entity_picture': '/local/gary-caller_id.png'}
        """

        #Get friendly name or capitalize and reformat state
        state = self.state_this_poll.get(devicename)

        if self._is_inzoneZ(state):
            state_fn = self.zone_friendly_name.get(state)

            if state_fn:
                state = state_fn
            else:
                state = state.replace('_', ' ', 99)
                state = state.title()

            if state == 'Home':
                state = 'home'

        self.state_this_poll[devicename]    = state.lower()

        #Update the device timestamp
        if not attrs:
            attrs  = {}
        if ATTR_TIMESTAMP in attrs:
            timestamp = attrs[ATTR_TIMESTAMP]
        else:
            timestamp = dt_util.now().strftime(ATTR_TIMESTAMP_FORMAT)[0:23]
            attrs[ATTR_TIMESTAMP] = timestamp
        self.last_dev_timestamp[self.group+devicename] = timestamp

        #Calculate and display how long the update took
        update_took_time =  round(time.time() - \
                self.update_timer.get(devicename), 2)
        if update_took_time > 3 and ATTR_INFO in attrs:
            attrs[ATTR_INFO] = "{} ●Took {}s".format(
                    attrs[ATTR_INFO], update_took_time)

        attrs[ATTR_ICLOUD3_VERSION] = VERSION

        attrs[CONF_GROUP] = self.mode_short_name+"::"+self.group

        #Set the gps attribute and update the attributes via self.see
        if kwargs == {} or not kwargs:
            kwargs = self._setup_base_kwargs(devicename,
                            self.last_lat.get(devicename),
                            self.last_long.get(devicename), 0, 0)

        kwargs['dev_id']        = devicename
        kwargs['host_name']     = self.friendly_name.get(devicename)
        kwargs['location_name'] = state
        kwargs['source_type']   = 'gps'
        kwargs[ATTR_ATTRIBUTES] = attrs

        self.see(**kwargs)

        self._trace_device_attributes(
            devicename, 'Write', fct_name, kwargs)

        if timestamp == '':         #Bypass if no initializing
            return

        retry_cnt = 1
        timestamp = timestamp[10:]      #Strip off date

        #Quite often, the attribute update has not actually taken
        #before other code is executed and errors occur.
        #Reread the attributes of the ones just updated to make sure they
        #were updated corectly. Verify by comparing the timestamps. If
        #differet, retry the attribute update. HA runs in multiple threads.
        try:
             while retry_cnt < 99:
                chk_see_attrs  = self._get_device_attributes(devicename)
                chk_timestamp  = str(chk_see_attrs.get(ATTR_TIMESTAMP))
                chk_timestamp  = chk_timestamp[10:]

                log_msg = (
                    "Verify Check #{}. Expected {}, Read {}").format(
                    retry_cnt, timestamp, chk_timestamp)
                self._LOGGER_debug_msg(log_msg)

                if timestamp == chk_timestamp:
                    #if retry_cnt > 1:
                    #    log_msg = ("Attribute update retry #{} "
                    #        "successful").format(retry_cnt)
                    #    self._LOGGER_debug_msg(log_msg)
                    break

                #retry_cnt_msg = "Write Reread{}".format(retry_cnt)
                #self._trace_device_attributes(
                #    devicename, retry_cnt_msg, fct_name, chk_see_attrs)

                if (retry_cnt % 10) == 0:
                    time.sleep(1)
                retry_cnt += 1

                self.see(**kwargs)


        except Exception as err:
            _LOGGER.exception(err)

        return

#--------------------------------------------------------------------
    def _setup_base_kwargs(self, devicename, latitude, longitude,
            battery, gps_accuracy):

        #check to see if device set up yet
        state = self.state_this_poll.get(devicename)
        zone_name = None

        if latitude == self.zone_home_lat:
            pass
        elif state == 'not_set':
            zone_name = self.base_zone      #'home'

        #if in zone, replace lat/long with zone center lat/long
        elif self._is_inzoneZ(state):
            if state == 'stationary':
                zone_name = self._stationary_zone_name(devicename)
            else:
                zone_name = state

        if zone_name:
            if self.zone_latitude.get(zone_name):
                latitude  = self.zone_latitude.get(zone_name)
                longitude = self.zone_longitude.get(zone_name)

                self.last_lat[devicename]  = latitude
                self.last_long[devicename] = longitude
                log_msg = ("Overiding GPS for {} with {}, GPS={}:{}").format(
                            devicename, zone_name, latitude, longitude)

                self._LOGGER_debug_msg(log_msg)

        gps_lat_long           = (latitude, longitude)
        kwargs                 = {}
        kwargs['gps']          = gps_lat_long
        kwargs['battery']      = int(battery)
        kwargs['gps_accuracy'] = gps_accuracy

        return kwargs

#--------------------------------------------------------------------
    def _format_entity_id(self, devicename):

        return '{}.{}'.format(DOMAIN, devicename)
#--------------------------------------------------------------------
    def _trace_device_attributes(self, devicename, description,
            fct_name, attrs):

        try:

            #Extract only attrs needed to update the device
            attrs_in_attrs = {}
            if 'iCloud' in description:
                attrs_base_elements = TRACE_ICLOUD_ATTRS_BASE
                if ATTR_LOCATION in attrs:
                    attrs_in_attrs  = attrs[ATTR_LOCATION]
            elif 'Zone' in description:
                attrs_base_elements = attrs
            else:
                attrs_base_elements = TRACE_ATTRS_BASE
                if ATTR_ATTRIBUTES in attrs:
                    attrs_in_attrs  = attrs[ATTR_ATTRIBUTES]

            trace_attrs = {k: v for k, v in attrs.items() \
                                       if k in attrs_base_elements}

            trace_attrs_in_attrs = {k: v for k, v in attrs_in_attrs.items() \
                                       if k in attrs_base_elements}

            #trace_attrs = attrs

            ls = self.state_last_poll.get(devicename)
            cs = self.state_this_poll.get(devicename)
            log_msg = ("_____ {} _____ {} Attrs _____ ({})".format(
                devicename, description, fct_name))

            self._LOGGER_debug_msg(log_msg)
            log_msg = ("Last={}, This={}, Elements={}".format(ls, cs, len(attrs)))
            self._LOGGER_debug_msg(log_msg)

            log_msg = ("Attrs={}{}").format(
                    trace_attrs, trace_attrs_in_attrs)
            self._LOGGER_debug_msg(log_msg)


        except Exception as err:
            _LOGGER.exception(err)

        return

#--------------------------------------------------------------------
    def _notify_device(self, message, devicename = None):
        return
        for devicename_x in self.tracked_devices:
            if devicename and devicename_x != devicename:
                continue

            entity_id    = "ios_{}".format(devicename_x)
            msg = ('"{}"').format(message)
            service_data = {"message": "test message"}

            #_LOGGER.warning(service_data_q)
            #_LOGGER.warning(service_data)
            self.hass.services.call("notify", entity_id, service_data)

#########################################################
#
#   DEVICE ZONE ROUTINES
#
#########################################################
    def _get_current_zone(self, devicename, latitude, longitude):

        '''
        Get current zone of the device based on the location """

        This is the same code as (active_zone/async_active_zone) in zone.py
        but inserted here to use zone table loaded at startup rather than
        calling hass on all polls
        '''
        zone_name_dist = 99999
        zone_name      = None

        for zone in self.zone_latitude:
            #Skip stationary zones for now, only look at ones set up in HA
            if ('stationary' in zone):
                continue

            zone_dist = self._calc_distance(latitude, longitude,
                self.zone_latitude.get(zone), self.zone_longitude.get(zone))

            in_zone      = zone_dist < self.zone_radius.get(zone)
            closer_zone  = zone_name is None or zone_dist < zone_name_dist
            smaller_zone = (zone_dist == zone_name_dist and
                            self.zone_radius.get(zone) <
                            self.zone_radius.get(zone_name))

            if in_zone and (closer_zone or smaller_zone):
                zone_name_dist  = round(zone_dist, 2)
                zone_name       = zone

            log_msg = ("Zone Lookup, {}:{}, Dist={} (r{})").format(
                zone_name, zone,  zone_dist, self.zone_radius.get(zone))
            self._LOGGER_debug_msg(log_msg)

        if zone_name is None:
            #See if device is in it's stationary zone
            zone      = self._stationary_zone_name(devicename)
            zone_dist = self._calc_distance(latitude, longitude,
                    self.zone_latitude.get(zone), self.zone_longitude.get(zone))

            if zone_dist < self.zone_radius.get(zone):
                zone_name = zone
        '''
        if zone_name is None:
            #See if device is in another stationary zone
            for zone in self.zone_latitude:
                if ('stationary' not in zone):
                    continue

                zone_dist = self._calc_distance(latitude, longitude,
                    self.zone_latitude.get(zone),
                    self.zone_longitude.get(zone))

                if zone_dist < self.zone_radius.get(zone):
                    zone_name = zone

                log_msg = ("Zone Lookup, {}:{}, Dist={} (R{})").format(
                zone_name, zone,  zone_dist, self.zone_radius.get(zone))
                self._LOGGER_debug_msg(log_msg)
        '''
        if zone_name is None:
            zone_name      = 'not_home'
            zone_name_dist = 0

        elif 'nearzone' in zone_name:
            zone_name = 'near_zone'

        #If the zone changed from a previous poll, save it and set the new one
        if (self.zone_current.get(devicename) != zone_name):
            self.zone_last[devicename] = \
                    self.zone_current.get(devicename)

            #First time thru, initialize zone_last
            if (self.zone_last.get(devicename) == ''):
                self.zone_last[devicename]  = zone_name

            self.zone_current[devicename]   = zone_name
            self.zone_timestamp[devicename] = \
                        dt_util.now().strftime(self.um_date_time_strfmt)

        log_msg = ("►►GET CURRENT ZONE END, Zone={}, GPS=({}, {}), "
                        "StateThisPoll={}, LastZone={}, ThisZone={}").format(
                    zone_name, latitude, longitude,
                    self.state_this_poll.get(devicename),
                    self.zone_last.get(devicename),
                    self.zone_current.get(devicename))
        self._LOGGER_debug_msg(log_msg)

        return zone_name

#--------------------------------------------------------------------
    '''
    This routine is replaced by the _get_current_zone routine that uses zone
    information loaded when HA starts. It might have to be changed to
    detect zones
    def _get_current_zone_fn(self, devicename, latitude, longitude):

        #v0.93.x=current_zone = active_zone(self.hass, latitude, longitude)
        currentzone = run_callback_threadsafe(self.hass.loop, async_active_zone,
                self.hass, latitude, longitude).result()

        #Example current_zone:
        #<state zone.home=zoning; hidden=True, latitude=27.726639,
        #longitude=-80.3904565, radius=40.0, friendly_name=Home, icon=mdi:home,
        #beacon=ualias=9AC56DEE-E6F3-4446-A2BC-9A68D06BC0BB, major=1, minor=1

#        log_msg = ("►►GET CURRENT ZONE, Zone={}, GPS=({}, {}), "
#                        "StateThisPoll={}").format(
#                    current_zone, latitude, longitude,
#                    self.state_this_poll.get(devicename))
#        self._LOGGER_debug_msg(log_msg)

        if current_zone:
            current_zone = current_zone.attributes.get(ATTR_FRIENDLY_NAME)

            #Override 'NearZone' zone name, will be reset later to not_home
            if 'nearzone' in current_zone.lower():
                current_zone = 'near_zone'
        else:
            current_zone = 'not_home'

        log_msg = ("►►GET CURRENT ZONE, Zone={}, GPS=({}, {}), "
                        "StateThisPoll={}").format(
                    current_zone, latitude, longitude,
                    self.state_this_poll.get(devicename))
        self._LOGGER_debug_msg(log_msg)

        return current_zone.lower()
    '''
#--------------------------------------------------------------------
    @staticmethod
    def _get_zone_names(zone_name):
        """
        Make zone_names 1, 2, & 3 out of the zone_name value for sensors

        name1 = home --> Home
                not_home --> Away
                gary_iphone_stationary --> Stationary
        name2 = gary_iphone_stationary --> Gary Iphone Stationary
                office_bldg_1 --> Office Bldg 1
        name3 = gary_iphone_stationary --> GaryIphoneStationary
                office__bldg_1 --> Office Bldg1
        """
        if zone_name:
            if 'stationary' in zone_name:
                name1 = 'Stationary'
            elif 'not_home' in zone_name:
                name1 = 'Away'
            else:
                name1 = zone_name.title()

            if zone_name == 'zone':
                badge_value = name1

            name2 = zone_name.title().replace('_', ' ', 99)
            name3 = zone_name.title().replace('_', '', 99)
        else:
            name1 = 'not_set'
            name2 = 'Not Set'
            name3 = 'NotSet'

        return [zone_name, name1, name2, name3]

#--------------------------------------------------------------------
    @staticmethod
    def _stationary_zone_name(devicename):
        return "{}_stationary".format(devicename)
#--------------------------------------------------------------------
    def _inzone_and_over_1km_away(self, devicename, latitude, longitude):

        '''
        if inzone and > 1km away from zone and BackFetch, old location
        or gps accuracy error, then probably missed zone exit that should
        be processsed.
        '''
        if self._isnot_inzone(devicename):
            return False
        else:
            return (self._current_zone_distance(
                        devicename, latitude, longitude) > 1)

#--------------------------------------------------------------------
    def _current_zone_distance(self, devicename, latitude, longitude):
        '''
        Get the distance from current zone(state)
        '''

        zone_dist = 99999
        zone_name = self.state_this_poll.get(devicename)

        if self.zone_latitude.get(zone_name):
            if zone_name == 'stationary':
                zone_name = self._stationary_zone_name(devicename)

            zone_dist    =  self._calc_distance(
                            latitude, longitude,
                            self.zone_latitude.get(zone_name),
                            self.zone_longitude.get(zone_name))

            log_msg   = (
                    "INZONE 1KM CHECK {}, Zone={}, CurrGPS=({}, {}), "
                    "ZoneGPS=({}, {}), Dist={}").format(
                    devicename, zone_name, latitude, longitude,
                    self.zone_latitude.get(zone_name),
                    self.zone_longitude.get(zone_name), zone_dist)
            self._LOGGER_debug_msg(log_msg)

        return zone_dist

#--------------------------------------------------------------------
    def _is_inzone(self, devicename):
        return (self.state_this_poll.get(devicename) != 'not_home')

    def _isnot_inzone(self, devicename):
        return (self.state_this_poll.get(devicename) == 'not_home')

    def _was_inzone(self, devicename):
        return (self.state_last_poll.get(devicename) != 'not_home')

    def _wasnot_inzone(self, devicename):
        return (self.state_last_poll.get(devicename) == 'not_home')

    @staticmethod
    def _is_inzoneZ(current_zone):
        return (current_zone != 'not_home')


    @staticmethod
    def _isnot_inzoneZ(current_zone):
        #_LOGGER.warning("_isnot_inzoneZ = %s",(current_zone == 'not_home'))
        return (current_zone == 'not_home')
#--------------------------------------------------------------------
    def _wait_if_update_in_process(self, arg_devicename=None):
        #An update is in process, must wait until done
        wait_cnt = 0
        while self.update_in_process_flag:
            wait_cnt += 1
            if arg_devicename:
                attrs                = {}
                attrs[ATTR_INTERVAL] = ("►WAIT-{}").format(wait_cnt)

                self._update_device_sensors(devicename, attrs)

            time.sleep(2)

#--------------------------------------------------------------------
    def _update_stationary_zone(self, devicename,
                arg_latitude, arg_longitude, arg_passive):
        """ Create/update dynamic stationary zone """

        try:

            latitude  = round(arg_latitude, 6)
            longitude = round(arg_longitude, 6)
            zone_name = self._stationary_zone_name(devicename)
            passve_zone = (latitude == self.stat_zone_base_latitude and
                    longitude == self.stat_zone_base_longitude)

            attrs = {}
            attrs['hidden']        = False
            attrs[CONF_NAME]          = zone_name
            attrs[ATTR_FRIENDLY_NAME] = "Stationary"
            attrs[ATTR_RADIUS]     = self.stat_zone_radius_meters
            attrs['icon']          = "mdi:account"
            attrs[ATTR_LATITUDE]   = latitude
            attrs[ATTR_LONGITUDE]  = longitude
            attrs['passive']       = passve_zone

            self.zone_friendly_name[zone_name] = 'Stationary'
            self.zone_latitude[zone_name]      = latitude
            self.zone_longitude[zone_name]     = longitude
            self.zone_radius[zone_name]        = self.stat_zone_radius
            self.zone_passive[zone_name]       = arg_passive

            self.hass.states.set("zone." + zone_name, "zoning", attrs)

            self._trace_device_attributes(
                    zone_name, "CreateStatZone", "CreateStatZone", attrs)

            log_msg = (
                    "{}:{}({}) Created Stationary Zone, GPS=({}, {})").format(
                    self.friendly_name.get(devicename), self.base_zone,
                    self.device_type.get(devicename),
                    latitude, longitude)
            self._LOGGER_info_msg(log_msg)

            return True

        except Exception as err:
            log_msg = ("►►INTERNAL ERROR (UpdtStatZone-{})".format(err))
            self._LOGGER_error_msg(log_msg)

            return False
#--------------------------------------------------------------------
    def _update_device_sensors(self, devicename, attrs:dict):
        '''
        Update/Create sensor for the device attributes

        sensor_device_attrs = ['distance', 'calc_distance', 'waze_distance',
                          'travel_time', 'dir_of_travel', 'interval', 'info',
                          'last_located', 'last_update', 'next_update',
                          'poll_count', 'trigger', 'battery', 'battery_state',
                          'gps_accuracy', 'zone', 'last_zone', 'travel_distance']

        sensor_attrs_format = {'distance': 'dist', 'calc_distance': 'dist',
                          'travel_distance': 'dist', 'battery': '%',
                          'dir_of_travel': 'title'}
        '''
        try:
            if not attrs:
                return

            badge_value = None
            base_entity = self.sensor_base_entity.get(devicename)
            for attr_name in SENSOR_DEVICE_ATTRS:
                sensor_entity = "{}_{}".format(base_entity, attr_name)

                if attr_name in attrs:
                    value = attrs.get(attr_name)
                else:
                    continue

                sensor_attrs = {}
                if attr_name in SENSOR_ATTR_FORMAT:
                    format_type = SENSOR_ATTR_FORMAT.get(attr_name)
                    if format_type == "dist":
                        sensor_attrs['unit_of_measurement'] = \
                                self.unit_of_measurement
                        value = round(value, 2) if value else 0.00

                    elif format_type == "diststr":
                        if value and '.' in str(value):
                            value = round(value, 2)
                            sensor_attrs['unit_of_measurement'] = \
                                self.unit_of_measurement
                        else:
                            sensor_attrs['unit_of_measurement'] = ''
                    elif format_type == "%":
                        sensor_attrs['unit_of_measurment'] = '%'
                    elif format_type == 'title':
                        value = value.title().replace('_', ' ')
                    elif format_type == 'kph-mph':
                        sensor_attrs['unit_of_measurement'] = self.um_kph_mph
                    elif format_type == 'm-ft':
                        sensor_attrs['unit_of_measurement'] = self.um_m_ft

                if attr_name in SENSOR_ATTR_ICON:
                    sensor_attrs['icon'] = SENSOR_ATTR_ICON.get(attr_name)

                self._update_device_sensors_hass(base_entity, attr_name,
                                    value, sensor_attrs)

                if attr_name == 'zone':
                    zone_names = self._get_zone_names(value)
                    badge_value = zone_names[1]

                    self._update_device_sensors_hass(base_entity, "zone_name1",
                                    zone_names[1], sensor_attrs)
                    self._update_device_sensors_hass(base_entity, "zone_name2",
                                    zone_names[2], sensor_attrs)
                    self._update_device_sensors_hass(base_entity, "zone_name3",
                                    zone_names[3], sensor_attrs)

                elif attr_name == 'last_zone':
                    zone_names = self._get_zone_names(value)

                    self._update_device_sensors_hass(base_entity, "last_zone_name1",
                                    zone_names[1], sensor_attrs)
                    self._update_device_sensors_hass(base_entity, "last_zone_name2",
                                    zone_names[2], sensor_attrs)
                    self._update_device_sensors_hass(base_entity, "last_zone_name3",
                                    zone_names[3], sensor_attrs)

                elif attr_name == 'distance':
                    if value and float(value) > 0:
                        badge_value = "{} {}".format(
                                value, self.unit_of_measurement)

                elif attr_name == 'speed':
                    value_f = str(int(value)) + ", " + \
                              str(int(attrs.get(ATTR_SPEED_AVERAGE))) + ", " + \
                              str(int(attrs.get(ATTR_SPEED_HIGH)))

                    sensor_attrs = {}
                    sensor_attrs['icon'] = SENSOR_ATTR_ICON.get('speed')

                    self._update_device_sensors_hass(base_entity, "speed_summary",
                                    value_f, sensor_attrs)

            if badge_value:
                self._update_device_sensors_hass(base_entity, "badge",
                                    badge_value,
                                    self.sensor_badge_attrs.get(devicename))

                #log_msg=("Badge ={}, Value='{}' {}").format(
                #        badge_entity, badge_value,
                #        self.sensor_badge_attrs.get(devicename))
                #self._LOGGER_debug_msg(log_msg)
            return True

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = ("►►INTERNAL ERROR (UpdtSensorUpdate-{})".format(err))
            self._LOGGER_error_msg(log_msg)

            return False
#--------------------------------------------------------------------
    def _update_device_sensors_hass(self, base_entity, attr_name,
                                    value, sensor_attrs):

        if attr_name in self.sensors_custom_list:
            sensor_entity = "{}_{}".format(base_entity, attr_name)
            self.hass.states.set(sensor_entity, value, sensor_attrs)

            #log_msg=("Sensor={}, Value='{}'").format(sensor_entity, value)
            #self._LOGGER_debug_msg(log_msg)

#--------------------------------------------------------------------
    def _setup_info_attr(self, devicename, battery, \
                            gps_accuracy, dist_last_poll_moved, \
                            current_zone, location_isold_flag):

        """
        Initialize info attribute with battery information
        #Symbols = •▶¦▶ ●►◄▬▲▼◀▶ oPhone=►▶
        """

        try:
            info = ''
            if self.base_zone != 'home':
                info = '{} ●Base.Zone: {}'.format(info, self.base_zone_name)

            if not self.CURRENT_MODE_FMF:
                info = '{} ●Track.Method: {}'.format(info, self.mode_short_name)

            if self.overrideinterval_seconds.get(devicename) > 0:
                info = '{} ●Overriding.Interval'.format(info)

            if self.log_debug_msgs_flag:
                info = '{} ●Debug.log-on'.format(info)

            if gps_accuracy > int(self.gps_accuracy_threshold):
                info = '{} ●Poor.GPS.Accuracy-{}({})'.format(info, gps_accuracy,
                            self.poor_gps_accuracy_cnt.get(devicename))
                if (self._isnot_inzoneZ(current_zone) and \
                        self.ignore_gps_accuracy_inzone_flag):
                    info = '{}-Ignored'.format(info)

            if current_zone == 'near_zone':
                info = '{} ●NearZone'.format(info)

            if battery == 0:
                info = '{} ●Battery-Unknown'.format(info, battery)
            else:
                info = '{} ●Battery-{}%'.format(info, battery)

            isold_cnt = self.location_isold_cnt.get(devicename)
            if isold_cnt > 0:
                info = '{} ●Old.Location-{}'.format(info, isold_cnt)

            if self.location_isold_msg.get(devicename):
                info = '{} ●Old.Location'.format(info)

            if self.waze_data_copied_from.get(devicename) is not None:
                copied_from = self.waze_data_copied_from.get(devicename)
                if devicename != copied_from:
                    info = '{} ●Using Waze data from {}'.format(info,
                                self.friendly_name.get(copied_from))

        except Exception as err:
            log_msg = ("►►INTERNAL ERROR-RETRYING (SetInfoAttr-{})".format(\
                        err))
            self._LOGGER_error_msg(log_msg)
            info = log_msg

        return info

#--------------------------------------------------------------------
    def _update_poll_count_ignore_attribute(self, devicename, info = None):
        self.poll_count_ignore[devicename] += 1
        self.location_isold_cnt[devicename] += 1

        try:
            poll_count = "{}:{}:{}".format(
                self.poll_count_icloud.get(devicename),
                self.poll_count_iosapp.get(devicename),
                self.poll_count_ignore.get(devicename))

            attrs  = {}
            attrs[ATTR_POLL_COUNT] = poll_count

            if info:
                attrs[ATTR_INFO] = "●{}".format(info)

            self._update_device_sensors(devicename, attrs)

        except:
            pass
#--------------------------------------------------------------------
    def _format_poll_count(self, devicename):

        return "{}:{}:{}".format(
            self.poll_count_icloud.get(devicename),
            self.poll_count_iosapp.get(devicename),
            self.poll_count_ignore.get(devicename))

#########################################################
#
#   VARIABLE DEFINITION & INITIALIZATION FUNCTIONS
#
#########################################################
    def _setup_general_variables(self):
        self.device_attributes           = {}
        self.state_last_poll             = {}
        self.state_this_poll             = {}
        self.zone_last                   = {}
        self.zone_current                = {}
        self.zone_timestamp              = {}
        self.this_update_seconds         = 0
        self.update_timer                = {}
        self.overrideinterval_seconds    = {}
        self.interval_seconds            = {}
        self.interval_str                = {}
        self.last_tavel_time             = {}
        self.last_distance_str           = {}
        self.went_3km                    = {} #>3 km/mi, probably driving
        self.last_update_time            = {}
        self.last_update_seconds         = {}
        self.next_update_seconds         = {}
        self.next_update_time            = {}
        self.poll_count_iosapp           = {}
        self.poll_count_ignore           = {}
        self.poll_count_icloud           = {}
        self.data_source                 = {}
        self.location_isold_cnt          = {}    # override interval while < 4
        self.location_isold_msg          = {}
        self.event_cnt                   = {}
        self.event_log_table             = []
        self.event_log_base_attrs        = ''

        self.track_devicename_list        = ''
        self.immediate_retry_flag        = False
        self.time_zone_offset_seconds    = 0
        self.setinterval_cmd_devicename  = None

        self.iosapp_location_update_secs     = {}
        self.iosapp_location_update_cnt      = {}
        self.device_being_updated_flag       = {}
        self.device_being_updated_retry_cnt  = {}
        self.update_in_process_flag          = False
        self.dist_from_home_small_move_total = {}
        self.fmf_location_data               = {}
#--------------------------------------------------------------------

    def _setup_um_formats(self, unit_of_measurement):
        #Define variables, lists & tables
        if unit_of_measurement == 'mi':
            self.um_time_strfmt          = '%I:%M:%S'
            self.um_date_time_strfmt     = '%x, %I:%M:%S'
            self.um_km_mi_factor         = 0.62137
            self.um_m_ft                 = 'ft'
            self.um_kph_mph              = 'mph'
        else:
            self.um_time_strfmt          = '%H:%M:%S'
            self.um_date_time_strfmt     = '%x, %H:%M:%S'
            self.um_km_mi_factor         = 1
            self.um_m_ft                 = 'm'
            self.um_kph_mph              = 'kph'

#--------------------------------------------------------------------
    def _setup_tracking_method(self, mode):

        self.CURRENT_MODE_FMF    = (mode == MODE_FMF)
        self.CURRENT_MODE_FMPHN  = (mode == MODE_FMPHN or mode == MODE_ICLOUD)
        self.CURRENT_MODE_FMF_FMPHN = (mode in MODE_FMF_FMPHN)
        if (self.CURRENT_MODE_FMF_FMPHN and
                PYICLOUD_IC3_IMPORT_SUCCESSFUL == False):
           mode = MODE_IOSAPP1

        self.CURRENT_MODE_IOSAPP1 = (mode == MODE_IOSAPP1)
        self.CURRENT_MODE_IOSAPP2 = (mode == MODE_IOSAPP2)
        self.CURRENT_MODE_IOSAPP  = (mode in MODE_IOSAPP_V1_V2)

        self.mode_config = mode
        self.mode        = mode
        self.mode_name   = MODE_NAME.get(mode)
        self.mode_short_name = MODE_SHORT_NAME.get(mode)
        self.iosapp_version = 1


#--------------------------------------------------------------------
    def _setup_device_tracking_fields(self):
        self.fmf_id                  = {}
        self.fmf_devicename_email    = {}
        self.seen_this_device_flag   = {}
        self.device_tracker_entity   = {}
        self.device_tracker_entity_iosapp = {}
        self.iosapp_version1_flag    = {}
        self.devicename_iosapp       = {}

        this_update_time = dt_util.now().strftime('%H:%M:%S')
        self.authenticated_time       = \
                        dt_util.now().strftime(self.um_date_time_strfmt)

        self.tracked_devices          = {}
        self.device_type              = {}
        self.overrideinterval_seconds = {}
        self.tracking_device_flag     = {}
        self.trigger                  = {}  #device update trigger
        self.devicename_verified      = {}  #Set to True in mode setup fcts
        self.any_device_being_updated_flag = False
        self.friendly_name    = {}       #name made from status[CONF_NAME]
        self.friendly_picture = {}       #devicename picture from badge setup
        self.icloud_api_devices       = {} #icloud.api.devices obj
        self.tracked_devices_config_parm = {} #config file item for devicename

#--------------------------------------------------------------------
    def _setup_zone_tables(self):
        self.zone_friendly_name        = {}
        self.zone_latitude             = {}
        self.zone_longitude            = {}
        self.zone_radius               = {}
        self.zone_passive              = {}
        self.base_zone_sensor_prefix   = ""

        '''
        Get friendly name of all zones to set the device_tracker state
        '''
        zones = self.hass.states.entity_ids('zone')

        zone_names = []
        for zone in zones:
            zone_name  = zone.split(".")[1]      #zone='zone.'+zone_name
            zone_names.append(zone_name)
            zone_data  = self.hass.states.get(zone).attributes

            self.zone_friendly_name[zone_name] = zone_data[ATTR_FRIENDLY_NAME]
            self.zone_latitude[zone_name]      = zone_data[ATTR_LATITUDE]
            self.zone_longitude[zone_name]     = zone_data[ATTR_LONGITUDE]
            self.zone_radius[zone_name]    = round(zone_data[ATTR_RADIUS]/1000, 4)

            try:
                self.zone_passive[zone_name]   = zone_data['passive']
            except KeyError:
                self.zone_passive[zone_name]   = False

            self._trace_device_attributes(
                    zone_name, "LoadZoneTbl", "LoadZoneTbl", zone_data)

        #base.zone can be 'zonename' or 'zonename,secondary'. Get the zonename
        base_zone_items = self.base_zone_config.split(',')

        base_zone = base_zone_items[0].lower().strip()

        self.base_zone_sensor_prefix = ""
        if base_zone in zone_names:
            if len(base_zone_items) == 2:
                if base_zone_items[1].strip() != "noprefix":
                    self.base_zone_sensor_prefix = \
                                    slugify(base_zone_items[1].strip()) + "_"
            elif base_zone != 'home':
                self.base_zone_sensor_prefix = base_zone + "_"
        else:
            base_zone = 'home'
            log_msg = ("Ignoring invalid Base Zone for {}:{}").format(
                    self.group, self.username)
            self._LOGGER_error_msg(log_msg)
            log_msg = ("Found Base Zone {}, Valid zones are {}").format(
                    self.base_zone_config, zone_names)
            self._LOGGER_error_msg(log_msg)

        log_msg = ("Zone Name Table Initialized {}, Base Zone '{}'").format(
                        self.zone_friendly_name, base_zone)
        self._LOGGER_info_msg(log_msg)

        self.base_zone        = base_zone
        self.base_zone_name   = self.zone_friendly_name.get(base_zone)
        self.zone_home_lat    = self.zone_latitude.get(base_zone)
        self.zone_home_long   = self.zone_longitude.get(base_zone)
        self.zone_home_radius = float(self.zone_radius.get(base_zone))

        return

#--------------------------------------------------------------------
    def _setup_stationary_zone_variables(self, stationary_inzone_interval_str,
                    stationary_still_time_str):
        #create dynamic zone used by ios app when stationary
        self.stat_zone_inzone_interval = self._time_str_to_secs(
                stationary_inzone_interval_str)
        self.stat_zone_still_time      = self._time_str_to_secs(
                stationary_still_time_str)
        self.in_stationary_zone_flag   = {}
        self.stat_zone_moved_total     = {}  #Total of small distances
        self.stat_zone_timer = {}  #Time when distance set to 0
        self.stat_zone_base_latitude   = self.zone_home_lat
        self.stat_zone_base_longitude  = self.zone_home_long
        self.stat_zone_base_latitude   = 90
        self.stat_zone_base_longitude  = 180
        self.stat_min_dist_from_home   = round(self.zone_home_radius * 2.5, 2)
        self.stat_dist_move_limit      = round(self.zone_home_radius * 1.5, 2)
        self.stat_zone_radius          = round(self.zone_home_radius * 2, 2)
        self.stat_zone_radius_meters   = self.stat_zone_radius * 1000

        self.stat_zone_half_still_time = self.stat_zone_still_time / 2

#--------------------------------------------------------------------
    def _setup_polling_variables(self):
        #used to calculate distance traveled since last poll
        self.last_lat                  = {}
        self.last_long                 = {}
        self.waze_time                 = {}
        self.waze_dist                 = {}
        self.calc_dist                 = {}
        self.dist                      = {}

        self.state_change_flag         = {}
        self.iosapp_update_flag        = {}
        self.last_dev_timestamp        = {}
        self.poor_gps_accuracy_flag    = {}
        self.poor_gps_accuracy_cnt     = {}

        #used to calculate speed, high speed & average speed since zone exit
        self.time_last_poll_secs            = {}
        self.time_zone_exit_secs       = {}
        self.dist_moved_last_zone_exit = {}
        self.last_zone_dist_home       = {}
        self.speed                     = {}
        self.speed_high                = {}
        self.speed_average             = {}

#--------------------------------------------------------------------
    def _setup_sensor_variables(self):
        #Prepare sensors and base attributes
        self.sensor_devicenames       = []
        self.sensors_custom_list      = []
        self.sensor_badge_attrs       = {}
        self.sensor_base_entity       = {}
        self.sensor_prefix_name       = {}
        self.sensor_entity_iosapp     = {}
        self.sensor_base_entity['prefix'] = 'devicename'

#--------------------------------------------------------------------
    def _setup_waze_variables(self, waze_region, waze_min_distance,
                waze_max_distance, waze_realtime):
        #Keep distance data to be used by another device if nearby. Also keep
        #source of copied data so that device won't reclone from the device
        #using it.
        self.waze_region              = waze_region
        self.waze_min_distance        = self._mi_to_km(float(waze_min_distance))
        self.waze_max_distance        = self._mi_to_km(float(waze_max_distance))
        self.waze_max_dist_save       = self.waze_max_distance
        self.waze_realtime            = waze_realtime

        self.waze_distance_history    = {}
        self.waze_data_copied_from    = {}
        self.waze_history_data_used_flag = {}

        self.waze_manual_pause_flag = False    #If Paused vid iCloud command

        if self.distance_method_waze_flag:
            log_msg = ("Waze Settings: Region={}, Realtime={}, "
                  "MaxDistance={}, MinDistance={}").format(
                  self.waze_region, self.waze_realtime,
                  self.waze_max_distance, self.waze_min_distance)
            self._LOGGER_info_msg(log_msg)


#--------------------------------------------------------------------
    def _setup_debug_control(self):
        #string set using the update_icloud command to pass debug commands
        #into icloud3 to monitor operations or to set test variables
        #   gps - set gps acuracy to 234
        #   old - set isold_cnt to 4
        #   interval - toggle display of interval calulation method in info fld
        #   log - log 'debug' messages to the log file under the 'info' type
        self.debug_control        = ''
        self.log_debug_msgs_flag       = DEBUG_TRACE_CONTROL_FLAG
        self.log_debug_msgs_trace_flag = DEBUG_TRACE_CONTROL_FLAG
        if DEBUG_TRACE_CONTROL_FLAG:
            self.debug_control         = 'interval'

#--------------------------------------------------------------------
    def _initialize_device_fields(self, devicename):
        #Make domain name entity ids for the device_tracker and
        #sensors for each device so we don't have to do it all the
        #time. Then check to see if 'sensor.geocode_location'
        #exists. If it does, then using iosapp version 2.
        self.device_tracker_entity[devicename] = ('{}.{}').format(
                DOMAIN, devicename)
        self.device_tracker_entity_iosapp[devicename] = ('{}.{}').format(
                DOMAIN, self.devicename_iosapp.get(devicename))
        self.sensor_entity_iosapp[devicename] = ('sensor.{}').format(
                self.devicename_iosapp.get(devicename))

        #self._xxx_check_iosapp_version(devicename)

        self.state_this_poll[devicename]       = \
                self._get_current_state(devicename, IOSAPP_DT_ENTITY)

        self.state_last_poll[devicename]      = 'not_set'
        self.zone_last[devicename]            = ''
        self.zone_current[devicename]         = ''
        self.zone_timestamp[devicename]       = ''
        self.iosapp_update_flag[devicename]   = False
        self.state_change_flag[devicename]    = False
        self.last_dev_timestamp[self.group+devicename]   = ''
        self.trigger[devicename]              = ''

        self.iosapp_location_update_secs[devicename] = 0
        self.iosapp_location_update_cnt[devicename]  = 0
        self.device_being_updated_flag[devicename]   = False
        self.device_being_updated_retry_cnt[devicename] = 0
        self.seen_this_device_flag[devicename] = False
        self.went_3km[devicename]              = False

#--------------------------------------------------------------------
    def _initialize_times_counts_flags(self, devicename):
        #times, flags
        self.last_update_time[devicename]     = ZERO_HHMMSS
        self.last_update_seconds[devicename]  = 0
        self.next_update_time[devicename]     = ZERO_HHMMSS
        self.next_update_seconds[devicename]  = 0
        self.poll_count_iosapp[devicename]    = 0
        self.poll_count_icloud[devicename]    = 0
        self.poll_count_ignore[devicename]    = 0
        self.data_source[devicename]          = ''
        self.last_tavel_time[devicename]      = ''
        self.last_distance_str[devicename]    = ''
        self.event_cnt[devicename]            = 0

#--------------------------------------------------------------------
    def _initialize_intervals_distances_times(self, devicename):
        #interval, distances, times
        self.overrideinterval_seconds[devicename] = 0
        self.interval_seconds[devicename]    = 0
        self.interval_str[devicename]        = '0 sec'
        self.waze_time[devicename]           = 0
        self.waze_dist[devicename]           = 0
        self.calc_dist[devicename]           = 0
        self.dist[devicename]                = 0
        self.dist_from_home_small_move_total[devicename] = 0
        self.update_timer[devicename]        = time.time()
        self.waze_history_data_used_flag[devicename] = False

#--------------------------------------------------------------------
    def _initialize_location_speed_fields(self, devicename):
        #location, gps
        self.location_isold_cnt[devicename]   = 0
        self.location_isold_msg[devicename]   = False
        self.last_lat[devicename]             = self.zone_home_lat
        self.last_long[devicename]            = self.zone_home_long
        self.poor_gps_accuracy_flag[devicename] = False
        self.poor_gps_accuracy_cnt[devicename]  = 0

        #speed
        self.time_last_poll_secs[devicename]       = self._time_now_secs()
        self.time_zone_exit_secs[devicename]  = self._time_now_secs()
        self.last_zone_dist_home[devicename]  = 0
        self.dist_moved_last_zone_exit[devicename] = 0
        self.speed[devicename]                = 0
        self.speed_high[devicename]           = 0
        self.speed_average[devicename]        = 0

#--------------------------------------------------------------------
    def _initialize_attrs(self, devicename):
        attrs = {}
        attrs[ATTR_ZONE]               = 'not_set'
        attrs[ATTR_LAST_ZONE]          = 'not_set'
        attrs[ATTR_ZONE_TIMESTAMP]     = ''
        attrs[ATTR_INTERVAL]           = ''
        attrs[ATTR_WAZE_TIME]          = ''
        attrs[ATTR_ZONE_DISTANCE]      = 0
        attrs[ATTR_CALC_DISTANCE]      = 0
        attrs[ATTR_WAZE_DISTANCE]      = 0
        attrs[ATTR_LAST_LOCATED]       = ZERO_HHMMSS
        attrs[ATTR_LAST_UPDATE_TIME]   = ZERO_HHMMSS
        attrs[ATTR_NEXT_UPDATE_TIME]   = ZERO_HHMMSS
        attrs[ATTR_POLL_COUNT]         = '0:0:0'
        attrs[ATTR_DIR_OF_TRAVEL]      = ''
        attrs[ATTR_TRAVEL_DISTANCE]    = 0
        attrs[ATTR_INFO]               = ''
        attrs[ATTR_SPEED]              = 0
        attrs[ATTR_SPEED_HIGH]         = 0
        attrs[ATTR_SPEED_AVERAGE]      = 0
        attrs[ATTR_ALTITUDE]           = 0
        attrs[ATTR_BATTERY_STATUS]     = ''
        attrs[ATTR_DEVICE_STATUS]      = ''
        attrs[ATTR_LOW_POWER_MODE]     = ''
        attrs[ATTR_TRIGGER]            = ''
        attrs[ATTR_TIMESTAMP]          = dt_util.utcnow().isoformat()[0:23]
        attrs[ATTR_BASE_ZONE]          = self.base_zone_name
        attrs[CONF_GROUP]              = self.mode_short_name+"::"+\
                                         self.group
        #attrs[ATTR_TRACKING]           = self.track_devicename_list
        attrs[ATTR_TRACKING]           = ("{} ({}..{})").format(
                                          self.track_devicename_list,
                                          self.mode_short_name, self.group)

        attrs[ATTR_AUTHENTICATED]      = ''
        #attrs[ATTR_ALIAS]      = self.devicename_iosapp.get(devicename)
        attrs[ATTR_ICLOUD3_VERSION]    = VERSION
        attrs[ATTR_EVENT_LOG]          = ''

        return attrs

#########################################################
#
#   DEVICE SETUP SUPPORT FUNCTIONS FOR MODES FMF, ICLOUD, IOSPP, IOSAPP2
#
#########################################################
    def _setup_tracked_devices_fmf(self):
        '''
        Cycle thru the Find My Friends contact data. Extract the name, id &
        email address. Scan fmf_email config parameter to tie the fmf_id in
        the location record to the devicename.

                    email --> devicename <--fmf_id
        '''
        '''
        contact={
            'emails': ['gary678tw@', 'lillian123@gmail.com'],
            'firstName': 'Lillian',
            'lastName': '',
            'photoUrl': 'PHOTO;X-ABCROP-RECTANGLE=ABClipRect_1&64&42&1228&1228&
                    //mOVw+4cc3VJSJmspjUWg==;
                    VALUE=uri:https://p58-contacts.icloud.com:443/186297810/wbs/
                    0123efg8a51b906789fece
            'contactId': '8590AE02-7D39-42C1-A2E8-ACCFB9A5E406',60110127e5cb19d1daea',
            'phones': ['(772)\xa0321-3765'],
            'middleName': '',
            'id': 'ABC0DEFGH2NzE3'}

        cycle thru config>track_devices devicename/email parameter
        looking for a match with the fmf contact record emails item
                fmf_devicename_email:
                   'gary_iphone'       = 'gary678@gmail.com'
                   'gary678@gmail.com' = 'gary_iphone@'
             - or -
                   'gary_iphone'       = 'gary678@'
                   'gary678@'          = 'gary_iphone@gmail'

                emails:
                   ['gary456tw@', 'gary456@gmail.com]

        When complete, erase fmf_devicename_email and replace it with full
        email list
        '''
        try:
            fmf = self.api.friends

            #cydle thru al contacts in fmf recd
            devicename_contact_emails = {}

            contacts_valid_emails = ''
            log_msg=("Matching devicenames with FmF contact emails")
            self._LOGGER_info_msg(log_msg)

            for contact in fmf.contacts:

                contact_emails = contact.get('emails')

                id_contact = contact.get('id')

                #cycle thru the emails on the tracked_devices config parameter
                for parm_email in self.fmf_devicename_email:
                    if parm_email.find('@') == -1:
                        continue

                    #cycle thru the contacts emails
                    matched_friend = False
                    devicename = self.fmf_devicename_email.get(parm_email)

                    for contact_email in contact_emails:
                        if contacts_valid_emails.find(contact_email) == -1:
                            contacts_valid_emails += contact_email + ","

                        if contact_email.startswith(parm_email):
                            #update temp list with full email from contact recd
                            matched_friend = True
                            devicename_contact_emails[contact_email] = devicename
                            devicename_contact_emails[devicename]    = contact_email
                            #devicename_contact_emails[parm_email]   = devicename

                            self.fmf_id[id_contact] = devicename
                            self.fmf_id[devicename] = id_contact
                            self.devicename_verified[devicename] = True
                            self.friendly_name[devicename] = contact.get('firstName')

                            log_msg = ("Matched {} with FmF contact {}:{}").\
                                        format(devicename,
                                        contact.get('firstName'), contact_email)
                            self._LOGGER_info_msg(log_msg)
                            break

            for devicename in self.devicename_verified:
                if self.devicename_verified.get(devicename) == False:
                    parm_email = self.fmf_devicename_email.get(devicename)
                    devicename_contact_emails[devicename] = parm_email
                    log_msg = ("Could not find friend with email {} in "
                               "{} FmF contacts list.").\
                                format(devicename, self.username)
                    self._LOGGER_warning_msg(log_msg)
                    log_msg = ("{} only has friends with emails: {}").format(
                               self.username,  contacts_valid_emails[:-1])
                    self._LOGGER_warning_msg(log_msg)
                    log_msg = ("Check iCloud acount for {} and make sure "
                               "the friend has been added to that account").\
                               format(self.username, parm_email,
                               contacts_valid_emails[:-1])
                    self._LOGGER_warning_msg(log_msg)

            self.fmf_devicename_email = {}
            self.fmf_devicename_email.update(devicename_contact_emails)

        except Exception as err:
            _LOGGER.exception(err)

#--------------------------------------------------------------------
    def _setup_tracked_devices_icloud(self):
        '''
        Scan the iCloud devices data. Select devices based on the
        include & exclude devices and device_type config parameters.

        Extract the friendly_name & device_type from the icloud data
        '''
        try:
            for device in self.api.devices:
                status      = device.status(DEVICE_STATUS_SET)
                location    = status['location']
                devicename  = slugify(
                        status[CONF_NAME].replace(' ', '', 99))
                device_type = status['deviceClass'].lower()

                if devicename in self.devicename_verified:
                    self.devicename_verified[devicename] = True

                    self.track_devicename_list = '{}, {}'.format(
                            self.track_devicename_list, devicename)

                    self.icloud_api_devices[devicename]  = device
                    self.device_type[devicename]      = device_type

                    event_msg = ("Tracking {}:{}").format(
                            self.group, devicename)
                    self._save_event("*", event_msg)

        except Exception as err:
            _LOGGER.exception(err)

            log_msg = ("iCloud3 Setup Aborted, Error authenticating "
                        "devices for {}").format(self.group)
            self._LOGGER_error_msg(log_msg)

#--------------------------------------------------------------------
    def _setup_tracked_devices_iosapp(self):
        '''
        The devices to be tracked are in the track_devices or the
        include_devices  config parameters.
        '''
        for devicename in self.devicename_verified:
            self.devicename_verified[devicename] = True

        return
 #--------------------------------------------------------------------
    def _setup_tracked_devices(self, config_parameter):
        '''
        Set up the devices to be tracked and it's associated information
        for the configuration line entry. This will fill in the followint
        fields based on the extracted deviename:
            device_type
            friendly_name
            fmf email address
            sensor.picture name
            device tracking flags
            tracked_devices list
        These fields may be overridden by the routines associated with the
        operating mode (fmf, icloud, iosapp)
        '''
        if config_parameter is None:
            return

        for devicename_line in config_parameter:
            di = self._setup_tracked_device_parameters(devicename_line)

            if di is None:
                return

            devicename = di[DI_DEVICENAME]

            if di[DI_EMAIL]:
                email = di[DI_EMAIL]
                self.fmf_devicename_email[email]      = devicename
                self.fmf_devicename_email[devicename] = email
            if di[DI_DEVICE_TYPE]:
                self.device_type[devicename]        = di[DI_DEVICE_TYPE]
            if di[DI_FRIENDLY_NAME]:
                self.friendly_name[devicename]      = di[DI_FRIENDLY_NAME]
            if di[DI_PICTURE]:
                self.friendly_picture[devicename]   = di[DI_PICTURE]
            if di[DI_SENSOR_PREFIX_NAME]:
                self.sensor_prefix_name[devicename] = di[DI_SENSOR_PREFIX_NAME]
            self.devicename_verified[devicename] = False

#--------------------------------------------------------------------
    def _setup_tracked_device_parameters(self, config_parameter):
        '''
        This will decode the device's parameter in the configuration file for
        the include_devices, sensor_name_prefix, track_devices items in the
        format of:
           - devicename > email, picture, reserved, sensornameprefix

        If the item cotains '@', it is an email item,
        If the item contains .png  or .jpg, it is a picture item.
        Otherwise, it is the prefix name item for sensors

        The device_type and friendly names are also returned in the
        following order as a list item:
            devicename, device_type, friendlyname, email, picture, sensor name
        '''
        try:
            email    = None
            picture  = None
            name     = None
            reserved = None
            device_type = None

            devicename_parameters = config_parameter.lower().split('>')
            devicename  = slugify(devicename_parameters[0].replace(' ', '', 99))

            self.tracked_devices_config_parm[devicename] = config_parameter

            if len(devicename_parameters) > 1:
                parameters = devicename_parameters[1].strip()
                parameters = parameters + ',,,,,,'

                #if no email address (no '@') and no ',' (only 1 item),
                #see if it a picture. If so, add an '@' to split correctly.
                if (parameters.find('@') == -1 and parameters.find(',') == -1):
                    if (parameters.find('.png') > 0 or parameters.find('.jpg') > 0):
                        parameters = ',' + parameters

                item = parameters.split(',')

                email = item[0].strip()
                if email != '' and email.find("@") == -1:
                    email += '@'

                picture = item[1].strip()
                if (picture != '' and picture.find(".png") == -1 and
                        picture.find(".jpg") == -1):
                    log_msg=(("Invalid picture name for {}, found "
                            "<{}>, should have '.png' or '.jpg'. Picture name "
                            "discarded.").format(devicename, picture))
                    self._LOGGER_warning_msg(log_msg)
                    picture = ''
                if picture.find('/') == -1:
                    picture = '/local/' + picture

                reserved    = item[2].strip()
                prefix_name = item[3].strip()

                if reserved != "" and prefix_name == "":
                    log_msg = ("Config 'tracking_devices' parameter error "
                            "corrected. 'Reserved' field (#3) being used for "
                            "'sensor_prefix_name'")
                    self._LOGGER_warning_msg(log_msg)
                    log_msg = ("Found  : {}").format(config_parameter)
                    self._LOGGER_warning_msg(log_msg)
                    temp = config_parameter.replace(reserved, ','+reserved)
                    temp = temp.replace(', ,', ',, ')
                    log_msg = ("Correct: {}").format(temp)
                    self._LOGGER_warning_msg(log_msg)
                    prefix_name = reserved
                    reservec = ""

            fname = devicename
            for dev_type in APPLE_DEVICE_TYPES:
                dev_type_pos = devicename.find(dev_type)
                if dev_type_pos > 0:
                    fnamew = devicename.replace(dev_type, "", 99)
                    fname  = fnamew.replace("_", "", 99)
                    fname  = fname.replace("-", "", 99).title()
                    device_type  = dev_type
                    break
        except Exception as err:
            _LOGGER.exception(err)

        device_info = [devicename, device_type, fname,
                       email, picture, reserved, prefix_name]

        return device_info

#--------------------------------------------------------------------
    def _check_depreciated_config_parms(self):
        '''
        Display warning messages about depreciated config parameters
        to include:
            - include_device(s)
            - include_device_type(s)
            - exclude_device(s)
            - exclude_device_type(s)
            - sensor_name_prefix
            - sensor_badge_picture
        '''
        try:
            if (self.include_devices      == [] and
                self.include_device_types == [] and
                self.exclude_devices      == [] and
                self.exclude_device_types == [] and
                self.filter_devices       == [] and
                self.sensor_name_prefix   == [] and
                self.sensor_badge_picture == []):
                return

            log_msg = ("iCloud3 Error: Depreciated config parameters are being "
                       "used to select devices to be tracked. Use the "
                      "'track_devices' parameter instead.")
            if self.track_devices == []:
                self._LOGGER_error_msg(log_msg)
            else:
                self._LOGGER_warning_msg(log_msg)
            log_msg = ("Config Parameters")

            if self.include_device != []:
                log_msg += (", include_device={}".format(
                                        self.include_device))
            if self.include_devices != []:
                log_msg += (", include_devices={}".format(
                                        self.include_devices))
            if self.exclude_device != []:
                log_msg += (", exclude_device={}".format(
                                        self.exclude_device))
            if self.exclude_devices != []:
                log_msg += (", exclude_devices={}".format(
                                        self.exclude_devices))
            if self.include_device_type != []:
                log_msg += (", include_device_type={}".format(
                                        self.include_device_type))
            if self.include_device_types != []:
                log_msg += (", include_device_types={}".format(
                                        self.include_device_types))
            if self.exclude_device_type != []:
                log_msg += (", exclude_device_type={}".format(
                                        self.exclude_device_type))
            if self.exclude_device_types != []:
                log_msg += (", exclude_device_types={}".format(
                                        self.exclude_device_types))
            if self.sensor_name_prefix != []:
                log_msg += (", sensor_name_prefix={}".format(
                                        self.sensor_name_prefix))
            if self.sensor_badge_picture != []:
                log_msg += (", sensor_badge_picture={}".format(
                                        self.sensor_badge_picture))
            if self.filter_devices != []:
                log_msg += (", filter_devices={}".format(
                                        self.filter_devices))
            if self.track_devices == []:
                self._LOGGER_error_msg(log_msg)
            else:
                self._LOGGER_warning_msg(log_msg)

        except Exception as err:
            _LOGGER.exception(err)


#########################################################
#
#   DEVICE SENSOR SETUP ROUTINES
#
#########################################################
    def _setup_sensor_base_attrs(self):
        '''
        The sensor name prefix can be the devicename or a name specified on
        the track_device configuration parameter        '''

        for devicename in self.tracked_devices:
            if self.sensor_prefix_name.get(devicename) is None:
                prefix_name = devicename
            elif self.sensor_prefix_name.get(devicename) != '':
                prefix_name = self.sensor_prefix_name.get(devicename)
            else:
                prefix_name = devicename

            self.sensor_base_entity[devicename] = 'sensor.{}{}'.format(
                        self.base_zone_sensor_prefix, prefix_name)

            badge_attrs = {}
            badge_attrs['entity_picture'] = \
                    self.friendly_picture.get(devicename)
            badge_attrs['friendly_name'] = self.friendly_name.get(devicename)
            badge_attrs['icon']   = SENSOR_ATTR_ICON.get('badge')
            self.sensor_badge_attrs[devicename] = badge_attrs

            log_msg = ("Set up sensor name for device, devicename={}, "
                        "entity_base={}").format(devicename,
                        self.sensor_base_entity.get(devicename))
            self._LOGGER_debug_msg(log_msg)

        return

#--------------------------------------------------------------------
    def _setup_sensors_custom_list(self):
        '''
        This will process the 'sensors' and 'exclude_sensors' config
        parameters if 'sensors' exists, only those sensors wil be displayed.
        if 'exclude_sensors' eists, those sensors will not be displayed.
        'sensors' takes ppresidence over 'exclude_sensors'.
        '''

        if self.sensor_ids != []:
            self.sensors_custom_list = []
            for sensor_id in self.sensor_ids:
                id = sensor_id.lower().strip()
                if id in SENSOR_ID_NAME_LIST:
                    self.sensors_custom_list.append(SENSOR_ID_NAME_LIST.get(id))

        elif self.exclude_sensor_ids != []:
            self.sensors_custom_list.extend(SENSOR_DEVICE_ATTRS)
            for sensor_id in self.exclude_sensor_ids:
                id = sensor_id.lower().strip()
                if id in SENSOR_ID_NAME_LIST:
                    if SENSOR_ID_NAME_LIST.get(id) in self.sensors_custom_list:
                        self.sensors_custom_list.remove(SENSOR_ID_NAME_LIST.get(id))
        else:
            self.sensors_custom_list.extend(SENSOR_DEVICE_ATTRS)

#--------------------------------------------------------------------
    def _xxx_check_iosapp_version(self, devicename):
        '''
        The devices might be running Version 1 or 2 of the iosapp. Check
        each device to see how the tracking data should be retrieved for
        that device.
        '''

        try:
            self.iosapp_version1_flag[devicename] = True

            entity_id = ("{}_{}").format(
                self.sensor_entity_iosapp.get(devicename), "geocode_location")

            device_state = self.hass.states.get(entity_id)

            self.iosapp_version1_flag[devicename] = False

        except AttributeError as err:
            _LOGGER.exception(err)
            log_msg = ('AttrError: Device {}, No Sensor-{}').format(
                        devicename, entity_id)
            self._LOGGER_error_msg(log_msg)
            pass

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = ('OtherError: Device {}, No Sensor-{}').format(
                        devicename, entity_id)
            self._LOGGER_error_msg(log_msg)
            pass

        return


#########################################################
#
#   DEVICE STATUS SUPPORT FUNCTIONS FOR GPS ACCURACY, OLD LOC DATA, ETC
#
#########################################################

    def _check_isold_status(self, devicename, arg_location_isold_flag,
                            loc_timestamp, loc_attr_timestamp):
        """
        Check if the location isold flag is set by the iCloud service or if
        the current timestamp is the same as the timestamp on the previous
        poll. If so, we want to retry locating device
        5 times and then use normal interval. But keep track of count for
        determining the interval.
        """

        try:
            isold_cnt = 0
            location_isold_flag = arg_location_isold_flag

            if 'old' in self.debug_control:
                location_isold_flag = True   #debug

            #Set isold flag if timestamp is more than 2 minutes old
            age = int(self._secs_since(loc_attr_timestamp))
            age_str = self._secs_to_time_str(age)
            location_isold_flag = (age > 120)

            if location_isold_flag:
                self.location_isold_cnt[devicename] += 1
                self.poll_count_ignore[devicename] += 1
            else:
                self.location_isold_cnt[devicename] = 0
            log_msg = ("►► CHECK ISOLD, Timestamp={}, isOldFlag={}, Age={}").\
                    format(loc_timestamp, arg_location_isold_flag, age_str)
            self._LOGGER_debug_msg(log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            location_isold_flag = False

            log_msg = ("►► INTERNAL ERROR (ChkOldLoc)")
            self._LOGGER_error_msg(log_msg)

        return location_isold_flag
#--------------------------------------------------------------------
    def _check_poor_gps(self, devicename, gps_accuracy):
        if 'gps' in self.debug_control:
            gps_accuracy = 234 #debug

        if gps_accuracy > self.gps_accuracy_threshold:
            event_msg = "Poor GPS accuracy ({})".format(gps_accuracy)
            self._save_event(devicename, event_msg)
            self.poor_gps_accuracy_flag[devicename] = True
            self.poor_gps_accuracy_cnt[devicename] += 1
        else:
            self.poor_gps_accuracy_flag[devicename] = False
            self.poor_gps_accuracy_cnt[devicename]  = 0

#--------------------------------------------------------------------
    def _check_use_iosapp_trigger(self, devicename, trigger, dev_timestamp):
        '''
        The trigger transaction has already updated the lat/long so
        you don't want to discard the record just because it is old.
        If in a zone, use the trigger but check the distance from the
        zone when updating the device. If the distance from the zone = 0,
        then reset the lat/long to the center of the zone.
        '''

        dev_timestamp_secs = self._timestamp_to_secs_dev(dev_timestamp)
        age                = self._secs_since(dev_timestamp_secs)
        age_str            = self._secs_to_time_str(age)
        use_iosapp_trigger = self._is_inzone(
                    self.state_last_poll.get(devicename))

        #Discard trigger item if more than 2 minutes old,
        if age > 120:
            use_iosapp_trigger = False
            self._update_poll_count_ignore_attribute(devicename)
            event_msg = "Location discarded, Old data, Age {}".format(age_str)
            self._save_event(devicename, event_msg)
            log_msg = ("{}:{}({}) Discarded, IOS data too old, Trigger={}, "
                "TimestampTime={}, Age={}").format(
                self.friendly_name.get(devicename), self.base_zone,
                self.device_type.get(devicename),
                trigger, self._timestamp_to_time_dev(dev_timestamp, True),
                age_str)
            self._LOGGER_info_msg(log_msg)

        return use_iosapp_trigger

#--------------------------------------------------------------------
    def _log_device_status_attrubutes(self, status):

        """
        Status={'batteryLevel': 1.0, 'deviceDisplayName': 'iPhone X',
        'deviceStatus': '200', CONF_NAME: 'Gary-iPhone',
        'deviceModel': 'iphoneX-1-2-0', 'rawDeviceModel': 'iPhone10,6',
        'deviceClass': 'iPhone',
        'id':'qyXlfsz1BIOGxcqDxDleX63Mr63NqBxvJcajuZT3y05RyahM3/OMpuHYVN
        SUzmWV', 'lowPowerMode': False, 'batteryStatus': 'NotCharging',
        'fmlyShare': False, 'location': {'isOld': False,
        'isInaccurate': False, 'altitude': 0.0, 'positionType': 'GPS'
        'latitude': 27.726843548976, 'floorLevel': 0,
        'horizontalAccuracy': 48.00000000000001,
        'locationType': '', 'timeStamp': 1539662398966,
        'locationFinished': False, 'verticalAccuracy': 0.0,
        'longitude': -80.39036092533418}, 'locationCapable': True,
        'locationEnabled': True, 'isLocating': True, 'remoteLock': None,
        'activationLocked': True, 'lockedTimestamp': None,
        'lostModeCapable': True, 'lostModeEnabled': False,
        'locFoundEnabled': False, 'lostDevice': None,
        'lostTimestamp': '', 'remoteWipe': None,
        'wipeInProgress': False, 'wipedTimestamp': None, 'isMac': False}
        """

        log_msg = ("►►ICLOUD DATA, DEVICE ID={}, ▶deviceDisplayName={}").format(
                status, status['deviceDisplayName'])
        self._LOGGER_debug_msg(log_msg)

        location = status['location']

        log_msg = ("►►ICLOUD DEVICE STATUS/LOCATION, ●deviceDisplayName={}, "
                "●deviceStatus={}, ●name={}, ●deviceClass={}, "
                "●batteryLevel={}, ●batteryStatus={}, "
                "●isOld={}, ●positionType={}, ●latitude={}, ●longitude={}, "
                "●horizontalAccuracy={}, ●timeStamp={}({})").format(
                status['deviceDisplayName'], status['deviceStatus'],
                status[CONF_NAME], status['deviceClass'],
                status['batteryLevel'], status['batteryStatus'],
                location[ATTR_ISOLD], location['positionType'],
                location[ATTR_LATITUDE], location[ATTR_LONGITUDE],
                location['horizontalAccuracy'], location[ATTR_LOC_TIMESTAMP],
                self._timestamp_to_time(location[ATTR_LOC_TIMESTAMP]))
        self._LOGGER_debug_msg(log_msg)
        return True

#--------------------------------------------------------------------

#########################################################
#
#   EVENT LOG ROUTINES
#
#########################################################
    def _setup_event_log(self):
        '''
        Set up the name, picture and devicename attributes in the Event Log
        sensor. Read the sensor attributes first to see if it was set up by
        another instance of iCloud3 for a different iCloud acount.
        '''
        name_attrs       = {}
        pict_attrs       = {}
        devicename_attrs = {}

        try:
            attrs = self.hass.states.get(SENSOR_EVENT_LOG_ENTITY).attributes

            if attrs and 'names' in attrs:
                name_attrs = attrs.get("names")
            if attrs and 'pictures' in attrs:
                pict_attrs = attrs.get("pictures")
            if attrs and 'devicenames' in attrs:
                devicename_attrs = attrs.get("devicenames")

            #_LOGGER.error("Get attrs>>%s",attrs)
            #_LOGGER.error("Get attrs(name)>>%s",attrs.get("name"))
            #_LOGGER.error("Get name_attrs>>%s",name_attrs)
            #_LOGGER.error("Get name_attrs(name)>>%s",name_attrs.get("name"))

            #_LOGGER.error("Get attrs(picture)>>%s",attrs.get("picture"))
            #_LOGGER.error("Get pict_attrs(picture>>%s",pict_attrs.get("picture"))
            #_LOGGER.error("Get pict_attrs>>%s",pict_attrs)
            #_LOGGER.error("Get pict_attrs(pict)>>%s",pict_attrs.get("picture"))

        except (KeyError, AttributeError):
            pass
        except Exception as err:
            _LOGGER.exception(err)

        for devicename in self.tracked_devices:
            #_LOGGER.warning("Creating log - %s-%s",self.group,devicename)
            name_attrs[devicename] = self.friendly_name.get(devicename)
            pict_attrs[devicename] = self.friendly_picture.get(devicename)
            devicename_attrs[devicename] = devicename

            #_LOGGER.error("New name_attrs>>%s",name_attrs)
            #_LOGGER.error("New pict_attrs>>%s",pict_attrs)

        base_attrs = {}
        base_attrs["names"]       = name_attrs
        base_attrs["pictures"]    = pict_attrs
        base_attrs["devicenames"] = devicename_attrs
        base_attrs["logs"]        = ""

        self.hass.states.set(SENSOR_EVENT_LOG_ENTITY, "Initialized", base_attrs)
        self.event_log_base_attrs = base_attrs

        return

#------------------------------------------------------
    def _save_event(self, devicename, log_text):

        try:
            this_update_time = dt_util.now().strftime('%H:%M:%S')

            if devicename == '' or devicename == 'Initializing':
                friendly_name = '*'
            else:
                #friendly_name = self.friendly_name.get(devicename)
                state       = self.state_this_poll.get(devicename)
                zone_names  = self._get_zone_names(
                            self.zone_current.get(devicename))
                zone        = zone_names[1]
                distance    = self.last_distance_str.get(devicename)
                travel_time = self.last_tavel_time.get(devicename)
                interval    = self.interval_str.get(devicename)

            if state is None:
                state = ''
            if zone is None:
                zone = ''
            if distance is None:
                distance = ''
            if travel_time is None:
              travel_time = ''
            if interval is None:
              interval = ''
            if devicename is None:
              devicename = '*'

            log_text = log_text.replace('"', '-', 99)
            log_text = log_text.replace("'", "-", 99)

            event_recd = [devicename, this_update_time,
                            state, zone, distance, travel_time,
                            interval, log_text]

            if self.event_log_table is None:
                self.event_log_table = []

            while len(self.event_log_table) > 999:
                self.event_log_table.pop(0)
            #_LOGGER.error ("event>>>%s",event_recd)
            self.event_log_table.append(event_recd)

        except Exception as err:
            _LOGGER.exception(err)

#------------------------------------------------------
    def _update_event_log_sensor_data(self, devicename = None):
        """Display the event log"""

        try:

            log_attrs  = self.event_log_base_attrs.copy()
            attr_recd  = {}
            attr_event = {}

            if devicename is None:
                return
            elif devicename == "*":
                log_attrs["filtername"] = "Initialize"
            else:
                log_attrs["filtername"] = \
                              self.friendly_name.get(devicename)
                self.event_cnt[devicename] += 1

            log_msg = ("Updating Event Log for {}").format(devicename)
            self._LOGGER_debug_msg(log_msg)

            attr_recd = self._setup_event_logs(devicename)

            log_attrs["logs"] = attr_recd

            log_update_time = ("{}, {}").format(
                    dt_util.now().strftime("%a, %m/%d"),
                    dt_util.now().strftime(self.um_time_strfmt))
            log_attrs["update_time"] = log_update_time

            #The state must change for the recds to be refressed on the
            #Lovelace card. If the state does not change, the new information
            #is not displayed. Add the update time to make it unique.

            sensor_state  = ("{};{}").format(devicename,  log_update_time)

            self.hass.states.set(SENSOR_EVENT_LOG_ENTITY,
                        sensor_state, log_attrs)

        except Exception as err:
            _LOGGER.exception(err)
#------------------------------------------------------
    def _setup_event_logs(self, devicename):
        """Build the event items attribute for  the event log sensor"""

        attr_recd  = []

        for event_recd in reversed(self.event_log_table):
            er_copy       = event_recd.copy()
            er_devicename = er_copy.pop(0)
            if (er_devicename == devicename or er_devicename == '*'):
                attr_recd.append(er_copy)

                #_LOGGER.info("---------------")
                #_LOGGER.info('%s',attr_recd)

        last_recd = ['00:00:00','','','','','','Last Record']
        attr_recd.append(last_recd)

        return str(attr_recd)
#########################################################
#
#   WAZE ROUTINES
#
#########################################################
    def _get_waze_data(self, devicename,
                            this_lat, this_long, last_lat,
                            last_long, current_zone, last_dist_from_home):

        try:
            if not self.distance_method_waze_flag:
                return ( WAZE_NOT_USED, 0, 0, 0)
            elif current_zone == self.base_zone:        #'home':
                return (WAZE_USED, 0, 0, 0)
            elif self.waze_status == WAZE_PAUSED:
                return (WAZE_PAUSED, 0, 0, 0)

            try:
                waze_from_home = self._get_waze_distance(devicename,
                        this_lat, this_long,
                        self.zone_home_lat, self.zone_home_long)

                waze_status = waze_from_home[0]
                if waze_status != WAZE_ERROR:
                    waze_from_last_poll = self._get_waze_distance(devicename,
                            last_lat, last_long, this_lat, this_long)
                else:
                    waze_from_last_poll = [WAZE_ERROR, 0, 0]

            except Exception as err:
                if err == "Name 'WazeRouteCalculator' is not defined":
                    self.distance_method_waze_flag = False
                    return (WAZE_NOT_USED, 0, 0, 0)

                return (WAZE_ERROR, 0, 0, 0)

            try:
                waze_dist_from_home = self._round_to_zero(waze_from_home[1])
                waze_time_from_home = self._round_to_zero(waze_from_home[2])
                waze_dist_last_poll = self._round_to_zero(waze_from_last_poll[1])

                if waze_dist_from_home == 0:
                    waze_time_from_home = 0
                else:
                    waze_time_from_home = self._round_to_zero(waze_from_home[2])

                if ((waze_dist_from_home > self.waze_max_distance) or
                     (waze_dist_from_home < self.waze_min_distance)):
                    waze_status = WAZE_OUT_OF_RANGE

            except Exception as err:
                log_msg = ("►►INTERNAL ERROR (ProcWazeData)-{})".format(err))
                self._LOGGER_error_msg(log_msg)

            log_msg = ("►►WAZE DISTANCES CALCULATED>, "
                  "Status={}, DistFromHome={}, TimeFromHome={}, "
                  " DistLastPoll={}, "
                  "WazeFromHome={}, WazeFromLastPoll={}").format(
                  waze_status, waze_dist_from_home, waze_time_from_home,
                  waze_dist_last_poll, waze_from_home, waze_from_last_poll)
            self._LOGGER_debug_msg(log_msg)

            return (waze_status, waze_dist_from_home, waze_time_from_home,
                    waze_dist_last_poll)

        except Exception as err:
            log_msg = ("►►INTERNAL ERROR (GetWazeData-{})".format(err))
            self._LOGGER_info_msg(log_msg)

            return (WAZE_ERROR, 0, 0, 0)

#--------------------------------------------------------------------
    def _get_waze_distance(self, devicename, from_lat, from_long, to_lat,
                        to_long):
        """
        Example output:
            Time 72.42 minutes, distance 121.33 km.
            (72.41666666666667, 121.325)

        See https://github.com/home-assistant/home-assistant/blob
        /master/homeassistant/components/sensor/waze_travel_time.py
        See https://github.com/kovacsbalu/WazeRouteCalculator
        """

        if not self.distance_method_waze_flag:
            return (WAZE_NOT_USED, 0, 0)

        try:
            from_loc = '{},{}'.format(from_lat, from_long)
            to_loc   = '{},{}'.format(to_lat, to_long)

            retry_cnt = 0
            while retry_cnt < 3:
                try:
                    route = WazeRouteCalculator.WazeRouteCalculator(
                            from_loc, to_loc, self.waze_region)

                    route_time, route_distance = \
                        route.calc_route_info(self.waze_realtime)

                    route_time     = round(route_time, 0)
                    route_distance = round(route_distance, 2)

                    return (WAZE_USED, route_distance, route_time)

                except WazeRouteCalculator.WRCError as err:
                    retry_cnt += 1
                    log_msg = ("Waze Server Error={}, Retrying (#{})").format(
                    err, retry_cnt)
                    self._LOGGER_info_msg(log_msg)

            return (WAZE_ERROR, 0, 0)

        except Exception as err:
            log_msg = ("►►INTERNAL ERROR (GetWazeDist-{})".format(err))
            self._LOGGER_info_msg(log_msg)

            return (WAZE_ERROR, 0, 0)
#--------------------------------------------------------------------
    def _get_waze_from_data_history(self, devicename,
                        curr_dist_from_home, this_lat, this_long):
        '''
        Before getting Waze data, look at all other devices to see
        if there are any really close. If so, don't call waze but use their
        distance & time instead if the data it it passes distance and age
        tests.

        The other device's distance from home and distance from last
        poll might not be the same as this devices current location
        but it should be close enough.

        last_waze_data is a list in the following format:
           [timestamp, latitudeWhenCalculated, longitudeWhenCalculated,
                [waze_dist_time_info]]
        '''

        if not self.distance_method_waze_flag:
            return None
        elif self.waze_status == WAZE_PAUSED:
            return None

        #Calculate how far the old data can be from the new data before the
        #data will be refreshed.
        test_distance = curr_dist_from_home * .05
        if test_distance > 5:
            test_distance = 5

        try:
            for near_devicename in self.waze_distance_history:
                self.waze_history_data_used_flag[devicename] = False
                waze_data_other_device = self.waze_distance_history.get(
                                                        near_devicename)
                #This device doesn't have any Waze data saved.
                if len(waze_data_other_device) == 0:
                    continue
                if len(waze_data_other_device[3]) == 0:
                    continue

                waze_data_timestamp = waze_data_other_device[0]
                waze_data_latitude  = waze_data_other_device[1]
                waze_data_longitude = waze_data_other_device[2]

                dist_from_other_waze_data = self._calc_distance(
                            this_lat, this_long,
                            waze_data_latitude, waze_data_longitude)

                #Get distance from current location and Waze data
                #If close enough, use it regardless of whose it is
                if dist_from_other_waze_data < test_distance:
                    event_msg = ("Waze history data used, "
                        "{} from current location").format(
                        dist_from_other_waze_data)
                    self._save_event(devicename, event_msg)

                    self.waze_data_copied_from[devicename] = near_devicename
                    log_msg=("{}:{}({}) using Waze history data from {}({}); "
                            "Distance from home {} km, travel time {} min, "
                            "distance moved {} km").format(
                            self.friendly_name.get(devicename), self.base_zone,
                            self.device_type.get(devicename),
                            self.friendly_name.get(near_devicename),
                            self.device_type.get(near_devicename),
                            waze_data_other_device[3][2],
                            waze_data_other_device[3][1],
                            waze_data_other_device[3][3])
                    self._LOGGER_info_msg(log_msg)

                    #Return Waze data (Status, distance, time, dist_moved)
                    self.waze_history_data_used_flag[devicename] = True
                    return waze_data_other_device[3]

        except Exception as err:
            _LOGGER.exception(err)
        return None
        '''
        Code I don't want to delete yet!!!!

        #Don't check against myself or another device that was
        #copied from me
        if (devicename == near_devicename):
            continue

        elif (devicename == self.waze_data_copied_from.get(
                    near_devicename)):
            log_msg=("Not copying Waze data, {} was copied from {}").\
                    format(near_devicename, devicename)
            self._LOGGER_debug_msg(log_msg)
            continue

        dist_from_other_device = self._calc_distance(
                    this_lat, this_long,
                    self.last_lat.get(near_devicename),
                    self.last_long.get(near_devicename))

        #Don't use if devices are far apart
        if dist_from_other_device > .05:
            continue

        waze_data_timestamp = waze_data_other_device[0]
        waze_data_latitude  = waze_data_other_device[1]
        waze_data_longitude = waze_data_other_device[2]

        #Don't use if waze data is more than X minutes old
        age = round(abs(self._secs_since(waze_data_timestamp)) / 60, 2)
        if age > test_age:
            continue
        '''


#--------------------------------------------------------------------
    def _format_waze_time_msg(self, devicename, waze_time_from_home,
                                waze_dist_from_home):
        '''
        Return the message displayed in the waze time field ►►
        '''

        #Display time to the nearest minute if more than 3 min away
        if self.waze_status == WAZE_USED:
            t = waze_time_from_home * 60
            r = 0
            if t > 180:
                t, r = divmod(t, 60)
                t = t + 1 if r > 30 else t
                t = t * 60

            waze_time_msg = self._secs_to_time_str(t)

        else:
            waze_time_msg = ''

        return waze_time_msg
#--------------------------------------------------------------------
    def _verify_waze_installation(self):
        '''
        Report on Waze Route alculator service availability
        '''

        self._LOGGER_info_msg("Verifying Waze Route Service component")

        if (WAZE_IMPORT_SUCCESSFUL == 'YES' and
                    self.distance_method_waze_flag):
            self.waze_status = WAZE_USED
        else:
            self.waze_status = WAZE_NOT_USED
            self.distance_method_waze_flag = False
            self._LOGGER_info_msg("Waze Route Service not available")


#########################################################
#
#   _LOGGER MESSAGE ROUTINES
#
#########################################################
    @staticmethod
    def _LOGGER_info_msg(msg):
        _LOGGER.info(msg)

    @staticmethod
    def _LOGGER_warning_msg(msg):
        _LOGGER.warning(msg)

    @staticmethod
    def _LOGGER_error_msg(msg):
        _LOGGER.error(msg)

    def _LOGGER_debug_msg(self, msg):
        if (self.log_debug_msgs_flag or self.log_debug_msgs_trace_flag):
            _LOGGER.info(msg)
        else:
            _LOGGER.debug(msg)

    def _LOGGER_debug_msg2(self, msg):
            _LOGGER.debug(msg)

    @staticmethod
    def _internal_error_msg(function_name, err_text: str='',
                section_name: str=''):
        log_msg = ("►►INTERNAL ERROR-RETRYING ({}:{}-{})".format(
                function_name, section_name, err_text))
        _LOGGER.error(log_msg)

        attrs = {}
        attrs[ATTR_INTERVAL]           = '0 sec'
        attrs[ATTR_NEXT_UPDATE_TIME]   = ZERO_HHMMSS
        attrs[ATTR_INFO]               = log_msg

        return attrs

#########################################################
#
#   TIME & DISTANCE UTILITY ROUTINES
#
#########################################################
    @staticmethod
    def _time_now_secs():
        ''' Return the epoch seconds in utc time '''

        return int(time.time())
 #--------------------------------------------------------------------
    def _secs_to_time(self, e_seconds):
        """ Convert seconds to hh:mm:ss """

        t_struct = time.localtime(e_seconds + self.e_seconds_local_offset_secs)
        return  time.strftime(self.um_time_strfmt, t_struct)

#--------------------------------------------------------------------
    @staticmethod
    def _secs_to_time_str(time_sec):
        """ Create the time string from seconds """
        if time_sec < 60:
            time_str = str(time_sec) + " sec"
        elif time_sec < 3600:
            time_str = str(round(time_sec/60, 1)) + " min"
        elif time_sec == 3600:
            time_str = "1 hr"
        else:
            time_str = str(round(time_sec/3600, 1)) + " hrs"

        # xx.0 min/hr --> xx min/hr
        time_str = time_str.replace('.0 ', ' ')
        return time_str
#--------------------------------------------------------------------
    def _secs_since(self, e_seconds):
        return self.this_update_seconds - e_seconds
#--------------------------------------------------------------------
    def _secs_to(self, e_seconds):
        return e_seconds - self.this_update_seconds
#--------------------------------------------------------------------
    @staticmethod
    def _time_to_secs(hhmmss):
        """ Convert hh:mm:ss into seconds """
        if hhmmss:
            s = hhmmss.split(":")
            tts_seconds = int(s[0]) * 3600 + int(s[1]) * 60 + int(s[2])
        else:
            tts_seconds = 0

        return tts_seconds

#--------------------------------------------------------------------
    @staticmethod
    def _time_str_to_secs(time_str='30 min'):
        """
        Calculate the seconds in the time string.
        The time attribute is in the form of '15 sec' ',
        '2 min', '60 min', etc
        """

        s1 = str(time_str).replace('_', ' ') + " min"
        time_part = float((s1.split(" ")[0]))
        text_part = s1.split(" ")[1]

        if text_part == 'sec':
            time_sec = time_part
        elif text_part == 'min':
            time_sec = time_part * 60
        elif text_part == 'hrs':
            time_sec = time_part * 3600
        elif text_part in ('hr', 'hrs'):
            time_sec = time_part * 3600
        else:
            time_sec = 1200      #default to 20 minutes

        return time_sec

#--------------------------------------------------------------------
    def _timestamp_to_time(self, utc_timestamp):
        """
        Convert iCloud timeStamp into the local time zone and
        return hh:mm:ss
        """

        ts_local = int(float(utc_timestamp)/1000) + \
                self.time_zone_offset_seconds

        ts_str = dt_util.utc_from_timestamp(
                ts_local).strftime(self.um_time_strfmt)
        if ts_str[0] == "0":
            ts_str = ts_str[1:]

        return ts_str

#--------------------------------------------------------------------
    def _timestamp_age_secs(self, timestamp):
        """
        Return the age of the device timestamp attribute (sec)
        Format is --'timestamp': '2019-02-02T12:12:38.358-0500'
        """

        time_now_secs  = self.this_update_seconds
        timestamp_secs = self._timestamp_to_secs_dev(timestamp)
        if timestamp_secs == 0:
            return 0

        return (time_now_secs - timestamp_secs)
#--------------------------------------------------------------------
    def _timestamp_to_time_dev(self, timestamp, time_24h = False):
        """
        Extract the time from the device timeStamp attribute
        updated by the IOS app.
        Format is --'timestamp': '2019-02-02T12:12:38.358-0500'
        Return as a 24hour time if time_24h = True
        """

        try:
            dev_time_hhmmssddd  = '{}.'.format(timestamp.split('T')[1])
            dev_time_hhmmss     = dev_time_hhmmssddd.split('.')[0]

            if self.unit_of_measurement == 'mi' and time_24h == False:
                dev_time_hh = int(dev_time_hhmmss[0:2])
                if dev_time_hh > 12:
                    dev_time_hh -= 12
                dev_time_hhmmss = "{}{}".format(
                        dev_time_hh, dev_time_hhmmss[2:])

            return dev_time_hhmmss
        except:
            return ZERO_HHMMSS
#--------------------------------------------------------------------
    def _timestamp_to_secs(self, utc_timestamp):
        """
        Convert timeStamp into the local time zone and
        return time in seconds
        """

        ts_local = int(float(utc_timestamp)/1000) + \
                self.time_zone_offset_seconds

        ts_str = dt_util.utc_from_timestamp(ts_local).strftime('%X')
        if ts_str[0] == "0":
            ts_str = ts_str[1:]

        t_sec = self._time_to_secs(ts_str)
       # if self.this_update_secs > 43200: t_sec = t_sec + 43200
        log_msg = ("_timestamp_to_secs, ts_str={},"
                         " Seconds={}").format(
                          ts_str, t_sec)
        self._LOGGER_debug_msg(log_msg)
        return t_sec

#--------------------------------------------------------------------
    @staticmethod
    def _timestamp_to_secs_dev(timestamp):
        """
        Convert the timestamp from the device timestamp attribute
        updated by the IOS app.
        Format is --'timestamp': '2019-02-02T12:12:38.358-0500'
        Return epoch seconds
        """
        try:
            if timestamp == '' or timestamp[0:19] == '0000-00-00T00:00:00':
                return 0

            tm = time.mktime(time.strptime(
                    timestamp[0:19], "%Y-%m-%dT%H:%M:%S"))

        except Exception as err:
            _LOGGER.error("Invalid timestamp format, timestamp = '%s'",
                timestamp)
            tm = 0

        return tm
#--------------------------------------------------------------------
    def _calculate_time_zone_offset(self):
        """
        Calculate time zone offset seconds
        """
        try:
            local_zone_offset = dt_util.now().strftime('%z')
            local_zone_offset_secs = int(local_zone_offset[1:3])*3600 + \
                        int(local_zone_offset[3:])*60
            if local_zone_offset[:1] == "-":
                local_zone_offset_secs = -1*local_zone_offset_secs

            e = int(time.time())
            l = time.localtime(e)
            ls= time.strftime('%H%M%S', l)
            g  =time.gmtime(e)
            gs=time.strftime('%H%M%S', g)
            t =dt_util.now().strftime('%H%M%S')

            if (ls == gs):
                self.e_seconds_local_offset_secs = local_zone_offset_secs

            log_msg = ("►►TIME ZONE OFFSET, Local Zone Offset: {},"
                         " Seconds Offset: {}").format(
                          local_zone_offset, local_zone_offset_secs)
            self._LOGGER_debug_msg(log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            x = self._internal_error_msg(fct_name, err, 'CalcTZOffset')
            local_zone_offset_secs = 0

        return local_zone_offset_secs

#--------------------------------------------------------------------
    def _km_to_mi(self, arg_distance, dec_places=2):
        if arg_distance > 0:
            if dec_places == 0:
                return round(arg_distance * self.um_km_mi_factor)
            else:
                return round(arg_distance * self.um_km_mi_factor, dec_places)
        else:
            return arg_distance

    def _mi_to_km(self, arg_distance, dec_places=2):
        if arg_distance > 0:
            if dec_places == 0:
                return round(arg_distance / self.um_km_mi_factor)
            else:
                return round(arg_distance / self.um_km_mi_factor, dec_places)
        else:
            return arg_distance

#--------------------------------------------------------------------
    @staticmethod
    def _calc_distance(from_lat, from_long, to_lat, to_long):
        d = distance(from_lat, from_long, to_lat, to_long) / 1000
        if d < .05:
            d = 0
        return round(d, 2)

#--------------------------------------------------------------------
    @staticmethod
    def _round_to_zero(arg_distance):
        if abs(arg_distance) < .05:
            arg_distance = 0
        return round(arg_distance, 2)

#--------------------------------------------------------------------
    def _add_comma_to_str(self, text):
        """ Add a comma to info if it is not an empty string """
        if text:
            return '{}, '.format(text)
        return ''

#########################################################
#
#   ICLOUD ROUTINES
#
#########################################################
    def service_handler_lost_iphone(self, group, arg_devicename):
        """Call the lost iPhone function if the device is found."""

        if not self.CURRENT_MODE_FMPHN:
            log_msg = ("Lost Phone Alert Error: Alerts can only be sent "
                       "when using tracking_method: fmphn'")
            self._LOGGER_warning_msg(log_msg)
            return

        valid_devicename = self._service_multi_acct_devicename_check(
                "Lost iPhone Service", group, arg_devicename)
        if valid_devicename is False:
            return

        device = self.tracked_devices.get(arg_devicename)
        device.play_sound()

        log_msg = ("iCloud Lost iPhone Alert, Device '{}'").format(
                    arg_devicename)
        self._LOGGER_info_msg(log_msg)

#--------------------------------------------------------------------
    def service_handler_icloud_update(self, group, arg_devicename=None,
                    arg_command=None):
        """
        Authenticate against iCloud and scan for devices.


        Commands:
        - waze reset range = reset the min-max rnge to defaults (1-1000)
        - waze toggle      = toggle waze on or off
        - pause            = stop polling for the devicename or all devices
        - resume           = resume polling devicename or all devices, reset
                             the interval override to normal interval
                             calculations
        - pause-resume     = same as above but toggles between pause and resume
        - zone xxxx        = updates the devie state to xxxx and updates all
                             of the iloud3 attributes. This does the see
                             service call and then an update.
        - reset            = reset everything and rescans all of the devices
        - debug interval   = displays the interval formula being used
        - debug gps        = simulates bad gps accuracy
        - debug old        = simulates that the location informaiton is old
        - info xxx         = the same as 'debug'
        - location         = request location update from ios app
        """

        #If several iCloud groups are used, this will be called for each
        #one. Exit if this instance of iCloud is not the one handling this
        #device. But if devicename = 'reset', it is an event_log service cmd.

        if arg_devicename:
            if (arg_devicename != 'restart'):
                valid_devicename = self._service_multi_acct_devicename_check(
                    "Update iCloud Service", group, arg_devicename)
                if valid_devicename is False:
                    return

        arg_command         = ("{} .").format(arg_command)
        arg_command_cmd     = arg_command.split(' ')[0].lower()
        arg_command_parm    = arg_command.split(' ')[1]       #original value
        arg_command_parmlow = arg_command_parm.lower()

        log_msg = ("iCloud3 Command, Device: '{}', Command: '{}' <WARN>").format(
                arg_devicename, arg_command)
        self._LOGGER_info_msg(log_msg)

        if arg_command_cmd != 'event_log':
            self._save_event(arg_devicename, "Service Call Command "
                "handled ({})".format(arg_command))

        attrs  = {}

        #System level commands
        if arg_command_cmd == 'restart':
            if self.restart_icloud_group_inprocess_flag == False:
                self.restart_icloud_group_request_flag = True

                #if mode flag was in the config file, use it otherwise
                #it will be set to False
                #self.mode = self.mode_config

                #attrs[ATTR_INFO] = '● ICLOUD RESTART REQUESTED ●'
                #for devicename in self.tracked_devices:
                #    self._update_device_sensors(devicename, attrs)
            return

        #elif arg_command_cmd == 'toggle_mode':
        #    self.restart_icloud_group_request_flag = True

        #    attrs[ATTR_INFO] = '● iCloud Disabled set to "{}" ●'.\
        #                format(self.mode)
        #    for devicename in self.tracked_devices:
        #        self._update_device_sensors(devicename, attrs)
        #    return

        elif arg_command_cmd == 'event_log':
            self._update_event_log_sensor_data(arg_devicename)
            return

        #Location level commands
        if arg_command_cmd == 'waze':
            if self.waze_status == WAZE_NOT_USED:
                arg_command_cmd = ''
                return
            elif arg_command_parmlow == 'reset_range':
                self.waze_min_distance = 0
                self.waze_max_distance = 99999
                self.waze_manual_pause_flag = False
                self.waze_status = WAZE_USED
            elif arg_command_parmlow == 'toggle':
                if self.waze_status == WAZE_PAUSED:
                    self.waze_manual_pause_flag = False
                    self.waze_status = WAZE_USED
                else:
                    self.waze_manual_pause_flag = True
                    self.waze_status = WAZE_PAUSED
            elif arg_command_parmlow == 'pause':
                self.waze_manual_pause_flag = False
                self.waze_status = WAZE_USED
            elif arg_command_parmlow != 'pause':
                self.waze_manual_pause_flag = True
                self.waze_status = WAZE_PAUSED

        elif arg_command_cmd == 'zone':     #parmeter is the new zone
            #if 'home' in arg_command_parmlow:    #home/not_home is lower case
            if self.base_zone in arg_command_parmlow:    #home/not_home is lower case
                arg_command_parm = arg_command_parmlow

            kwargs = {}
            attrs  = {}

            self._wait_if_update_in_process(arg_devicename)
            self.next_update_time[arg_devicename]         = ZERO_HHMMSS
            self.next_update_seconds[arg_devicename]      = 0
            self.overrideinterval_seconds[arg_devicename] = 0
            self.update_in_process_flag = False

            self._update_device_icloud('Command', arg_devicename)

            return

        #Device level commands
        device_time_adj = 0
        for devicename in self.tracked_devices:
            if arg_devicename and devicename != arg_devicename:
                continue

            device_time_adj += 3

            now_secs_str = dt_util.now().strftime('%X')
            now_seconds  = self._time_to_secs(now_secs_str)
            x, update_in_secs = divmod(now_seconds, 15)
            update_in_secs = 15 - update_in_secs + device_time_adj

            attrs = {}

            #command preprocessor, reformat specific commands
            if arg_command_cmd in ('debug', 'info'):
                arg_command_cmd = 'resume'      #force retart for changes

                if arg_command_parm == 'logging':
                    self.log_debug_msgs_flag = \
                            (not self.log_debug_msgs_flag)
                    self.debug_control = 'interval' \
                        if self.log_debug_msgs_flag else ''

                elif arg_command_parm in self.debug_control:
                    self.debug_control = ''
                else:
                    self.debug_control = arg_command_parm
                attrs[ATTR_INFO] = '● {} ●'.format(self.debug_control)

            elif arg_command_cmd == 'pause-resume':
                if self.next_update_time[devicename] == 'Paused':
                    arg_command_cmd = 'resume'
                else:
                    arg_command_cmd = 'pause'

            #command processor, execute the entered command
            if arg_command_cmd == 'pause':
                cmd_type = CMD_PAUSE
                self.next_update_seconds[devicename] = 99999
                self.next_update_time[devicename]    = 'Paused'
                attrs[ATTR_INTERVAL]                 ='●PAUSED●'

            elif arg_command_cmd == 'resume':
                cmd_type = CMD_RESUME
                self.next_update_time[devicename]         = ZERO_HHMMSS
                self.next_update_seconds[devicename]      = 0
                self.overrideinterval_seconds[devicename] = 0
                self._update_device_icloud('Resuming', devicename)

            elif arg_command_cmd == 'waze':
                cmd_type = CMD_WAZE
                if self.waze_status == WAZE_USED:
                    self.next_update_time[devicename]         = ZERO_HHMMSS
                    self.next_update_seconds[devicename]      = 0
                    self.overrideinterval_seconds[devicename] = 0
                    attrs[ATTR_NEXT_UPDATE_TIME]              = ZERO_HHMMSS
                    attrs[ATTR_WAZE_DISTANCE]                 = 'Resuming'
                    self._update_device_sensors(devicename, attrs)
                    attrs = {}

                    self._update_device_icloud('Resuming', devicename)
                else:
                    attrs[ATTR_WAZE_DISTANCE] = 'Paused'
                    attrs[ATTR_WAZE_TIME]     = ''

            elif arg_command_cmd == 'location':
                self._request_iosapp_location_update(devicename)
                #attrs[ATTR_INFO] = '● Location Update Requested ●'

            else:
                cmd_type = CMD_ERROR
                attrs[ATTR_INFO] = '● INVALID COMMAND ({}) ●'.format(
                            arg_command_cmd)

            if attrs:
                self._update_device_sensors(devicename, attrs)

        #end for devicename in devs loop

#--------------------------------------------------------------------
    def service_handler_icloud_setinterval(self, group, arg_interval=None,
                    arg_devicename=None):

        """
        Set the interval or process the action command of the given devices.
            'interval' has the following options:
                - 15               = 15 minutes
                - 15 min           = 15 minutes
                - 15 sec           = 15 seconds
                - 5 hrs            = 5 hours
                - Pause            = Pause polling for all devices
                                     (or specific device if devicename
                                      is specified)
                - Resume            = Resume polling for all devices
                                     (or specific device if devicename
                                      is specified)
                - Waze              = Toggle Waze on/off
        """
        #If several iCloud groups are used, this will be called for each
        #one. Exit if this instance of iCloud is not the one handling this
        #device.

        if (self.CURRENT_MODE_IOSAPP and
                self.iosapp_locate_cnt.get(devicename) > \
                    self.max_iosapp_locate_cnt):
            return

        elif arg_devicename:
            valid_devicename = self._service_multi_acct_devicename_check(
                    "Update Interval Service", group, arg_devicename)
            if valid_devicename is False:
                return

        if arg_interval is None:
            if arg_devicename is not None:
                self._save_event(arg_devicename, "Set Interval Command Error, "
                        "no new interval specified")
            return

        cmd_type = CMD_INTERVAL
        new_interval = arg_interval.lower().replace('_', ' ')

#       loop through all devices being tracked and
#       update the attributes. Set various flags if pausing or resuming
#       that will be processed by the next poll in '_polling_loop_15_sec_icloud'
        device_time_adj = 0
        for devicename in self.tracked_devices:
            if arg_devicename and devicename != arg_devicename:
                continue

            device_time_adj += 3

            self._wait_if_update_in_process()

            log_msg = ("►►SET INTERVAL COMMAND Start {}, "
                          "ArgDevname={}, ArgInterval={}"
                          "Old/New Interval: {}:{}").format(
                          devicename, arg_devicename, arg_interval,
                          self.interval_str.get(devicename), new_interval)
            self._LOGGER_debug_msg(log_msg)
            self._save_event(devicename, ("Set Interval Command handled "
                        "New interval is {}").format(arg_interval))

            self.next_update_time[devicename]         = ZERO_HHMMSS
            self.next_update_seconds[devicename]      = 0
            self.overrideinterval_seconds[devicename] = 0

            self.interval_str[devicename] = new_interval
            self.overrideinterval_seconds[devicename] = \
                    self._time_str_to_secs(new_interval)

            now_seconds = \
                self._time_to_secs(dt_util.now().strftime('%X'))
            x, update_in_secs = divmod(now_seconds, 15)
            time_suffix = 15 - update_in_secs + device_time_adj

            attrs  = {}
            attrs[ATTR_INTERVAL] = '●Updating●'

            self._update_device_sensors(devicename, attrs)

            log_msg = ("►►SET INTERVAL COMMAND END {}").format(devicename)
            self._LOGGER_debug_msg(log_msg)
#--------------------------------------------------------------------
    def _service_multi_acct_devicename_check(self, svc_call_name,
            group, devicename):

        #if self.mode:
        #    return False

        if devicename is None:
            log_msg = ("{} Error, no devicename specified").format(svc_call_name)
            self._LOGGER_error_msg(log_msg)
            return False

        info_msg = ("Checking {} for {}").format(
                    svc_call_name, group)

        if (devicename not in self.track_devicename_list):
            event_msg = ("{}:{} not in this group").format(
                    info_msg, devicename)
            #self._save_event(devicename, event_msg)
            self._LOGGER_info_msg(event_msg)
            return False

        event_msg = ("{}:{} Processed").format(
                    info_msg, devicename)
        #self._save_event(devicename, event_msg)
        self._LOGGER_info_msg(event_msg)
        return True
#--------------------------------------------------------------------
