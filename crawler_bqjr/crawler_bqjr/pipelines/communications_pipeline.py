# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.communications_items import UserCommunicationInfoItem, YournumberItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_COMMUNICATIONS_DB, MONGO_COMMUNICATIONS_COLLECTIONS, \
    MONGO_YOURNUMBER_COLLECTIONS
from data_storage.db_settings import RABBITMQ_QUEUE


class UserCommunicationInfoPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(UserCommunicationInfoItem, MONGO_COMMUNICATIONS_DB,
                         MONGO_COMMUNICATIONS_COLLECTIONS)
        self.rabbitmq_queue_name = RABBITMQ_QUEUE["yunyingshang"]

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"],
                                         "brand": insert_dict["brand"]})
        result = mongo_instance.insertOne(insert_dict)

        # 发送mq
        self.rabbitmq_sender(self.rabbitmq_queue_name, insert_dict)

        return str(result.inserted_id)


class YournumberPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(YournumberItem, MONGO_COMMUNICATIONS_DB,
                         MONGO_YOURNUMBER_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"phone": insert_dict["phone"], })
        result = mongo_instance.insertOne(insert_dict)

        return str(result.inserted_id)
