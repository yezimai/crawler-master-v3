# -*- coding: utf-8 -*-

from base64 import b64encode
from gzip import compress
from hashlib import md5
from os import path as os_path

from Crypto.Cipher.AES import new as AES_new, MODE_EAX
from scrapy.exceptions import DropItem

from crawler_bqjr.settings import HTML_DIR
from crawler_bqjr.spiders.company_spiders.base import BLANK_CHARS
from data_storage.db_settings import RABBITMQ_EXCHANGE
from data_storage.mongo_db import MongoDB
from data_storage.rabbitmq import RabbitmqSender
from global_utils import json_dumps

none_type = type(None)


class MongoPipelineUtils(object):
    def __init__(self, item_class, mongo_db, mongo_collection):
        self.item_class = item_class
        self.mongo_instance = MongoDB(mongo_db, mongo_collection)
        self.key = b"zhegemiyaobeininadaoyemeiyouyong"

    def encrypt(self, text):
        key = self.key
        cryptor = AES_new(key, MODE_EAX, key)
        return b64encode(cryptor.encrypt(text.encode()))

    def strip_insert_item(self, item):
        return {k: (v.strip(BLANK_CHARS) if isinstance(v, str) else v)
                for k, v in item.items()}

    def write_item_to_db(self, item):
        # 保存html源文为文件
        if "html" in item:
            html = item.pop("html")
            html_hash = md5(html.encode()).hexdigest()
            filename = os_path.join(HTML_DIR, html_hash + ".html")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            item["html_file"] = html_hash

        insert_dict = self.strip_insert_item(item)
        result = self.mongo_instance.insertOne(insert_dict)
        return str(result.inserted_id)

    def process_item(self, item, spider):
        item_class = self.item_class
        if type(item) is item_class:
            try:
                if "password" in item:
                    item["password"] = self.encrypt(item["password"])
                self.write_item_to_db(item)
            except Exception:
                spider.logger.exception("%s write item(%s) to db error: " % (spider.name, item))
            raise DropItem("Processing %s item done." % item_class.__name__)
        else:
            return item

    def all_data_2_string(self, data_dict):
        new_dict = {}

        for k, v in data_dict:
            if type(v) in [str, none_type]:
                data = v
            elif isinstance(v, dict):
                data = self.all_data_2_string(v)
            elif type(v) in [list, tuple]:
                data = [self.all_data_2_string(i) for i in v]
            elif isinstance(v, bytes):
                data = v.decode()
            else:
                data = str(v)
            new_dict[k] = data

        return new_dict

    def rabbitmq_sender(self, queue, item_dict):
        """
        对保存mq的内容进行gzip压缩和base64位编码
        :param queue: 队列名
        :return:
        """
        del item_dict["_id"]
        content = b64encode(compress(json_dumps(item_dict).encode("utf-8"))).decode("utf-8")
        with RabbitmqSender(queue=queue,exchange=RABBITMQ_EXCHANGE, durable=True) as rs:
            rs.send(content)
