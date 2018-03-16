# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.company_items import CompanyItem, \
    CompanyDetailItem, CompanyDetail2Item, CompanyGXSTDetailItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from crawler_bqjr.spiders.company_spiders.base import push_new_company_id
from crawler_bqjr.spiders.company_spiders.detail_tianyancha import push_new_tianyancha_company_id
from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS, \
    MONGO_COMPANY_DETAIL_COLLECTIONS, MONGO_COMPANY_DETAIL2_COLLECTIONS, MONGO_COMPANY_DETAIL3_COLLECTIONS
from data_storage.ssdb_db import get_ssdb_conn


class CompanyPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(CompanyItem, MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS)
        self.ssdb_conn = get_ssdb_conn()

    def write_item_to_db(self, item):
        name = item.get("name", "").strip()
        if not name:
            return

        insert_dict = self.strip_insert_item(item)
        result = self.mongo_instance.insertOne(insert_dict)
        _id = str(result.inserted_id)

        if insert_dict.get("area") == "shenzhen" or "深圳" in name:
            push_new_company_id(self.ssdb_conn, _id)

        return _id


class CompanyDetailPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(CompanyDetailItem, MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL_COLLECTIONS)


class CompanyDetail2Pipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(CompanyDetail2Item, MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS)
        self.ssdb_conn = get_ssdb_conn()

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        result = self.mongo_instance.insertOne(insert_dict)
        _id = str(result.inserted_id)

        search_url = item["search_url"]
        if search_url and ".tianyancha." == search_url[10:22]:
            push_new_tianyancha_company_id(self.ssdb_conn, _id)

        return _id


class GSXTDetailPipline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(CompanyGXSTDetailItem, MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL3_COLLECTIONS)
