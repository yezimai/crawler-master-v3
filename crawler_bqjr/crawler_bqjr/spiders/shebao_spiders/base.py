# -*- coding: utf-8 -*-

from crawler_bqjr.items.shebao_items import SheBaoItem
from crawler_bqjr.spider_class import AccountSpider


class ShebaoSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=SheBaoItem, **kwargs)

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        city = account_info["city"]
        self.logger.critical("The city is:%s" % city)
        request.meta["item"]["city"] = city
        return request
