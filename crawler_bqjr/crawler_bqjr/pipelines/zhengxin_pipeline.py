# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.zhengxin_items import ZhengxinPbcItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_ZHENGXIN_DB, MONGO_ZHENGXIN_PBC_COLLECTIONS
from data_storage.db_settings import RABBITMQ_QUEUE


#################################################################
# 征信
#################################################################
class ZhengxinPbcPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(ZhengxinPbcItem, MONGO_ZHENGXIN_DB, MONGO_ZHENGXIN_PBC_COLLECTIONS)
        self.rabbitmq_queue_name = RABBITMQ_QUEUE["zhengxin"]

    def write_item_to_db(self, item):
        insert_dict = dict(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"]})
        result = mongo_instance.insertOne(insert_dict)

        # 发送mq
        self.rabbitmq_sender(self.rabbitmq_queue_name, insert_dict)

        return str(result.inserted_id)
