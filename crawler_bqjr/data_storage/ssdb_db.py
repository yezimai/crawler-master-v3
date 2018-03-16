# -*- coding: UTF-8 -*-

from threading import local

from data_storage.db_settings import SSDB_SETTINGS
from data_storage.ssdb import Client as SsdbClient


class ConnectionHandler(object):
    def __init__(self):
        self._databases = SSDB_SETTINGS
        self._connections = local()

    def __getitem__(self, alias):
        if hasattr(self._connections, alias):
            return getattr(self._connections, alias)

        setting = self._databases[alias]
        conn = SsdbClient(**setting)

        setattr(self._connections, alias, conn)
        return conn

    def __setitem__(self, key, value):
        setattr(self._connections, key, value)

    def __delitem__(self, key):
        delattr(self._connections, key)

    def __iter__(self):
        return iter(self._databases)


_connects = ConnectionHandler()


def get_ssdb_conn():
    try:
        conn = _connects["local"]
    except Exception:
        from traceback import print_exc
        print_exc()
        raise
    else:
        return conn


if __name__ == '__main__':
    conn = get_ssdb_conn()

    print(dir(conn))
    conn.hset("HM_IP_COUNT", "KEY_SAME_IP_USE_COUNT", 1)
    conn.hincr("HM_IP_COUNT", "KEY_SAME_IP_USE_COUNT", 1)
    print(conn.hget("HM_IP_COUNT", "KEY_SAME_IP_USE_COUNT"))

    print("".center(100, "-"))
    conn.set("test_!@#$", "set test_!@#$")
    conn.set("test_!@#$2", "set test_!@#$")
    conn.set("test_!@#$3", "set test_!@#$")
    print("after set:", conn.get("test_!@#$"))
    conn.delete("test_!@#$")
    conn.multi_del("test_!@#$2",
                   "test_!@#$3",
                   "test_!@#$4",
                   )
    print("after delete:", conn.get("test_!@#$"))

    print("qpop empty:", conn.qpop_front("中文_queue"))
    conn.qpush_back("中文_queue", '测试中文')
    print("qpop after push:", conn.qpop_front("中文_queue"))
    print("qpop after push again:", conn.qpop_front("中文_queue"))

    print("".center(100, "-"))
    conn.hset("test_hset", "123", "")
    print("after hset:", conn.hget("test_hset", "123"))
    print("hexists:", conn.hexists("test_hset", "123"))
    print("not hexists:", conn.hexists("test_hset", "bucunzai"))
    print("hdel hexists:", conn.hdel("test_hset", "123"))
    print("hdel not hexists:", conn.hdel("test_hset", "bucunzai"))
    print("hget not hexists:", conn.hget("test_hset", "bucunzai"))

    print("".center(100, "-"))
    print("sz_company_queue size:", conn.qsize("sz_company_queue"))
    print("tianyancha_queue size:", conn.qsize("tianyancha_queue"))
    print("spider_company_name_hset size:", conn.hsize("spider_company_name_hset"))

    print("".center(100, "-"))
    print("spider_shixin_list_id_hset size:", conn.hsize("spider_shixin_list_id_hset"))
    print("spider_shixin_id_hset size:", conn.hsize("spider_shixin_id_hset"))
    print("spider_zhixing_id_hset size:", conn.hsize("spider_zhixing_id_hset"))
    print("spider_zhixing_name_hset size:", conn.hsize("spider_zhixing_name_hset"))
    print("spider_dlm_name_hset size:", conn.hsize("spider_dlm_name_hset"))
