# -*- coding: utf-8 -*-

from crawler_bqjr.items.shebao_items import SheBaoItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_5XIAN1JIN_DB, MONGO_SHEBAO_COLLECTIONS


class SheBaoPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(SheBaoItem, MONGO_5XIAN1JIN_DB, MONGO_SHEBAO_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"],
                                         "city": insert_dict["city"],
                                         })
        result = mongo_instance.insertOne(insert_dict)

        return str(result.inserted_id)
