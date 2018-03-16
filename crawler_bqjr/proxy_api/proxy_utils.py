# -*- coding: utf-8 -*-

from random import choice as rand_choice

from requests import get as http_get

from crawler_bqjr.items.proxy_items import AnonymousLevel, SchemeType, SupportMethod, StableTime
from data_storage.db_settings import MONGO_PROXY_DB, MONGO_PROXY_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_ASCENDING
from proxy_api.proxy_check import HTTP_CHECK_URL_LIST, HTTPS_CHECK_URL_LIST


class NoProxyException(Exception):
    pass


class ProxyApi(object):
    def __init__(self):
        self.mongo_instance = MongoDB(MONGO_PROXY_DB, MONGO_PROXY_COLLECTIONS)  # 线程安全并带连接池
        self.scheme_filter_dict = {SchemeType.HTTP: {"$ne": SchemeType.HTTPS},
                                   SchemeType.HTTPS: {"$ne": SchemeType.HTTP},
                                   SchemeType.HTTP_OR_HTTPS: {"$eq": SchemeType.HTTP_OR_HTTPS},
                                   }
        self.method_filter_dict = {SupportMethod.GET: {"$ne": SupportMethod.POST},
                                   SupportMethod.POST: {"$ne": SupportMethod.GET},
                                   SupportMethod.GET_OR_POST: {"$eq": SupportMethod.GET_OR_POST},
                                   }
        self.good_quality_dict = {SchemeType.HTTP: {"$gte": len(HTTP_CHECK_URL_LIST)},
                                  SchemeType.HTTPS: {"$gte": len(HTTPS_CHECK_URL_LIST)},
                                  SchemeType.HTTP_OR_HTTPS: {"$gte": len(HTTPS_CHECK_URL_LIST)},
                                  }
        self.good_response_time_dict = {SchemeType.HTTP: {"$lt": 1, "$gte": 0},
                                        SchemeType.HTTPS: {"$lt": 3, "$gte": 0},
                                        SchemeType.HTTP_OR_HTTPS: {"$lt": 1, "$gte": 0},
                                        }

    def close(self):
        self.mongo_instance.close()

    def get_proxy_from_kuaidaili(self, stable_time=StableTime.MIN_10):
        try:
            url = "http://dps.kuaidaili.com/api/getdps/?" \
                  "orderid=959308673589451&num=50&sep=2&ut=" + str(stable_time)
            resp = http_get(url)
            if resp.status_code != 200:
                raise NoProxyException

            return resp.text.split()
        except Exception:
            from traceback import print_exc
            print_exc()
            raise NoProxyException

    def get_proxy_all(self, location=None, anonymous=AnonymousLevel.MIDDLE,
                      scheme=SchemeType.HTTP, method=SupportMethod.GET):
        the_filter = {"quality": self.good_quality_dict[scheme],
                      "response_time": self.good_response_time_dict[scheme],
                      # "anonymous_level": {"$lte": anonymous},
                      "scheme_type": self.scheme_filter_dict[scheme],
                      # "support_method": self.method_filter_dict[method],
                      }
        # if location:
        #     the_filter["location"] = re_compile(".*" + location + ".*")

        cursor = self.mongo_instance.getAll(filter=the_filter,
                                            fields={"ip": 1, "port": 1, "_id": 0},
                                            sort=[("response_time", MONGO_ASCENDING)])
        return [item["ip"] + ":" + str(item["port"]) for item in cursor]

    def get_proxy_one(self, location=None, anonymous=AnonymousLevel.MIDDLE, scheme=SchemeType.HTTP,
                      method=SupportMethod.GET, stable_time=StableTime.MIN_10):
        good_proxys = self.get_proxy_all(location, anonymous, scheme, method)
        if good_proxys:
            return rand_choice(good_proxys)
        else:
            raise NoProxyException


if __name__ == '__main__':
    a = ProxyApi()
    print(a.get_proxy_one(scheme=SchemeType.HTTPS))
