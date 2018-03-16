# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListZhaoshang100Spider(CompanySpider):
    name = "zhaoshang100"
    allowed_domains = ["zhaoshang100.com"]
    start_urls = ["http://www.zhaoshang100.com/minglu246/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 60,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        urljoin = response.urljoin
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//a[@class='proName02']")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            url = urljoin(url)
            yield Request(url, callback=parse_company)

        url = response.xpath("//div[@id='pager']/a[text()='下页']/@href").extract_first()
        if url:
            url = urljoin(url)
            yield Request(url, self.parse)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join

        item["name"] = response.xpath("//div[@class='coInfos']/h1/text()").extract_first()
        item["summary"] = response.xpath("//div[@class='coInfos']/div[@id='ciTxt']/text()").extract_first()

        try:
            info_dict = dict((info[0], text_join(info[1:])) for info
                             in (sel.xpath(".//text()").extract() for sel
                                 in response.xpath("//div[@class='aiMain']/ul/li")))
            item["name"] = info_dict.get("公司名称") or item["name"]
            item["address"] = info_dict.get("公司地址")
            item["main_products"] = info_dict.get("主营业务")
            item["mobile"] = info_dict.get("联系手机")
            item["telephone"] = info_dict.get("联系电话")
        except Exception:
            self.logger.exception("")

        yield item
