# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from re import compile as re_compile

from crawler_bqjr.items.bank_items import BankItem
from crawler_bqjr.pipelines.base import MongoPipelineUtils
from data_storage.db_settings import MONGO_BANK_DB, MONGO_BANK_COLLECTIONS


#################################################################
# 银行交易记录
#################################################################
class BankPipeline(MongoPipelineUtils):
    """
    银行交易记录管道类
    """

    def __init__(self):
        super().__init__(BankItem, MONGO_BANK_DB, MONGO_BANK_COLLECTIONS)
        self.date_replace_pattern = re_compile(r"[: /\\\-]")

    def format_item(self, item):
        copy_one = {}
        date_replace_pattern = self.date_replace_pattern
        money_keys = ["trade_amount", "trade_balance", "trade_income", "trade_outcome"]

        for k, v in item.items():
            if "trade_records" == k:
                for d in v:
                    d["trade_date"] = date_replace_pattern.sub("", d["trade_date"])
                    for key in money_keys:
                        try:
                            d[key] = d[key].replace(",", "")
                        except Exception:
                            pass
            elif "balance" == k:
                try:
                    v = v.replace(",", "")
                except Exception:
                    pass

            copy_one[k] = v

        return copy_one

    def write_item_to_db(self, item):
        insert_dict = self.format_item(item)
        mongo_instance = self.mongo_instance
        mongo_instance.deleteOne(filter={"username": insert_dict["username"],
                                         "bank": insert_dict["bank"],
                                         })
        result = mongo_instance.insertOne(insert_dict)

        return str(result.inserted_id)
