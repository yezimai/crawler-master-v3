# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListQincaiSpider(CompanySpider):
    name = "qincai"
    allowed_domains = ["qincai.net"]
    start_urls = ["http://www.qincai.net/hohohoyuoh/show_crawl_nav.html"]

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

        sel_list = response.xpath("//div[contains(@class,'itemlist')]/h2/a")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response_url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
            except Exception:
                continue
            if len(name) > 50:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            item = CompanyItem()
            item["from_web"] = spider_name
            item["from_url"] = response_url
            item["area"] = "shenzhen"
            item["name"] = name
            yield item

        url = response.xpath("//div[@class='pagelist']/a[text()='后页']/@href").extract_first()
        if url:
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)
