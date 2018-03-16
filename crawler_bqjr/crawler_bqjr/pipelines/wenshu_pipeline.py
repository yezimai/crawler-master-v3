# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from os import path as os_path, makedirs

from crawler_bqjr.items.wenshu_items import WenshuItem, ChinacourtItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from crawler_bqjr.settings import WENSHU_DIR
from data_storage.db_settings import MONGO_WENSHU_DB, \
    MONGO_CHINACOURT_COLLECTIONS, MONGO_WENSHU_COLLECTIONS, SSDB_WENSHU_ID_HSET
from data_storage.ssdb_db import get_ssdb_conn


class WenshuPipeline(MongoPipelineUtils):
    """
    裁判文书管道类
    """

    def __init__(self):
        super().__init__(WenshuItem, MONGO_WENSHU_DB, MONGO_WENSHU_COLLECTIONS)
        self.ssdb_conn = get_ssdb_conn()

    def write_item_to_db(self, item):
        # 保存文书内容
        if "html" in item:
            html = item.pop("html")
            pub_date = item["pub_date"].split("-")
            save_dir = os_path.join(WENSHU_DIR, item['case_type'],
                                    pub_date[0], pub_date[1], pub_date[2])
            if not os_path.exists(save_dir):
                makedirs(save_dir)
            filename = os_path.join(save_dir, item['file_id'] + ".html")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            item["html_file"] = filename

        insert_dict = self.strip_insert_item(item)
        result = self.mongo_instance.insertOne(insert_dict)

        # 保存和信息都成功才把file_id记录到ssdb
        self.record_wenshu_id(item["file_id"])

        return str(result.inserted_id)

    def record_wenshu_id(self, file_id):
        try:
            self.ssdb_conn.hset(SSDB_WENSHU_ID_HSET, file_id, "")
        except Exception:
            return


class ChinacourtPipeline(MongoPipelineUtils):
    """
    中国法院管道类
    """

    def __init__(self):
        super().__init__(ChinacourtItem, MONGO_WENSHU_DB, MONGO_CHINACOURT_COLLECTIONS)
