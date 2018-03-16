# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep
from traceback import print_exc

from crawler_bqjr.spider_class import LoggingClosedSpider, RecordSearchedSpider, NoticeChangeSpider
from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS, \
    MONGO_COMPANY_DETAIL_COLLECTIONS, MONGO_COMPANY_DETAIL2_COLLECTIONS, \
    MONGO_COMPANY_DETAIL3_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_DESCENDING, ObjectId
from data_storage.ssdb_db import get_ssdb_conn

SSDB_COMPANY_QUEUE_NAME = "sz_company_queue"
SSDB_COMPANY_HSET_NAME = "spider_company_name_hset"
BLANK_CHARS = "\u3000\u2002\xa0 \f\n\r\t\v"


def get_one_company(mongo_instance, ssdb_conn):
    while True:
        _id = ssdb_conn.qpop_front(SSDB_COMPANY_QUEUE_NAME)
        if _id is not None:
            a_company = mongo_instance.getOne(filter={"_id": ObjectId(_id)})
            if a_company is not None:
                a_company.pop("_id")
                return a_company
        else:
            return None


def push_new_company_id(ssdb_conn, _id):
    ssdb_conn.qpush_back(SSDB_COMPANY_QUEUE_NAME, _id)


def push_all_company_id():
    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL_COLLECTIONS) as mongo_instance:
        finished = set(item["name"] for item in mongo_instance.getAll(fields={"name": 1, "_id": 0}))

    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS) as mongo_instance:
        finished.update(item["name"] for item in mongo_instance.getAll(fields={"name": 1, "_id": 0}))

    ssdb_conn = get_ssdb_conn()
    ssdb_conn.qclear(SSDB_COMPANY_QUEUE_NAME)

    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"name": 1, "_id": 1},
                                          filter={"$or": [{"area": "shenzhen"},
                                                          {"name": re_compile(r".*深圳.*")}]},
                                          sort=[("_id", MONGO_DESCENDING)]):
            name = item["name"]
            if name not in finished:
                ssdb_conn.qpush_back(SSDB_COMPANY_QUEUE_NAME, str(item["_id"]))

    ssdb_conn.close()
    del finished

    print("push_all_company_id done.")


def record_all_company_name():
    ssdb_conn = get_ssdb_conn()
    ssdb_conn.hclear(SSDB_COMPANY_HSET_NAME)

    with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"name": 1, "_id": 0}):
            try:
                # 将爬取过的公司名单加入SSDB，用于避免重复爬取
                name = item["name"]
                if len(name) < 60:
                    ssdb_conn.hset(SSDB_COMPANY_HSET_NAME, name, "")
            except Exception:
                print_exc()

    ssdb_conn.close()

    print("record_all_company_name done.")


def _del_duplicate_company(collections=MONGO_COMPANY_DETAIL_COLLECTIONS):
    name_set = set()
    duplicate_ids = []
    with MongoDB(MONGO_COMPANY_DB, collections) as mongo_instance:
        for item in mongo_instance.getAll(fields={"name": 1}, sort=[("_id", MONGO_DESCENDING)]):
            name = item["name"]
            if name not in name_set:
                name_set.add(name)
            else:
                duplicate_ids.append(item["_id"])

        for the_id in duplicate_ids:
            mongo_instance.deleteOne(filter={"_id": the_id})

    del name_set

    print("Del %d of duplicated item in collection[%s]" % (len(duplicate_ids), collections))


def del_duplicate_company():
    _del_duplicate_company(MONGO_COMPANY_COLLECTIONS)
    _del_duplicate_company(MONGO_COMPANY_DETAIL_COLLECTIONS)
    _del_duplicate_company(MONGO_COMPANY_DETAIL2_COLLECTIONS)
    _del_duplicate_company(MONGO_COMPANY_DETAIL3_COLLECTIONS)


class CompanySpider(LoggingClosedSpider, RecordSearchedSpider, NoticeChangeSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_COMPANY_HSET_NAME, **kwargs)

    def text_strip(self, text):
        return text.strip(BLANK_CHARS)

    def text_join(self, text_iterable, link_str=""):
        text_list = (i.strip(BLANK_CHARS) for i in text_iterable)
        return link_str.join(i for i in text_list if i)

    def do_nothing(self, response):
        sleep(11)
