# Decentralized Instant Messaging Station (Python)

## Server Installation Manual

### Requirements

* gcc

```
yum install -y gcc
```

* OpenSSL

```
yum install -y openssl-devel
```

* zlib

```
yum install -y zlib-devel
```

* _ctypes

```
yum install -y libffi-devel
```

* Python 3.7+

```
cd /tmp/
wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tar.xz
tar -xvf Python-3.7.0.tar.xz
cd Python-3.7.0/
```

(make sure module 'ssl' enabled)

```
# vi Modules/Setup.dist

    206 # Socket module helper for socket(2)
    207 _socket socketmodule.c
    208 
    209 # Socket module helper for SSL support; you must comment out the other
    210 # socket line above, and possibly edit the SSL variable:
    211 SSL=/usr/local/ssl
    212 _ssl _ssl.c \
    213         -DUSE_SSL -I$(SSL)/include -I$(SSL)/include/openssl \
    214         -L$(SSL)/lib -lssl -lcrypto

:wq
```

```
./configure
make & make install
```

* git

```
yum install -y git
```

* pip3

```
pip3 install --upgrade pip
```

* fix renamed module Crypto

```
pip3 install pycryptodome
```

### DIMS Installation

```
cd /srv/
git clone https://github.com/dimchat/station-py.git dims

cd dims/
chmod a+x start_station.sh

pip3 install apns2
pip3 install dimp
```

### DIMS Configuration

Edit **station/config.py**

* Database directory: ```database.base_dir = '/data/.dim/'```
* Listening port: ```station_port = 9394```

### Check running every 10 seconds

crontab -e

```
# DIM Station
* * * * * /srv/dim/start_station.sh
* * * * * sleep 10; /srv/dims/start_station.sh
* * * * * sleep 20; /srv/dims/start_station.sh
* * * * * sleep 30; /srv/dims/start_station.sh
* * * * * sleep 40; /srv/dims/start_station.sh
* * * * * sleep 50; /srv/dims/start_station.sh
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

(Moky @ Fri Apr 26 17:37:23 CST 2019)
