# -*- coding: utf-8 -*-

"""
    Genesis Service Providers
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Configuration of stations
"""

from dimp import ID, Meta, Profile, PublicKey, PrivateKey

from server import Server

s001_name = 'Genesis Station'

s001_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'
s001_id = ID(s001_id)

s001_pk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN PUBLIC KEY-----\n'
            'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDET7fvLupUBUc6ImwJejColybq\n'
            'rU+Y6PwiCKhblGbwVqbvapD2A1hjEu4EtL6mm3v7hcgsO3Df33/ShRua6GW9/JQV\n'
            'DLfdznLfuTg8w5Ug+dysJfbrmB1G7nbqDYEyXQXNRWpQsLHYSD/ihaSKWNnOuV0c\n'
            '7ieJEzQAp++O+d3WUQIDAQAB\n'
            '-----END PUBLIC KEY-----'
}
s001_pk = PublicKey(s001_pk)

s001_sk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN RSA PRIVATE KEY-----\n'
            'MIICXAIBAAKBgQDET7fvLupUBUc6ImwJejColybqrU+Y6PwiCKhblGbwVqbvapD2\n'
            'A1hjEu4EtL6mm3v7hcgsO3Df33/ShRua6GW9/JQVDLfdznLfuTg8w5Ug+dysJfbr\n'
            'mB1G7nbqDYEyXQXNRWpQsLHYSD/ihaSKWNnOuV0c7ieJEzQAp++O+d3WUQIDAQAB\n'
            'AoGAA+J7dnBYWv4JPyth9ayNNLLcBmoUUIdwwNgow7orsM8YKdXzJSkjCT/dRarR\n'
            'eIDMaulmcQiils2IjSEM7ytw4vEOPWY0AVj2RPhD83GcYyw9sUcTaz22R5UgsQ8X\n'
            '7ikqBX+YO+diVBf2EqAoEihdO8App6jtlsQGsUjjlrKQIMECQQDSphyRLixymft9\n'
            'bip7N6YZA5RoiO1yJhPn6X2EQ0QxX8IwKlV654jhDcLsPBUJsbxYK0bWfORZLi8V\n'
            '+ambjnbxAkEA7pNmEvw/V+zw3DDGizeyRbhYgeZxAgKwXd8Vxd6pFl4iQRmvu0is\n'
            'd94jZzryBycP6HSRKN11stnDJN++5TEVYQJALfTjoqDqPY5umazhQ8SeTjLDvBKz\n'
            'iwXXre743VQ3mnYDzbJOt+OvrznrXtK03EqUhr/aUo0o3HQA/dBcOn3YYQJBAM98\n'
            'yAh48wogGnYVwYbwgI3cPrVy2hO6jPKHAyOce4flhHsDwO7rzHtPaZDtFfMciNxN\n'
            'DLXyrNtIQkx+f0JLBuECQCUfuJGL+qbExpD3tScBJPAIJ8ZVRVbTcL3eHC9q6gx3\n'
            '7Fmn9KfbQrUHPwwdo5nuK+oVVYnFkyKGPSer7ras8ro=\n'
            '-----END RSA PRIVATE KEY-----'
}
s001_sk = PrivateKey(s001_sk)

s001_meta = {
    'version': 1,
    'seed': 'gsp-s001',
    'key': s001_pk,
    'fingerprint': 'R+Bv3RlVi8pNuVWDJ8uEp+N3l+B04ftlaNFxo7u8+V6eSQsQJNv7tfQNFdC633Up'
                   'XDw3zZHvQNnkUBwthaCJTbEmy2CYqMSx/BLuaS7spkSZJJAT7++xqif+pRjdw9yM'
                   '/aPufKHS4PAvGec21PsUpQzOV5TQFyF5CDEDVLC8HVY='
}
s001_meta = Meta(s001_meta)

s001_profile = Profile.new(identifier=s001_id)
s001_profile.name = s001_name
s001_profile.sign(private_key=s001_sk)

"""
    Asymmetric Key Data
    ~~~~~~~~~~~~~~~~~~~
    
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDET7fvLupUBUc6ImwJejColybq
rU+Y6PwiCKhblGbwVqbvapD2A1hjEu4EtL6mm3v7hcgsO3Df33/ShRua6GW9/JQV
DLfdznLfuTg8w5Ug+dysJfbrmB1G7nbqDYEyXQXNRWpQsLHYSD/ihaSKWNnOuV0c
7ieJEzQAp++O+d3WUQIDAQAB
-----END PUBLIC KEY-----

-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDET7fvLupUBUc6ImwJejColybqrU+Y6PwiCKhblGbwVqbvapD2
A1hjEu4EtL6mm3v7hcgsO3Df33/ShRua6GW9/JQVDLfdznLfuTg8w5Ug+dysJfbr
mB1G7nbqDYEyXQXNRWpQsLHYSD/ihaSKWNnOuV0c7ieJEzQAp++O+d3WUQIDAQAB
AoGAA+J7dnBYWv4JPyth9ayNNLLcBmoUUIdwwNgow7orsM8YKdXzJSkjCT/dRarR
eIDMaulmcQiils2IjSEM7ytw4vEOPWY0AVj2RPhD83GcYyw9sUcTaz22R5UgsQ8X
7ikqBX+YO+diVBf2EqAoEihdO8App6jtlsQGsUjjlrKQIMECQQDSphyRLixymft9
bip7N6YZA5RoiO1yJhPn6X2EQ0QxX8IwKlV654jhDcLsPBUJsbxYK0bWfORZLi8V
+ambjnbxAkEA7pNmEvw/V+zw3DDGizeyRbhYgeZxAgKwXd8Vxd6pFl4iQRmvu0is
d94jZzryBycP6HSRKN11stnDJN++5TEVYQJALfTjoqDqPY5umazhQ8SeTjLDvBKz
iwXXre743VQ3mnYDzbJOt+OvrznrXtK03EqUhr/aUo0o3HQA/dBcOn3YYQJBAM98
yAh48wogGnYVwYbwgI3cPrVy2hO6jPKHAyOce4flhHsDwO7rzHtPaZDtFfMciNxN
DLXyrNtIQkx+f0JLBuECQCUfuJGL+qbExpD3tScBJPAIJ8ZVRVbTcL3eHC9q6gx3
7Fmn9KfbQrUHPwwdo5nuK+oVVYnFkyKGPSer7ras8ro=
-----END RSA PRIVATE KEY-----

"""

s001_host = '0.0.0.0'
s001_port = 9394

s001 = Server(identifier=s001_id, host=s001_host, port=s001_port)
s001.privateKey = s001_sk
s001.running = False
