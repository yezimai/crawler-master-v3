# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List58Spider(CompanySpider):
    name = "58"
    allowed_domains = ["qy.58.com"]
    start_urls = ["http://qy.58.com/sz/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 200,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        parse_company_name = self.parse_company_name

        sel_list = response.xpath("//dl[@class='selIndCate']"
                                  "//a[starts-with(@href,'http://qy.58.com/sz_')]/@href").extract()
        if not sel_list:
            self.notice_change("No href found!!!!! " + response.url)

        for url in sel_list:
            yield Request(url, callback=parse_company_name, dont_filter=True)

    def parse_company_name(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@class='compList']/ul/li/span/a")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
            except Exception:
                continue
            if name == "独立经纪人":
                continue

            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            yield Request(url, callback=parse_company)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join

        item["name"] = response.xpath("//a[contains(@class,'businessName')]/@title").extract_first()
        item["summary"] = self.text_join(response.xpath("//div[@class='compIntro']/p/text()").extract(), "\n")

        info_dict = {}
        try:
            info_dict.update(i.split("：", maxsplit=1) for i in
                             (text_join(sel.xpath(".//text()").extract()) for sel
                              in response.xpath("//ul[contains(@class,'basicMsgListo')]/li")) if "：" in i)
            item["company_form"] = info_dict.get("公司性质")
            item["employee_scale"] = info_dict.get("公司规模")
            item["legal_person"] = info_dict.get("法人")
            item["industry"] = info_dict.get("公司行业")
            item["address"] = info_dict.get("公司地址", "").replace("查看地图", "")
        except Exception:
            self.logger.exception("")

        yield item
