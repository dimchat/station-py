# -*- coding: utf-8 -*-

"""
    Immortal Accounts
    ~~~~~~~~~~~~~~~~~

    Genesis accounts for test: "Immortal Hulk", "Monkey King"
"""

from mkm.immortals import Immortals

from dimp import ID, LocalUser

immortals = Immortals()

#
#  Immortal Hulk
#

hulk_id = 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'
hulk_id = ID(hulk_id)

hulk_meta = immortals.meta(identifier=hulk_id)
hulk_profile = immortals.profile(identifier=hulk_id)
hulk_sk = immortals.private_key_for_signature(identifier=hulk_id)
hulk_pk = hulk_meta.key
hulk_name = hulk_profile.name

hulk = LocalUser(hulk_id)


#
#  Monkey King
#

moki_id = 'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'
moki_id = ID(moki_id)

moki_meta = immortals.meta(identifier=moki_id)
moki_profile = immortals.profile(identifier=moki_id)
moki_sk = immortals.private_key_for_signature(identifier=moki_id)
moki_pk = moki_meta.key
moki_name = moki_profile.name

moki = LocalUser(moki_id)
