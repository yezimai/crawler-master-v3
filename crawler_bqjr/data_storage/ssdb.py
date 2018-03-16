# coding=utf8

"""
Python client for https://github.com/ideawu/ssdb
"""

__version__ = '0.1.7'
__license__ = 'bsd2'

import spp
import sys
import socket
import threading
import contextlib

if sys.version > '3':
    # binary: cast str to bytes
    binary = lambda string: bytes(string, 'utf8')
    # string: cast bytes to native string
    string = lambda binary: binary.decode('utf8')
else:
    binary = str
    string = str

commands = {
    'auth': int,
    'set': int,
    'setx': int,
    'expire': int,
    'ttl': int,
    'setnx': int,
    'get': str,
    'getset': str,
    'del': int,
    'incr': int,
    'exists': bool,
    'getbit': int,
    'setbit': int,
    'countbit': int,
    'substr': str,
    'strlen': int,
    'keys': list,
    'scan': list,
    'rscan': list,
    'multi_set': int,
    'multi_get': list,
    'multi_del': int,
    'hset': int,
    'hget': str,
    'hdel': int,
    'hincr': int,
    'hexists': bool,
    'hsize': int,
    'hlist': list,
    'hrlist': list,
    'hkeys': list,
    'hgetall': list,
    'hscan': list,
    'hrscan': list,
    'hclear': int,
    'multi_hset': int,
    'multi_hget': list,
    'multi_hdel': int,
    'zset': int,
    'zget': int,
    'zdel': int,
    'zincr': int,
    'zexists': bool,
    'zsize': int,
    'zlist': list,
    'zrlist': list,
    'zkeys': list,
    'zscan': list,
    'zrscan': list,
    'zrank': int,
    'zrrank': int,
    'zrange': list,
    'zrrange': list,
    'zclear': int,
    'zcount': int,
    'zsum': int,
    'zavg': float,
    'zremrangebyrank': int,
    'zremrangebyscore': int,
    'multi_zset': int,
    'multi_zget': list,
    'multi_zdel': int,
    'qsize': int,
    'qclear': int,
    'qfront': str,
    'qback': str,
    'qget': str,
    'qslice': list,
    'qpush': int,
    'qpush_front': int,
    'qpush_back': int,
    'qpop': str,
    'qpop_front': str,
    'qpop_back': str,
    'qlist': list,
    'qrlist': list,
    'info': list
}

conversions = {
    int: lambda lst: int(lst[0]),
    str: lambda lst: str(lst[0]),
    float: lambda lst: float(lst[0]),
    bool: lambda lst: bool(int(lst[0])),
    list: lambda lst: list(lst)
}


class SSDBException(Exception):
    pass


class Connection(threading.local):
    def __init__(self, host='0.0.0.0', port=8888, auth=None, auth_enable=False):
        self.auth = auth
        self.auth_enable = auth_enable
        self.host = host
        self.port = port
        self.sock = None
        self.commands = []
        self.parser = spp.Parser()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(1)
        self.sock.connect((self.host, self.port))
        if self.auth:
            self.auth_connect()

    def auth_connect(self):
        if self.sock is None:
            self.connect()

        # send commands
        auth = list(map(self.encode, [('auth', self.auth)]))
        self.sock.sendall(binary(''.join(auth)))

        chunks = []

        while len(chunks) < len(auth):
            buf = self.sock.recv(4096)

            if not isinstance(buf, bytes) and not len(buf):
                self.close()
                raise socket.error('Socket closed on remote end')

            self.parser.feed(string(buf))
            chunk = self.parser.get()
            if chunk is not None:
                chunks.append(chunk)

        for status, body in chunks:
            if status == 'ok' and body == '1':
                return True
            else:
                raise SSDBException('%s  %s  %s' % ('认证失败 ', status, body))

    def close(self):
        self.parser.clear()
        self.sock.close()
        self.sock = None

    def encode(self, args):
        lst = []
        pattern = '%d\n%s\n'

        for arg in args:
            size = len(binary(str(arg)))
            lst.append(pattern % (size, arg))
        lst.append('\n')
        return ''.join(lst)

    def build(self, type, data):
        return conversions[type](data)

    def request(self):  # noqa
        # lazy connect
        if self.sock is None:
            self.connect()

        # send commands
        cmds = list(map(self.encode, self.commands))
        self.sock.sendall(binary(''.join(cmds)))

        chunks = []

        while len(chunks) < len(self.commands):
            buf = self.sock.recv(4096)

            if not isinstance(buf, bytes) and not len(buf):
                self.close()
                raise socket.error('Socket closed on remote end')

            self.parser.feed(string(buf))
            chunk = self.parser.get()
            if chunk is not None:
                chunks.append(chunk)

        responses = []

        for index, chunk in enumerate(chunks):
            cmd = self.commands[index]
            status, body = chunk[0], chunk[1:]

            if status == 'ok':
                data = self.build(commands[cmd[0]], body)
                responses.append(data)
            elif status == 'not_found':
                responses.append(None)
            else:
                raise SSDBException('%r on command %r', status, cmd)
        self.commands[:] = []
        return responses


class BaseClient(object):
    def __init__(self):
        def create_method(command):
            def method(*args):
                self.conn.commands.append((command,) + args)
                if not isinstance(self, Pipeline):
                    return self.conn.request()[0]

            return method

        for command in commands:
            name = {'del': 'delete'}.get(command, command)
            setattr(self, name, create_method(command))


class Client(BaseClient):
    def __init__(self, host='0.0.0.0', port=8888, auth_enable=False, auth=None):
        super(Client, self).__init__()
        self.host = host
        self.port = port
        self.conn = Connection(host=host, port=port, auth=auth, auth_enable=auth_enable)

    def close(self):
        self.conn.close()

    @contextlib.contextmanager
    def pipeline(self):
        yield Pipeline(self.conn)


class Pipeline(BaseClient):
    def __init__(self, conn):
        super(Pipeline, self).__init__()
        self.conn = conn

    def execute(self):
        return self.conn.request()
