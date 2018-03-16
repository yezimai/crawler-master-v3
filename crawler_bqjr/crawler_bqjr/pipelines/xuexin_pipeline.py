# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from hashlib import md5
from os import path as os_path

from crawler_bqjr.items.userinfo_items import XuexinItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from crawler_bqjr.settings import IMAGE_DIR, IMAGE_HTTP_SUFFIX
from data_storage.db_settings import MONGO_XUEXIN_DB, MONGO_XUEXIN_COLLECTIONS
from data_storage.db_settings import RABBITMQ_QUEUE


class XuexinPipeline(MongoPipelineUtils):
    """
    学信管道类
    """

    def __init__(self):
        super().__init__(XuexinItem, MONGO_XUEXIN_DB, MONGO_XUEXIN_COLLECTIONS)
        self.rabbitmq_queue_name = RABBITMQ_QUEUE["xuexin"]

    def write_item_to_db(self, item):
        # 保存毕业证照片
        for value in item.values():
            if isinstance(value, list):
                for v in value:
                    if 'photo' in v:
                        photo_data = v["photo"]
                        photo_hash = md5(photo_data).hexdigest() + '.jpg'
                        filename = os_path.join(IMAGE_DIR, photo_hash)
                        with open(filename, 'wb') as f:
                            f.write(photo_data)
                        v["photo"] = photo_hash

        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"]})
        result = mongo_instance.insertOne(insert_dict)

        # 发送mq
        for xueli in insert_dict['xueli']:
            if 'photo' in xueli:
                xueli['photo'] = IMAGE_HTTP_SUFFIX + xueli['photo']
        self.rabbitmq_sender(self.rabbitmq_queue_name, insert_dict)

        return str(result.inserted_id)
