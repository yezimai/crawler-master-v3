# -*- coding: utf-8 -*-

from re import compile as re_compile, S as re_S
# from random import choice
from traceback import print_exc

from scrapy.http import FormRequest

from crawler_bqjr.items.shixin_items import ShixinListItem
from crawler_bqjr.spider_class import RecordSearchedSpider
from crawler_bqjr.utils import sleep_to_tomorrow
from data_storage.db_settings import MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_DESCENDING
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

SSDB_SHIXIN_LIST_ID_HSET_NAME = "spider_shixin_list_id_hset"


def record_all_shixinlist_id():
    ssdb_conn = get_ssdb_conn()
    ssdb_conn.hclear(SSDB_SHIXIN_LIST_ID_HSET_NAME)

    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"id": 1, "name": 1, "_id": 0}):
            try:
                the_id = item["name"] + item["id"]
                ssdb_conn.hset(SSDB_SHIXIN_LIST_ID_HSET_NAME, the_id, "")
            except Exception:
                print_exc()

    ssdb_conn.close()

    print("record_all_shixin_list_id done.")


def del_duplicate_shixinlist():
    id_set = set()
    duplicate_ids = []
    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"id": 1, "name": 1},
                                          sort=[("_id", MONGO_DESCENDING)]):
            try:
                the_id = item["name"] + item["id"]
                if the_id not in id_set:
                    id_set.add(the_id)
                else:
                    duplicate_ids.append(item["_id"])
            except Exception:
                print_exc()
        del id_set

        for the_id in duplicate_ids:
            mongo_instance.deleteOne(filter={"_id": the_id})

    print("Del %d of duplicated item in collection[%s]"
          % (len(duplicate_ids), MONGO_SHIXIN_LIST_COLLECTIONS))
    del duplicate_ids


class ShixinKuaichaSpider(RecordSearchedSpider):
    """
    http://www.kuaicha.info/lawMobile/js/area.js
    地区查询条件
    """
    name = "shixin_kuaicha"
    allowed_domains = ["kuaicha.info"]
    start_urls = ["http://www.kuaicha.info/lawMobile/js/area.js"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_SHIXIN_LIST_ID_HSET_NAME, **kwargs)
        # self.proxy_list = ["113.128.91.0:48888", "182.126.179.6:8118"]
        # self.proxy = choice(self.proxy_list)
        self.post_url = "http://www.kuaicha.info/lawMobile/findExecutedPersonListByArea.action"
        self.post_data = {
            "accessId": "",
            "province": "四川",
            "city": "成都市",
            "area": "青羊区",
            "startIndex": "0",
            "pageSize": "10000",
            "appkey": "sdfasdfsfwqerewqrweqWRWER"
        }
        self.replace_pattern = re_compile(r"/\*(.*?)\*/", re_S)
        self.area_regex = re_compile(r"var provinceList=(.*)", re_S)
        self.query_condition = []
        self.current_condition = None

    def parse(self, response):
        area_result = self.area_regex.search(response.text).group(1).replace("//", "#").replace(";", "")
        area_result = self.replace_pattern.sub("", area_result)
        area_result = area_result.replace('name', '"name"') \
            .replace('cityList', '"cityList"').replace('areaList', '"areaList"')

        area_result = json_loads(area_result)
        query_condition = self.query_condition
        for result in reversed(area_result):
            province = result["name"]
            for cityList in reversed(result["cityList"]):
                condition = dict()
                city = cityList["name"]
                condition["province"] = province
                condition["city"] = city
                condition["area"] = ""
                if not len(cityList["areaList"]):
                    query_condition.append(condition)
                else:
                    for area in reversed(cityList["areaList"]):
                        area_condition = dict()
                        area_condition["area"] = area
                        query_condition.append(dict(condition, **area_condition))

        # 根据地区条件组合查询
        query = query_condition.pop()
        self.post_data["province"] = query["province"]
        self.post_data["city"] = query["city"]
        self.post_data["area"] = query["area"]
        self.current_condition = query
        request = FormRequest(self.post_url, self.parse_detail, formdata=self.post_data)
        # self.set_proxy(request)
        yield request

    def parse_detail(self, response):
        result = json_loads(response.text)
        if result["ErrorMsg"] == "成功":
            for info in result["data"]["areaList"]:
                name = info["name"]
                the_id = info["cardNum"]

                key = name + the_id
                if self.is_search_name_exists(key):
                    continue
                self.record_search_name(key)

                item = ShixinListItem()
                item["from_web"] = "kuaicha"
                item["name"] = name
                item["id"] = the_id
                yield item
        elif result["ErrorMsg"] == "已达到每日查询次数上限":
            # self.proxy = choice(self.proxy_list)
            self.query_condition.append(self.current_condition)
            self.logger.info("今日查询次数达到上限，明日再查")
            sleep_to_tomorrow()

        if self.query_condition:
            query = self.query_condition.pop()
            self.post_data["province"] = query["province"]
            self.post_data["city"] = query["city"]
            self.post_data["area"] = query["area"]
            self.current_condition = query
            request = FormRequest(self.post_url, self.parse_detail, formdata=self.post_data)
            # self.set_proxy(request)
            yield request
        else:
            self.logger.info("所有条件查询结束")

    # def set_proxy(self, request):
    #     # 设置代理
    #     self.logger.info("current proxy->%s" % self.proxy)
    #     request.meta["proxy"] = "http://" + self.proxy
