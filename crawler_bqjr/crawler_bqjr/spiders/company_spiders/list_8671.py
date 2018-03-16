# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List8671Spider(CompanySpider):
    name = "8671"
    allowed_domains = ["8671.net"]
    start_urls = ["http://guangdong.8671.net/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 60,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        url_set = set(response.xpath("//a[text()='更多']/@href").extract())
        url_set.update(response.xpath("//div[@id='dCatalogueBox']/ul/li/a/@href").extract())
        parse_company_name = self.parse_company_name

        if not url_set:
            self.notice_change("No href found!!!!! " + response.url)

        for url in url_set:
            yield Request(url, callback=parse_company_name, dont_filter=True)

    def parse_company_name(self, response):
        spider_name = self.name
        response_url = response.url

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        text_strip = self.text_strip

        sel_list = response.xpath("//td[@class='tItem']")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response_url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("a/text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            item = CompanyItem()
            item["from_web"] = spider_name
            item["from_url"] = response_url
            item["area"] = "guangdong"
            item["name"] = name
            infos = sel.xpath(".//text()").extract()
            item["address"] = infos[-1] if infos else None
            yield item

        url = response.xpath("//a/b[text()='下一页']/../@href").extract_first()
        if url:
            yield Request(url, self.parse_company_name, dont_filter=True)
