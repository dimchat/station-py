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

### 2. Edit "etc/gsp.js" & "etc/config.py"

```
    "stations": [
        //
        //  2.1. Add your new station ID with host & port here
        //
        {"ID": "gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC", "host": "106.52.25.169", "port": 9394}
    ],
    "assistants": [
        //
        //  2.2. Add your new assistant ID here
        //
        "assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq"
    ],
    "archivists": [
        //
        //  2.3. Add your new archivist ID here
        //
        "archivist@2Ph6zsUBL8rbimRArb2f539j64JUJJQoDpZ"
    ]
```

```
#
#   2.3. Replace your new station ID here
#
station_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'

#
#   2.4. Replace your new bots ID here
#
assistant_id = 'assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq'
archivist_id = 'archivist@2Ph6zsUBL8rbimRArb2f539j64JUJJQoDpZ'

#
#   2.5. Set to your data directory
#
base_dir = '/data/.dim'
```

### 3. Run

```
chmod a+x start*.sh
./start_station.sh
./start_octopus.sh
./start_archivist.sh
./start_assistant.sh
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
