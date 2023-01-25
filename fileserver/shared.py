# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

import getopt
import sys
from typing import Optional, Set

from dimples import hex_decode
from dimples.database import Storage

from libs.utils import Singleton
from libs.common import Config


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        # cached values
        self.__image_types: Optional[Set[str]] = None
        self.__allowed_types: Optional[Set[str]] = None
        self.__md5_secret: Optional[bytes] = None

    @property
    def server_host(self) -> str:
        return self.config.get_string(section='ftp', option='host')

    @property
    def server_port(self) -> int:
        return self.config.get_integer(section='ftp', option='port')

    #
    #   download
    #

    @property
    def avatar_url(self) -> str:
        return self.config.get_string(section='ftp', option='avatar_url')

    @property
    def download_url(self) -> str:
        return self.config.get_string(section='ftp', option='download_url')

    #
    #   upload
    #

    @property
    def avatar_directory(self) -> str:
        return self.config.get_string(section='ftp', option='avatar_dir')

    @property
    def upload_directory(self) -> str:
        return self.config.get_string(section='ftp', option='upload_dir')

    @property
    def image_file_types(self) -> Set[str]:
        types = self.__image_types
        if types is None:
            types = self.__get_set(section='ftp', option='image_types')
            assert len(types) > 0, 'image file types not set'
            self.__image_types = types
        return types

    @property
    def allowed_file_types(self) -> Set[str]:
        types = self.__allowed_types
        if types is None:
            types = self.__get_set(section='ftp', option='allowed_types')
            assert len(types) > 0, 'allowed file types not set'
            self.__allowed_types = types
        return types

    def __get_set(self, section: str, option: str) -> Set[str]:
        result = set()
        value = self.config.get_string(section=section, option=option)
        assert value is not None, 'string value not found: section=%s, option=%s' % (section, option)
        array = value.split(',')
        for item in array:
            string = item.strip()
            if len(string) > 0:
                result.add(string)
        return result

    @property
    def md5_secret(self) -> bytes:
        key = self.__md5_secret
        if key is None:
            string = self.config.get_string(section='ftp', option='md5_secret')
            assert string is not None, 'md5 key not set'
            key = hex_decode(string=string)
            self.__md5_secret = key
        return key


def show_help(cmd: str, app_name: str, default_config: str):
    print('')
    print('    %s' % app_name)
    print('')
    print('usages:')
    print('    %s [--config=<FILE>]' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % default_config)
    print('    --help, -h      show this help message and exit')
    print('')


def create_config(app_name: str, default_config: str) -> Config:
    """ Step 1: load config """
    cmd = sys.argv[0]
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=cmd, app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check config filepath
    if ini_file is None:
        ini_file = default_config
    if not Storage.exists(path=ini_file):
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config from file
    config = Config.load(file=ini_file)
    print('>>> config loaded: %s => %s' % (ini_file, config))
    return config
