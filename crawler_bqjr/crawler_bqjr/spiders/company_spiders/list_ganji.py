# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListGanjiSpider(CompanySpider):
    name = "ganji"
    allowed_domains = ["ganji.com"]
    start_urls = ["http://sz.ganji.com/gongsi/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 30,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        spider_name = self.name
        response_url = response.url

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@class='com-list-2']/table/tr/td/a")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response_url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("@title").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            item = CompanyItem()
            item["from_web"] = spider_name
            item["area"] = "shenzhen"
            item["name"] = name

            url = sel.xpath("@href").extract_first("")
            request = Request(url, callback=parse_company)
            request.meta["item"] = item
            yield request

        url = response.xpath("//ul[contains(@class,'pageLink')]//a[@class='next']/@href").extract_first()
        if url:
            url = response.urljoin(url)
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        meta = response.meta
        item = meta["item"]
        item["from_url"] = response.url

        text_join = self.text_join

        item["name"] = response.xpath("//div[@class='c-title']/h1/text()").extract_first() or item["name"]
        item["summary"] = self.text_join(response.xpath("//p[@id='company_description']"
                                                        "/a/@data-description").extract(), "\n")

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='c-introduce']/ul/li")))
            item["name"] = info_dict.get("公司名称") or item["name"]
            item["address"] = info_dict.get("公司地址")
            item["company_form"] = info_dict.get("公司类型")
            item["employee_scale"] = info_dict.get("公司规模")
            item["industry"] = info_dict.get("公司行业")
        except Exception:
            self.logger.exception("")

        yield item
