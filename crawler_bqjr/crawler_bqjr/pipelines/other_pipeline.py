# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from hashlib import md5
from os import path as os_path
from urllib.request import Request, urlopen

from crawler_bqjr.items.other_items import YishangItem, GpsspgItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from crawler_bqjr.settings import IMAGE_DIR, USER_AGENT
from data_storage.db_settings import MONGO_OTHER_DB, MONGO_SHOP_COLLECTIONS, \
    MONGO_ADDRESS_COLLECTIONS
from data_storage.mysql_db import get_db_conn


#################################################################
# 商户
#################################################################
class YishangPipeline(MongoPipelineUtils):
    """
    亿商公益管道类
    """

    def __init__(self):
        super().__init__(YishangItem, MONGO_OTHER_DB, MONGO_SHOP_COLLECTIONS)

    def write_item_to_db(self, item):
        # 保存商户图片
        pic = item.get('pic', "").strip()
        if pic:
            pic_hash = md5(pic.encode()).hexdigest() + os_path.splitext(pic)[1]
            filename = os_path.join(IMAGE_DIR, pic_hash)
            try:
                request = Request(url=pic, headers={'User-Agent': USER_AGENT})
                pic_content = urlopen(request).read()
                with open(filename, 'wb') as f:
                    f.write(pic_content)
            except Exception:
                pass
            item["pic"] = pic_hash

        insert_dict = self.strip_insert_item(item)
        result = self.mongo_instance.insertOne(insert_dict)
        return str(result.inserted_id)


class GpsspgPipeline(MongoPipelineUtils):
    """
    地址转换经纬度管道类
    """

    def __init__(self):
        super().__init__(GpsspgItem, MONGO_OTHER_DB, MONGO_ADDRESS_COLLECTIONS)
        # self.mysql_conn = get_db_conn()

    # def write_item_to_mysql(self, item):
    #     insert_dict = dict(item)
    #
    #     base_sql = "INSERT INTO"
    #     try:
    #         self.mysql_conn.cursor().execute(base_sql)
    #     except Exception:
    #         pass

    def write_item_to_db(self, item):
        insert_dict = dict(item)
        # self.mongo_instance.deleteOne(filter={"id": insert_dict["id"], "address": insert_dict["address"], })
        result = self.mongo_instance.insertOne(insert_dict)
        return str(result.inserted_id)
