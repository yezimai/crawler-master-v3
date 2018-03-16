# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from re import compile as re_compile

from crawler_bqjr.items.emailbill_items import EmailBillItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_EMAILBILL_DB, MONGO_EMAILBILL_COLLECTIONS


class EmailBillPipeline(MongoPipelineUtils):
    """
    邮箱账单管道类
    """

    def __init__(self):
        super().__init__(EmailBillItem, MONGO_EMAILBILL_DB, MONGO_EMAILBILL_COLLECTIONS)
        self.date_replace_pattern = re_compile(r"[: /\\\-]")

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"],
                                         })
        result = mongo_instance.insertOne(insert_dict)
        # 发送mq
        self.rabbitmq_sender("CRAWL_EMAIL_QUEUE", insert_dict)
        return str(result.inserted_id)
