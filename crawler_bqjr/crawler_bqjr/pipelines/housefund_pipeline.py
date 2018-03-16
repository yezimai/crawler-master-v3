# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.housefund_items import HousefundItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_5XIAN1JIN_DB, MONGO_HOUSEFUND_COLLECTIONS


class HousefundPipeline(MongoPipelineUtils):
    """
    公积金管道类
    """

    def __init__(self):
        super().__init__(HousefundItem, MONGO_5XIAN1JIN_DB, MONGO_HOUSEFUND_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"],
                                         "city": insert_dict["city"]})
        result = mongo_instance.insertOne(insert_dict)

        return str(result.inserted_id)
