# -*- coding: utf-8 -*-

from crawler_bqjr.items.bank_items import BankItem
from crawler_bqjr.spider_class import AccountSpider


class BankSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=BankItem, **kwargs)

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        bank = account_info["bank"]
        self.logger.critical("The bank is:%s" % bank)
        item = request.meta["item"]
        item["bank"] = bank
        item["trade_records"] = []
        return request

    def element_click_three_times(self, element):
        try:
            element.click()
            element.click()
            element.click()
        except Exception:
            pass
