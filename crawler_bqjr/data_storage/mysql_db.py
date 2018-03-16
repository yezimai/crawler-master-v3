# -*- coding: UTF-8 -*-

from threading import local

from pymysql import connect as db_connect, Error as DB_Error


DATABASES = {
    'local': {'db': 'test',
              'user': 'test',
              'passwd': '123456',
              'host': 'localhost',
              # 'unix_socket': "MySQL",
              # 'named_pipe': True,
              },
}


class CursorWrapper(object):
    """
    对MySQLdb的cursor的包装，增加dictfetchone和dictfetchall接口
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def __build_dict(self, row):
        return dict(zip((col[0] for col in self.cursor.description), row))

    def dictfetchone(self):
        row = self.cursor.fetchone()
        return row and self.__build_dict(row)

    def dictfetchall(self):
        return [self.__build_dict(row) for row in self.cursor.fetchall()]

    def __getattr__(self, item):
        return getattr(self.cursor, item)


class ConnectionWrapper(object):
    def __init__(self, connection):
        self.connection = connection

    def cursor(self, cursor=None):
        cursor = self.connection.cursor(cursor)
        return CursorWrapper(cursor)

    def __getattr__(self, item):
        return getattr(self.connection, item)


class ConnectionHandler(object):
    def __init__(self):
        self._databases = DATABASES
        self._connections = local()

    def __getitem__(self, alias):
        if hasattr(self._connections, alias):
            return getattr(self._connections, alias)

        setting = self._databases[alias]
        setting.setdefault("charset", "utf8")
        conn = ConnectionWrapper(db_connect(**setting))
        conn.autocommit(True)

        setattr(self._connections, alias, conn)
        return conn

    def __setitem__(self, key, value):
        setattr(self._connections, key, value)

    def __delitem__(self, key):
        delattr(self._connections, key)

    def __iter__(self):
        return iter(self._databases)


_connects = ConnectionHandler()


def get_db_conn():
    try:
        conn = _connects["local"]
        conn.ping(True)
        return conn
    except DB_Error:
        from traceback import print_exc
        print_exc()
        raise
