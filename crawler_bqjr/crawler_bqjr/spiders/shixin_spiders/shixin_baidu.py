# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import product, chain
from random import randint
from re import compile as re_compile
from traceback import print_exc
from urllib.parse import urlencode, parse_qs, unquote, urlsplit

from scrapy import Request

from crawler_bqjr.items.shixin_items import ShixinDetailItem
from crawler_bqjr.spider_class import NameSearchSpider, RecordSearchedSpider
from crawler_bqjr.utils import get_js_time
from data_storage.db_settings import MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS, \
    MONGO_SHIXIN_DETAIL_COLLECTIONS, MONGO_ZHIXING_DETAIL_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_DESCENDING
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

SSDB_SHIXIN_ID_HSET_NAME = "spider_shixin_id_hset"


def record_all_shixin_id():
    ssdb_conn = get_ssdb_conn()
    ssdb_conn.hclear(SSDB_SHIXIN_ID_HSET_NAME)

    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_DETAIL_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"from_web": 1, "link_id": 1, "_id": 0}):
            try:
                the_id = item["from_web"] + "_" + str(item["link_id"])
                ssdb_conn.hset(SSDB_SHIXIN_ID_HSET_NAME, the_id, "")
            except Exception:
                print_exc()

    ssdb_conn.close()

    print("record_all_shixin_id done.")


def count_shixin_id(mongo_instance):
    id_set = set()
    company_count = 0
    for i in mongo_instance.getAll(fields={"_id": 0, "name": 1, "id": 1, "legal_person": 1}):
        try:
            key = i["name"] + i["id"]
            if key not in id_set:
                id_set.add(key)
                if i["legal_person"]:
                    company_count += 1
        except Exception:
            print_exc()
    total_count = len(id_set)
    print("Shixin total_count[%d], person_count[%d], company_count[%d]"
          % (total_count, total_count - company_count, company_count))
    del id_set


def del_duplicate_shixin():
    file_code_set = set()
    duplicate_ids = []
    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_DETAIL_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"from_web": 1, "link_id": 1},
                                          sort=[("_id", MONGO_DESCENDING)]):
            try:
                file_code = item["from_web"] + "_" + str(item["link_id"])
                if file_code not in file_code_set:
                    file_code_set.add(file_code)
                else:
                    duplicate_ids.append(item["_id"])
            except Exception:
                print_exc()
        del file_code_set

        for the_id in duplicate_ids:
            mongo_instance.deleteOne(filter={"_id": the_id})

        count_shixin_id(mongo_instance)

    print("Del %d of duplicated item in collection[%s]"
          % (len(duplicate_ids), MONGO_SHIXIN_DETAIL_COLLECTIONS))
    del duplicate_ids


class ShixinBaiduSpider(NameSearchSpider, RecordSearchedSpider):
    name = "shixin_baidu"
    allowed_domains = ["baidu.com"]
    start_urls = ["https://www.baidu.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 0.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_SHIXIN_ID_HSET_NAME, **kwargs)
        self.good_words = set()
        self.good_names = set()
        self.link_id_pattern = re_compile(r"(\d+)$")
        self.from_web = "0"

    def _get_search_request(self, name, pn):
        the_time = get_js_time()
        form_data = {"resource_id": "6899",
                     "query": "失信被执行人名单",
                     "cardNum": "",
                     "iname": name,
                     "pn": str(pn),
                     "rn": "10",
                     "ie": "utf-8",
                     "oe": "utf-8",
                     "format": "json",
                     't': the_time,
                     '_': int(the_time) + 2,
                     'callback': "jQuery1102" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                     }

        return Request("https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?"
                       + urlencode(form_data), self.parse_search, dont_filter=True)

    def get_search_name_request(self):
        _get_search_request = self._get_search_request

        # 名字搜索
        for word in set(chain(self.first_names, self.most_words)):
            yield _get_search_request(word, 0)

    def get_search_good_word_request(self):
        _get_search_request = self._get_search_request

        filter_set = set(w for w in self.citys if len(w) == 2)
        filter_set.update(w for w in self.first_names if len(w) == 2)

        # 常用字两字排列
        good_words = self.good_words.copy()
        for word1, word2 in product(good_words, good_words):
            name = word1 + word2
            if name not in filter_set:
                filter_set.add(name)
                yield _get_search_request(name, 0)

        if self.good_names:
            good_first_name = set(self.first_names) & set(self.good_words)
            good_names = self.good_names.copy()
            for word1, word2 in product(good_first_name, good_names):
                name = word1 + word2
                filter_set.add(name)
                yield _get_search_request(name, 0)

            good_name_word = set(self.good_words) - set(self.first_names)
            for word1, word2 in product(good_names, good_name_word):
                name = word1 + word2
                filter_set.add(name)
                yield _get_search_request(name, 0)

        # 法院公布名单
        with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS) as mongo_instance:
            name_set = {i["name"] for i in mongo_instance.getAll(fields={"name": 1, "_id": 0})
                        if len(i["name"]) < 5}

        # 被执行人名单
        with MongoDB(MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS) as mongo_instance:
            name_set.update(i["name"] for i in mongo_instance.getAll(fields={"name": 1, "_id": 0})
                            if len(i["name"]) < 5)

        name_set -= filter_set
        self.logger.info("name_set length: %d" % len(name_set))
        for name in name_set:
            yield _get_search_request(name, 0)

    def get_search_rare_word_request(self):
        _get_search_request = self._get_search_request

        # 名字搜索
        for word in self.rare_words:
            yield _get_search_request(word, 0)

    def get_search_company_request(self):
        _get_search_request = self._get_search_request

        # 省份、主要城市
        for city in self.citys:
            yield _get_search_request(city, 0)

    def get_page_request(self):
        parse = self.parse
        for i in range(101):
            the_time = get_js_time()
            form_data = {"resource_id": "6899",
                         "query": "全国法院失信被执行人名单",
                         "pn": str(i * 10),
                         "rn": "10",
                         "ie": "utf-8",
                         "oe": "utf-8",
                         "format": "json",
                         't': the_time,
                         '_': int(the_time) + 2,
                         'callback': "jQuery1102" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                         }

            yield Request("https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?"
                          + urlencode(form_data), parse, dont_filter=True)

    def start_requests(self):
        yield from self.get_page_request()
        yield from self.get_search_name_request()
        yield from self.get_search_good_word_request()
        # yield from self.get_search_company_request()
        yield from self.get_search_rare_word_request()

    def parse_items(self, datas):
        from_web = self.from_web
        link_id_pattern = self.link_id_pattern
        update_time = datetime.now()
        for data in datas:
            name = data.get("iname")
            if not name:
                continue

            try:
                link_id = int(link_id_pattern.search(data.get("loc")).group(1))
            except Exception:
                link_id = randint(1E10, 1E11)

            link_name = from_web + "_" + str(link_id)
            if self.is_search_name_exists(link_name):
                continue
            self.record_search_name(link_name)

            item = ShixinDetailItem()
            item["from_web"] = from_web
            item["link_id"] = link_id
            item["update_time"] = update_time
            item["name"] = name
            item["id"] = data.get("cardNum")
            item["province"] = data.get("areaName")
            item["file_code"] = data.get("caseCode")
            item["execution_court"] = data.get("courtName")
            item["fulfill_situation"] = data.get("disruptTypeName")
            item["duty"] = data.get("duty")
            item["execution_file_code"] = data.get("gistId")
            item["adjudge_court"] = data.get("gistUnit")
            item["fulfill_status"] = data.get("performance") or data.get("performancePart")
            item["publish_date"] = data.get("publishDate")
            item["on_file_date"] = data.get("regDate")

            for k, v in item.items():
                if v is None:
                    self.logger.error("Data(%s)表格异常：(%s)" % (data, k))
                    break

            item["legal_person"] = data.get("businessEntity")
            item["sex"] = data.get("sexy")
            item["age"] = data.get("age")

            yield item

    def parse(self, response):
        try:
            text = response.text

            if '"status":"0"' in text:  # 成功
                data = json_loads(text)["data"]
                if data:
                    yield from self.parse_items(data[0]["result"])
                else:
                    self.logger.error("No Data for URL(%s)" % unquote(response.url))
            else:
                self.logger.error("百度_API---访问失败")
        except Exception:
            self.logger.exception("百度_API---访问异常")

    def parse_search(self, response):
        text = response.text
        try:
            if '"status":"0"' in text:  # 成功
                data = json_loads(text)["data"]
                form_data = parse_qs(urlsplit(response.url).query)
                pn = int(form_data["pn"][0])
                name = form_data["iname"][0]
                if data:
                    yield from self.parse_items(data[0]["result"])
                    if pn < 1000:
                        yield self._get_search_request(name, pn + 10)
                    elif len(name) == 1:
                        self.good_words.add(name)
                        self.logger.info("Good Word(%s)" % name)
                    elif len(name) > 1 and name not in self.citys:
                        self.good_names.add(name)
                        self.logger.info("Good Name(%s)" % name)
                else:
                    self.logger.warning("No Data for URL(%s)" % unquote(response.url))
            else:
                self.logger.error("百度_API---访问失败，(%s)" % text)
        except Exception:
            self.logger.exception("百度_API---访问异常，(%s)" % response.url)


if __name__ == '__main__':
    with MongoDB(MONGO_SHIXIN_DB, MONGO_SHIXIN_DETAIL_COLLECTIONS) as mongo_instance:
        count_shixin_id(mongo_instance)
