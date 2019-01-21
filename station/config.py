# -*- coding: utf-8 -*-

"""
    Configuration
    ~~~~~~~~~~~~~

    Configure Station
"""

import dimp

from station.gsp_s001 import *


"""
    DIM Network Server
"""
host = '127.0.0.1'
port = 9394


station_id = dimp.ID(s001_id)
station_sk = dimp.PrivateKey(s001_sk)
station_pk = station_sk.publicKey

station = dimp.Station(identifier=station_id, public_key=station_pk, host=host, port=port)
station.privateKey = station_sk
