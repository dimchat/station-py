
import socket
from typing import Optional

import stun


STUN_SERVERS = (
    'stun.ekiga.net',
    'stun.ideasip.com',
    'stun.voiparound.com',
    'stun.voipbuster.com',
    'stun.voipstunt.com',
    'stun.voxgratia.org'
)

STUN_PORT = 3478


class UDPSocket(stun.Delegate):

    def __init__(self):
        super().__init__()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__socket = s
        # local host & port
        self.__ip = '0.0.0.0'
        self.__port = 0

    def local_ip(self) -> str:
        return self.__ip

    def local_port(self) -> int:
        return self.__port

    def send(self, data: bytes, remote_host: str, remote_port: int) -> int:
        try:
            return self.__socket.sendto(data, (remote_host, remote_port))
        except socket.error:
            return -1

    def receive(self, buffer_size: int=2048) -> (bytes, tuple):
        try:
            return self.__socket.recvfrom(buffer_size)
        except socket.error:
            return None, None

    def bind(self, ip: str, port: int):
        address = (ip, port)
        self.__socket.bind(address)
        self.__ip = ip
        self.__port = port

    def settimeout(self, value: Optional[float]):
        self.__socket.settimeout(value)

    def feedback(self, message: str):
        print('::', message)


def main(ip: str='0.0.0.0', port: int=9394):
    # create socket
    sock = UDPSocket()
    sock.bind(ip=ip, port=port)
    sock.settimeout(5)
    # create client
    client = stun.Client()
    client.delegate = sock
    port = STUN_PORT
    for host in STUN_SERVERS:
        print('--------------------------------')
        print('-- Querying: %s ...' % host)
        ret = client.get_nat_type(stun_host=host, stun_port=port)
        print('-- Result:', ret)
        print('--------------------------------')


if __name__ == '__main__':
    main()
