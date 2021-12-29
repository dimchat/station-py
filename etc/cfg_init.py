# -*- coding: utf-8 -*-

from typing import Optional

from dimp import ID
from dimsdk import Station
from dimsdk.ans import keywords as ans_keywords

from libs.utils import Log
from libs.database import Storage, Database
from libs.common import SharedFacebook, AddressNameServer

from etc.config import base_dir
from etc.config import gsp_conf
from etc.config import ans_reserved_records
from etc.config import station_id, assistant_id, archivist_id


Log.info('======== Initializing Configurations ========')


"""
    Database
    ~~~~~~~~
"""
Log.info(">>> Local storage directory: %s" % base_dir)
Storage.root = base_dir
g_database = Database()


"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = SharedFacebook()


"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""
g_ans = AddressNameServer()


def update_ans(name: str, identifier: Optional[ID] = None):
    Log.info('Update ANS: %s -> %s' % (name, identifier))
    if name in ans_keywords:
        # remove reserved name temporary
        index = ans_keywords.index(name)
        ans_keywords.remove(name)
        g_ans.save(name=name, identifier=identifier)
        ans_keywords.insert(index, name)
    else:
        # not reserved name, save it directly
        g_ans.save(name=name, identifier=identifier)


Log.info('-------- Loading ANS reserved records')
for key in ans_reserved_records:
    _id = ID.parse(identifier=ans_reserved_records[key])
    assert _id is not None, 'ANS record error: %s, %s' % (key, ans_reserved_records[key])
    update_ans(name=key, identifier=_id)


"""
    Station Info Loaders
    ~~~~~~~~~~~~~~~~~~~~

    Loading station info from service provider configuration
"""


def create_station(info: dict) -> Station:
    host = info.get('host')
    port = info.get('port', 9394)
    identifier = info.get('ID')
    identifier = ID.parse(identifier=identifier)
    assert identifier is not None and host is not None, 'station info error: %s' % info
    server = Station(identifier=identifier, host=host, port=port)
    g_facebook.cache_user(user=server)
    Log.info('Station created: %s' % server)
    return server


"""
    Service Provider
    ~~~~~~~~~~~~~~~~
"""
Log.info('-------- Loading GSP info: %s' % gsp_conf)
sp_info = Storage.read_json(path=gsp_conf)
assert isinstance(sp_info, dict), 'failed to load SP info: %s' % gsp_conf
# all stations owned by this SP
all_stations = sp_info['stations']
Log.info('>>> Loading %d stations' % len(all_stations))
all_stations = [create_station(info=item) for item in all_stations]
# current station
station_id = ID.parse(identifier=station_id)
if station_id is not None:
    update_ans(name='station', identifier=station_id)
elif len(all_stations) > 0:
    station_id = all_stations[0].identifier
    update_ans(name='station', identifier=station_id)
# connected stations
neighbor_stations = []
for item in all_stations:
    if item.identifier != station_id:
        Log.info('Add neighbor station: %s' % item)
        neighbor_stations.append(item)
Log.info('Got current station: %s' % station_id)


"""
    System Bots
    ~~~~~~~~~~~

    1. assistant: bot for group message
    2. archivist: bot for searching users
"""
Log.info('-------- Loading bots')

# set default assistant
assistant_id = ID.parse(identifier=assistant_id)
if assistant_id is not None:
    update_ans(name='assistant', identifier=assistant_id)
# add group assistants
group_assistants = sp_info['assistants']
group_assistants = [ID.parse(identifier=item) for item in group_assistants]
Log.info('Group assistants: %s' % group_assistants)
for ass in group_assistants:
    g_facebook.add_assistant(assistant=ass)
# check default assistant
if assistant_id is None and len(group_assistants) > 0:
    assistant_id = group_assistants[0]
    update_ans(name='assistant', identifier=assistant_id)
Log.info('Default assistant: %s' % assistant_id)

# set default search engine
archivist_id = ID.parse(identifier=archivist_id)
if archivist_id is not None:
    update_ans(name='archivist', identifier=archivist_id)
# add search engines
search_archivists = sp_info['archivists']
search_archivists = [ID.parse(identifier=item) for item in search_archivists]
Log.info('Search archivists: %s' % search_archivists)
# check default search engine
if archivist_id is None and len(group_assistants) > 0:
    archivist_id = search_archivists[0]
    update_ans(name='archivist', identifier=archivist_id)
Log.info('Default archivist: %s' % archivist_id)
