# Decentralized Instant Messaging Station (Python)

Demo project for [pypi/dimp](https://pypi.org/project/dimp/) packages.

Source codes:

1. [DIM SDK (sdk-py)](https://github.com/dimchat/sdk-py)
2. [DIM Protocol (core-py)](https://github.com/dimchat/core-py)
3. [Message Module (dkd-py)](https://github.com/dimchat/dkd-py)
4. [Account Module (mkm-py)](https://github.com/dimchat/mkm-py)

## Usages

### 0. Install Requirements

```
pip3 install -r requirements.txt
```

### 1. Create Accounts

1.0. Usages

```
tests/register.py help generate
tests/register.py help modify
```

1.1. Create station account (define your ID.seed)

```
tests/register.py generate STATION --seed="gsp-s001"
```

copy the new ID (e.g.: "gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC")

```
tests/register.py modify {NewID} --name="Station1" --host="{WAN_IP}" --port=9394
```

1.2. Create group assistant

```
tests/register.py generate ROBOT --seed="assistant"
tests/register.py modify {NewID} --name="GroupBot1"
```

1.3. Create search bot

```
tests/register.py generate ROBOT --seed="archivist"
tests/register.py modify {NewID} --name="SearchEngine1"
```

### 2. Edit "etc/config.py"

```
#
#   2.1. Replace your new station ID here
#
station_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'
all_stations = [
    station_id,
    
    #
    #   Place neighbor stations with host & port here
    #
    
    # {'ID': 'gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW', 'host': '106.52.25.169', 'port': 9394},
]

#
#   2.2. Replace your new bots here
#
archivist_id = 'archivist@2PVvMPm1j74HFWAGnDSZFkLsbEgM3KCGkTR'
assistant_id = 'assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq'

#
#   2.3. Set to your data directory
#
base_dir = '/data/.dim'
```

### 3. Run

```
chmod a+x start_*.sh
./start_station.sh
./start_assistant.sh
./start_archivist.sh
```

### Test Client

```
python3 tests/client.py
```

## Architecture

```

        /----------------\                     /----------------\
        |  User1 (moki)  |                     |  User2 (hulk)  |
        \----------------/                     \----------------/
                |                                      ^
                |                                      |
    ============|======================================|=============
                |                                      |
                V                                      |
        .....................               .....................
        :  RequestHandler1  : ---+     +--> :  RequestHandler2  :
        .....................    |     |    .....................
              |                  V     |                 |
              |              /-------------\             |
        ..............       |  TCPServer  |       ..............
        :  Session1  :        >...........<        :  Session2  :
        ..............       |   Station   |       ..............
              |              \-------------/             |
              |                     |                    |
              |          /---------------------\         |
              |          |      Database       |         |
              |           >...................<          |
              |          |  Barrack, KeyStore  |         |
              |          \---------------------/         |
              |                                          |
              |            /-----------------\           |
              \----------> |  Session Server | <---------/
                           \-----------------/
    
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                  DIMP
                               (DKD, MKM)
    
```
