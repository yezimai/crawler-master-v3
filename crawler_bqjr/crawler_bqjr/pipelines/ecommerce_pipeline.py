# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from crawler_bqjr.items.ecommerce_items import ZhiFuBaoItem, JDItem, TaoBaoItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_ECOMMERCE_DB, \
    MONGO_ZHIFUBAO_COLLECTIONS, MONGO_JD_COLLECTIONS, MONGO_TAOBAO_COLLECTIONS
from data_storage.db_settings import RABBITMQ_QUEUE


class EcommercePipeline(MongoPipelineUtils):
    def __init__(self, item_class, mongo_db, mongo_collection, mq_queue):
        super().__init__(item_class, mongo_db, mongo_collection)
        self.rabbitmq_queue_name = mq_queue

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"], })
        result = mongo_instance.insertOne(insert_dict)

        # 发送mq
        self.rabbitmq_sender(self.rabbitmq_queue_name, insert_dict)

        return str(result.inserted_id)


class ZhiFuBaoPipeline(EcommercePipeline):
    """
    支付宝管道类
    """

    def __init__(self):
        super().__init__(ZhiFuBaoItem, MONGO_ECOMMERCE_DB,
                         MONGO_ZHIFUBAO_COLLECTIONS, RABBITMQ_QUEUE["alipay"])


class TAOBAOPipeline(EcommercePipeline):
    """
    淘宝管道类
    """

    def __init__(self):
        super().__init__(TaoBaoItem, MONGO_ECOMMERCE_DB,
                         MONGO_TAOBAO_COLLECTIONS, RABBITMQ_QUEUE["taobao"])


class JDPipeline(EcommercePipeline):
    """
    京东管道类
    """

    def __init__(self):
        super().__init__(JDItem, MONGO_ECOMMERCE_DB,
                         MONGO_JD_COLLECTIONS, RABBITMQ_QUEUE["jingdong"])
