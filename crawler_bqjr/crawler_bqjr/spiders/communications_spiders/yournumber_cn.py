# -*- coding: utf-8 -*-

from scrapy.http import Request

from crawler_bqjr.items.communications_items import YournumberItem
from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.spiders.communications_spiders.phone_num_util import get_phone_info_from_yournumber


class YournumberSpider(AccountSpider):
    name = "yournumber"
    allowed_domains = ["yournumber.cn"]
    start_urls = ["http://www.yournumber.cn"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def get_account_request(self, account_info):
        """
        account_info["phone"]: '{"phone": ["15908143404", "18732184025", "13712881884", "17742941147", "053258690396"]}'
        :param account_info:
        :return:
        """
        request = Request(self._start_url_, self.parse, dont_filter=True, errback=self.err_callback)
        item = YournumberItem()
        item["phone"] = account_info["phone"]
        request.meta["item"] = item
        return request

    def parse(self, response):
        item = response.meta["item"]
        phone_list = item["phone"]
        for phone in phone_list:
            self.logger.info("Get phone: %s" % phone)
            result = get_phone_info_from_yournumber(phone)
            item["phone"] = phone
            item["result"] = result
            yield item
        yield self.get_next_request()
