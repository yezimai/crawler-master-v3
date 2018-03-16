# -*- coding: utf-8 -*-

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListSoudhSpider(CompanySpider):
    name = "soudh"
    allowed_domains = ["soudh.com"]
    start_urls = ("http://www.soudh.com/city-602-" + str(i) + ".html" for i in range(1, 105))

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        spider_name = self.name
        response_url = response.url

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        text_strip = self.text_strip

        sel_list = response.xpath("//nobr/a/text()").extract()
        if not sel_list:
            self.notice_change("No data found!!!!! " + response_url)

        for name in sel_list:
            name = text_strip(name)
            if name_exists_func(name):
                continue
            record_name_func(name)

            item = CompanyItem()
            item["from_web"] = spider_name
            item["from_url"] = response_url
            item["area"] = "shenzhen"
            item["name"] = name
            yield item
