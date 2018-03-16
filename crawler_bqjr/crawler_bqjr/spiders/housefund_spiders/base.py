# -*- coding: utf-8 -*-

from crawler_bqjr.items.housefund_items import HousefundItem
from crawler_bqjr.spider_class import AccountSpider


class HousefundSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=HousefundItem, **kwargs)

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        city = account_info["city"]
        self.logger.critical("The city is:%s" % city)
        request.meta["item"]["city"] = city
        return request
