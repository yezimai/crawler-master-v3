# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListQiyeSpider(CompanySpider):
    name = "qiye"
    allowed_domains = ["qiye.net"]
    start_urls = ["http://www.qiye.net/company_pr001016"]

    custom_settings = {
        'DOWNLOAD_DELAY': 300,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        spider_name = self.name
        urljoin = response.urljoin
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company_contact = self.parse_company_contact
        text_strip = self.text_strip
        text_join = self.text_join

        sel_list = response.xpath("//ul[@class='companyList']/li")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for li in sel_list:
            name_a = li.xpath("div[@class='tit']/strong/a")
            try:
                name = text_strip(name_a.xpath("text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            item = CompanyItem()
            item["from_web"] = spider_name
            item["area"] = "guangdong"
            item["name"] = name

            try:
                info_dict = dict(info.split("：", maxsplit=1) for info
                                 in (text_join(sel.xpath(".//text()").extract()) for sel in li.xpath("dl[1]/dd")))
                item["main_products"] = info_dict.get("主营产品")
                item["address"] = info_dict.get("企业地址")
            except Exception:
                self.logger.exception("")

            url = name_a.xpath("@href").extract_first("")
            url = urljoin(url) + "-contact"
            request = Request(url, callback=parse_company_contact)
            request.meta["item"] = item
            yield request

        url = response.xpath("//div[@class='matpages']/a[text()='下一页']/@href").extract_first()
        if url:
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company_contact(self, response):
        meta = response.meta
        item = meta["item"]
        item["from_url"] = response.url

        text_join = self.text_join

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//ul[@class='contactbox']/li")))
            item["address"] = info_dict.get("公司地址")
            item["telephone"] = info_dict.get("电话号码")
            item["mobile"] = info_dict.get("手机号码")
        except Exception:
            self.logger.exception("")

        yield Request(response.url.replace("-contact", "-company"), self.parse_company_introduce, meta=meta)

    def parse_company_introduce(self, response):
        item = response.meta["item"]
        item["summary"] = self.text_join(response.xpath("//div[@class='text']/text()").extract(), "\n")
        item["name"] = response.xpath("//div[@class='companyname']/text()").extract_first()

        yield item
