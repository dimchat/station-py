# -*- coding: utf-8 -*-

"""
    Immortal Accounts
    ~~~~~~~~~~~~~~~~~

    Genesis accounts for test: "Immortal Hulk", "Monkey King"
"""

from mkm import PublicKey, PrivateKey
from mkm import ID, Meta, Profile, User


#
#  Immortal Hulk
#

hulk_id = 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'
hulk_id = ID(hulk_id)

hulk_name = 'Hulk'

hulk_pk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN PUBLIC KEY-----\n'
            'MIGJAoGBALB+vbUK48UU9rjlgnohQowME+3JtTb2hLPqtatVOW364/EKFq0/PSdn'
            'ZVE9V2Zq+pbX7dj3nCS4pWnYf40ELH8wuDm0Tc4jQ70v4LgAcdy3JGTnWUGiCsY+'
            '0Z8kNzRkm3FJid592FL7ryzfvIzB9bjg8U2JqlyCVAyUYEnKv4lDAgMBAAE=\n'
            '-----END PUBLIC KEY-----'
}
hulk_pk = PublicKey(hulk_pk)

hulk_sk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN RSA PRIVATE KEY-----\n'
            'MIICXQIBAAKBgQCwfr21CuPFFPa45YJ6IUKMDBPtybU29oSz6rWrVTlt+uPxChat'
            'Pz0nZ2VRPVdmavqW1+3Y95wkuKVp2H+NBCx/MLg5tE3OI0O9L+C4AHHctyRk51lB'
            'ogrGPtGfJDc0ZJtxSYnefdhS+68s37yMwfW44PFNiapcglQMlGBJyr+JQwIDAQAB'
            'AoGAVc0HhJ/KouDSIIjSqXTJ2TN17L+GbTXixWRw9N31kVXKwj9ZTtfTbviA9MGR'
            'X6TaNcK7SiL1sZRiNdaeC3vf9RaUe3lV3aR/YhxuZ5bTQNHPYqJnbbwsQkp4IOwS'
            'WqOMCfsQtP8O+2DPjC8Jx7PPtOYZ0sC5esMyDUj/EDv+HUECQQDXsPlTb8BAlwWh'
            'miAUF8ieVENR0+0EWWU5HV+dp6Mz5gf47hCO9yzZ76GyBM71IEQFdtyZRiXlV9CB'
            'OLvdlbqLAkEA0XqONVaW+nNTNtlhJVB4qAeqpj/foJoGbZhjGorBpJ5KPfpD5BzQ'
            'gsoT6ocv4vOIzVjAPdk1lE0ACzaFpEgbKQJBAKDLjUO3ZrKAI7GSreFszaHDHaCu'
            'Bd8dKcoHbNWiOJejIERibbO27xfVfkyxKvwwvqT4NIKLegrciVMcUWliivsCQQCi'
            'A1Z/XEQS2iUO89tVn8JhuuQ6Boav0NCN7OEhQxX3etFS0/+0KrD9psr2ha38qnww'
            'zaaJbzgoRdF12qpL39TZAkBPv2lXFNsn0/Jq3cUemof+5sm53KvtuLqxmZfZMAuT'
            'SIbB+8i05JUVIc+mcYqTqGp4FDfz6snzt7sMBQdx6BZY\n'
            '-----END RSA PRIVATE KEY-----'
}
hulk_sk = PrivateKey(hulk_sk)

hulk_meta = {
    'version': 0x01,
    'seed': 'hulk',
    'key': hulk_pk,
    'fingerprint': 'jIPGWpWSbR/DQH6ol3t9DSFkYroVHQDvtbJErmFztMUP2DgRrRSNWuoKY5Y26qL3'
                   '8wfXJQXjYiWqNWKQmQe/gK8M8NkU7lRwm+2nh9wSBYV6Q4WXsCboKbnM0+HVn9Vd'
                   'fp21hMMGrxTX1pBPRbi0567ZjNQC8ffdW2WvQSoec2I='
}
hulk_meta = Meta(hulk_meta)

hulk_profile = Profile.new(identifier=hulk_id)
hulk_profile.name = hulk_name
hulk_profile.sign(private_key=hulk_sk)

hulk = User(hulk_id)


#
#  Monkey King
#

moki_id = 'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'
moki_id = ID(moki_id)

moki_name = 'Monkey King'

moki_pk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN PUBLIC KEY-----\n'
            'MIGJAoGBALQOcgxhhV0XiHELKYdG587Tup261qQ3ahAGPuifZvxHXTq+GgulEyXi'
            'ovwrVjpz7rKXn+16HgspLHpp5agv0WsSn6k2MnQGk5RFXuilbFr/C1rEX2X7uXlU'
            'XDMpsriKFndoB1lz9P3E8FkM5ycG84hejcHB+R5yzDa4KbGeOc0tAgMBAAE=\n'
            '-----END PUBLIC KEY-----'
}
moki_pk = PublicKey(moki_pk)

moki_sk = {
    'algorithm': 'RSA',
    'data': '-----BEGIN RSA PRIVATE KEY-----\n'
            'MIICXQIBAAKBgQC0DnIMYYVdF4hxCymHRufO07qdutakN2oQBj7on2b8R106vhoL'
            'pRMl4qL8K1Y6c+6yl5/teh4LKSx6aeWoL9FrEp+pNjJ0BpOURV7opWxa/wtaxF9l'
            '+7l5VFwzKbK4ihZ3aAdZc/T9xPBZDOcnBvOIXo3Bwfkecsw2uCmxnjnNLQIDAQAB'
            'AoGADi5wFaENsbgTh0HHjs/LHKto8JjhZHQ33pS7WjOJ1zdgtKp53y5sfGimCSH5'
            'q+drJrZSApCCcsMWrXqPO8iuX/QPak72yzTuq9MEn4tusO/5w8/g/csq+RUhlLHL'
            'dOrPfVciMBXgouT8BB6UMa0e/g8K/7JBV8v1v59ZUccSSwkCQQD67yI6uSlgy1/N'
            'WqMENpGc9tDDoZPR2zjfrXquJaUcih2dDzEbhbzHxjoScGaVcTOx/Aiu00dAutoN'
            '+Jpovpq1AkEAt7EBRCarVdo4YKKNnW3cZQ7u0taPgvc/eJrXaWES9+MpC/NZLnQN'
            'F/NZlU9/H2607/d+Xaac6wtxkIQ7O61bmQJBAOUTMThSmIeYoZiiSXcrKbsVRneR'
            'JZTKgB0SDZC1JQnsvCQJHld1u2TUfWcf3UZH1V2CK5sNnVpmOXHPpYZBmpECQBp1'
            'hJkseMGFDVneEEf86yIjZIM6JLHYq2vT4fNr6C+MqPzvsIjgboJkqyK2sLj2WVm3'
            'bJxQw4mXvGP0qBOQhQECQQCOepIyFl/a/KmjVZ5dvmU2lcHXkqrvjcAbpyO1Dw6p'
            '2OFCBTTQf3QRmCoys5/dyBGLDhRzV5Obtg6Fll/caLXs\n'
            '-----END RSA PRIVATE KEY-----'
}
moki_sk = PrivateKey(moki_sk)

moki_meta = {
    'version': 0x01,
    'seed': 'moki',
    'key': moki_pk,
    'fingerprint': 'ld68TnzYqzFQMxeJ6N+aZa2jRf9d4zVx4BUiBlmur67ne8YZF08plhCiIhfyYDIw'
                   'wW7KLaAHvK8gJbp0pPIzLR4bhzu6zRpDLzUQsq6bXgMp+WAiZtFm6IHWNUwUEYcr'
                   '3iSvTn5L1HunRt7kBglEjv8RKtbNcK0t1Xto375kMlo='
}
moki_meta = Meta(moki_meta)

moki_profile = Profile.new(identifier=moki_id)
moki_profile.name = moki_name
moki_profile.sign(private_key=moki_sk)

moki = User(moki_id)
