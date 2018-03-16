# -*- coding: utf-8 -*-

from re import compile as re_compile

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spiders.company_spiders.base import CompanySpider
from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_DESCENDING, ObjectId
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

SSDB_TIANYANCHA_QUEUE_NAME = "tianyancha_queue"


def push_new_tianyancha_company_id(ssdb_conn, _id):
    ssdb_conn.qpush_back(SSDB_TIANYANCHA_QUEUE_NAME, _id)


def push_all_tianyancha_company_id():
    ssdb_conn = get_ssdb_conn()
    ssdb_conn.qclear(SSDB_TIANYANCHA_QUEUE_NAME)

    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"_id": 1},
                                          filter={"search_url": re_compile(r"^http://www\.tianyancha\.com/company/")},
                                          sort=[("_id", MONGO_DESCENDING)]):
            ssdb_conn.qpush_back(SSDB_TIANYANCHA_QUEUE_NAME, str(item["_id"]))

    ssdb_conn.close()

    print("push_all_tianyancha_company_id done.")


class DetailTianyanchaSpider(CompanySpider):
    name = "tianyancha"
    allowed_domains = ["tianyancha.com"]
    start_urls = ["http://www.tianyancha.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_instance = MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS)

    def _get_one_company(self):
        while True:
            _id = self.ssdb_conn.qpop_front(SSDB_TIANYANCHA_QUEUE_NAME)
            if _id is not None:
                a_company = self.mongo_instance.getOne(filter={"_id": ObjectId(_id)})
                if a_company is not None:
                    a_company.pop("_id")
                    return a_company
            else:
                return None

    def start_requests(self):
        parse_company_name = self.parse_company_name
        _get_one_company = self._get_one_company
        tianyancha_id_pattern = re_compile(r"(\d+)$")
        while True:
            a_company = _get_one_company()
            if a_company is not None:
                try:
                    tianyancha_id = tianyancha_id_pattern.search(a_company["search_url"]).group(1)
                    a_company["tianyancha_id"] = tianyancha_id
                    request = Request("http://www.tianyancha.com/near/s.json?id=%s" % tianyancha_id,
                                      parse_company_name)
                    request.meta["company_other_info"] = a_company
                    yield request
                except Exception:
                    self.logger.error("No tianyancha_id url(%s)" % a_company["search_url"])
            else:
                yield Request(DO_NOTHING_URL, self.do_nothing,
                              errback=self.do_nothing, dont_filter=True)

    def parse(self, response):
        meta = response.meta
        tianyancha_id = meta["company_other_info"]["tianyancha_id"]
        yield Request("http://www.tianyancha.com/company/%d.json" % tianyancha_id,
                      self.parse_company, meta=response.meta)

    def parse_company_name(self, response):
        try:
            text = response.text

            if '"state":"ok"' in text:  # 成功
                spider_name = self.name
                name_exists_func = self.is_search_name_exists
                record_name_func = self.record_search_name
                datas = json_loads(text)["data"]
                if "items" in datas:
                    for data in datas["items"]:
                        name = data["name"]
                        if not name:
                            continue

                        if name_exists_func(name):
                            continue
                        record_name_func(name)

                        item = CompanyItem()
                        item["from_web"] = spider_name
                        item["from_url"] = "http://www.tianyancha.com/company/" + data["id"]
                        item["area"] = "shenzhen"
                        item["name"] = name
                        yield item
            else:
                self.logger.warning("天眼查---查找相关公司失败，URL(%s)" % response.url)
        except Exception:
            self.logger.exception("天眼查---查找相关公司异常，URL(%s)" % response.url)

    def parse_company(self, response):
        try:
            text = response.text

            if '"state":"ok"' in text:  # 成功
                datas = json_loads(text)
                pass
            else:
                self.logger.error("天眼查---搜索公司失败，URL(%s)" % response.url)
        except Exception:
            self.logger.exception("天眼查---搜索公司异常，URL(%s)" % response.url)
