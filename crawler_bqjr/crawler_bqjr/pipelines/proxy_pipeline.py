# -*- coding: utf-8 -*-

from scrapy.exceptions import DropItem

from crawler_bqjr.items.proxy_items import ProxyItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_PROXY_DB, MONGO_PROXY_COLLECTIONS


class ProxyPipeline(MongoPipelineUtils):
    def __init__(self):
        super().__init__(ProxyItem, MONGO_PROXY_DB, MONGO_PROXY_COLLECTIONS)
        cursor = self.mongo_instance.getAll(fields={"ip": 1, "port": 1, "_id": 0})
        self.proxy_set = {(item["ip"], item["port"]) for item in cursor}
        self.new_proxy_count = 0

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        insert_dict["response_time"] = -1
        insert_dict["fail_times"] = 0
        insert_dict["ok_times"] = 0
        insert_dict["quality"] = 0
        self.mongo_instance.insertOne(insert_dict)

    def process_item(self, item, spider):
        if isinstance(item, ProxyItem):
            port = item["port"]
            port = int(port) if port else 80
            item["port"] = port

            proxy_addr = (item["ip"], port)
            if proxy_addr not in self.proxy_set:
                self.proxy_set.add(proxy_addr)
                self.new_proxy_count += 1
                try:
                    self.write_item_to_db(item)
                except Exception:
                    spider.logger.exception("%s write item(%s) to db error: " % (spider.name, item))
                raise DropItem("Processing proxy item done.")
            else:
                raise DropItem("Duplicate proxy item found.")
        else:
            return item
