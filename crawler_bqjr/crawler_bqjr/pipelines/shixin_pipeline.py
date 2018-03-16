# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.shixin_items import ShixinListItem, ShixinDetailItem, \
    ZhixingDetailItem, P2PItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from crawler_bqjr.spiders.shixin_spiders.zhixing_court import SSDB_ZHIXING_ID_HSET_NAME
from data_storage.db_settings import MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS, \
    MONGO_SHIXIN_DETAIL_COLLECTIONS, MONGO_ZHIXING_DETAIL_COLLECTIONS, \
    MONGO_P2P_DEADBEAT_COLLECTIONS
from data_storage.ssdb_db import get_ssdb_conn


#################################################################
# 失信
#################################################################
class ShixinListPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(ShixinListItem, MONGO_SHIXIN_DB, MONGO_SHIXIN_LIST_COLLECTIONS)


class ShixinDetailPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(ShixinDetailItem, MONGO_SHIXIN_DB, MONGO_SHIXIN_DETAIL_COLLECTIONS)


class ZhixingDetailPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(ZhixingDetailItem, MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS)
        self.ssdb_conn = get_ssdb_conn()

    def write_item_to_db(self, item):
        self.ssdb_conn.hset(SSDB_ZHIXING_ID_HSET_NAME, item["link_id"], "")
        return super().write_item_to_db(item)


class P2PPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(P2PItem, MONGO_SHIXIN_DB, MONGO_P2P_DEADBEAT_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        has_result = mongo_instance.getOne(filter={"id": insert_dict["id"],
                                                   "from_web": insert_dict["from_web"]},
                                           fields={"_id": 1})
        if not has_result:
            result = mongo_instance.insertOne(insert_dict)
            return str(result.inserted_id)
        else:
            return str(has_result["_id"])
