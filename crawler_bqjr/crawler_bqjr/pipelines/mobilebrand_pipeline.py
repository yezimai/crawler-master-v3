# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from datetime import datetime

from crawler_bqjr.items.mobilebrand_items import CnmoItem, ZolAccessoryItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_MOBILEBRAND_COLLECTIONS, MONGO_MOBILEBRAND_DB, \
    MONGO_MOBILEACCESSORY_COLLECTIONS


#################################################################
# 手机品牌大全
#################################################################
class CnmoPipeline(MongoPipelineUtils):
    """
    中国手机大全管道类
    """

    def __init__(self):
        super().__init__(CnmoItem, MONGO_MOBILEBRAND_DB, MONGO_MOBILEBRAND_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        db_item_info = mongo_instance.getOne(filter={"product_url": insert_dict['product_url']},
                                             fields={"product_price": 1, "for_sale": 1, "detail_info": 1})
        if not db_item_info:
            result = mongo_instance.insertOne(insert_dict)
            return str(result.inserted_id)
        else:
            _id = db_item_info['_id']
            update_time = datetime.now()
            if db_item_info.get('product_price') != insert_dict.get('product_price'):
                updater = {"$set": {"product_price": insert_dict.get('product_price'),
                                    "detail_info": insert_dict.get('detail_info'),
                                    "update_time": update_time,
                                    }
                           }
                mongo_instance.updateOne({"_id": _id}, updater)

            if db_item_info.get('for_sale') != insert_dict.get('for_sale'):
                updater = {"$set": {"for_sale": insert_dict.get('for_sale'),
                                    "detail_info": insert_dict.get('detail_info'),
                                    "update_time": update_time,
                                    }
                           }
                mongo_instance.updateOne({"_id": _id}, updater)

            if "detail_info" not in db_item_info:
                updater = {"$set": {"detail_info": insert_dict.get('detail_info'),
                                    }
                           }
                mongo_instance.updateOne({"_id": _id}, updater)

            return str(_id)


class ZolAccessoryPipeline(MongoPipelineUtils):
    """
    ZOL的手机配件相关
    """

    def __init__(self):
        super().__init__(ZolAccessoryItem, MONGO_MOBILEBRAND_DB, MONGO_MOBILEACCESSORY_COLLECTIONS)

    def write_item_to_db(self, item):
        insert_dict = self.strip_insert_item(item)
        mongo_instance = self.mongo_instance
        db_item_info = mongo_instance.getOne(filter={"name": insert_dict['name']},
                                             fields={"price": 1, "status": 1})
        if not db_item_info:
            result = mongo_instance.insertOne(insert_dict)
            return str(result.inserted_id)
        else:
            _id = db_item_info['_id']
            update_time = datetime.now()
            if db_item_info.get('price') != insert_dict.get('price'):
                updater = {"$set": {"price": insert_dict.get('price'),
                                    "update_time": update_time,
                                    }
                           }
                mongo_instance.updateOne({"_id": _id}, updater)

            if db_item_info.get('status') != insert_dict.get('status'):
                updater = {"$set": {"status": insert_dict.get('status'),
                                    "update_time": update_time,
                                    }
                           }
                mongo_instance.updateOne({"_id": _id}, updater)

            return str(_id)
