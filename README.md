# Decentralized Instant Messaging Station (Python)

Demo project for [pypi/dimp](https://pypi.org/project/dimp/) packages.

Source codes:

1. [DIM Protocol (core-py)](https://github.com/dimchat/core-py)
2. [Message Module (dkd-py)](https://github.com/dimchat/dkd-py)
3. [Account Module (mkm-py)](https://github.com/dimchat/mkm-py)

## Usages

1.) Install Requirements

```
pip3 install dimp
pip3 install apns2
```

2.) Run Server

```
cd station-py
python3 station/start.py 
```

3.) Run Test Client

```
cd station-py
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
