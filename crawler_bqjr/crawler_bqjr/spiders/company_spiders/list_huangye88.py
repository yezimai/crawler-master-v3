# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListHuangye88Spider(CompanySpider):
    name = "huangye88"
    allowed_domains = ["huangye88.com"]
    start_urls = ["http://b2b.huangye88.com/shenzhen/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 0.6,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        parse_company_name = self.parse_company_name

        sel_list = response.xpath("//div[@class='main']/div/"
                                  "div[starts-with(@id,'subcatlisting_')]/ul/li/a/@href").extract()
        if not sel_list:
            self.notice_change("No href found!!!!! " + response.url)

        for url in sel_list:
            yield Request(url, callback=parse_company_name, dont_filter=True)

    def parse_company_name(self, response):
        spider_name = self.name
        response_url = response.url

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//form[@id='jubao']/dl/dt/h4/a")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response_url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
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
            request = Request(url + "company_detail.html", callback=parse_company)
            request.meta["item"] = item
            yield request

        url = response.xpath("//div[contains(@class,'page_tag')]/a[text()='下一页']/@href").extract_first()
        if url:
            yield Request(url, self.parse_company_name, dont_filter=True)

    def parse_company(self, response):
        meta = response.meta
        item = meta["item"]
        item["from_url"] = response.url

        item["name"] = response.xpath("//h1[@class='big']/text()").extract_first() or item["name"]
        item["summary"] = self.text_join(response.xpath("//p[@class='txt']/text()").extract(), "\n")

        info_dict = {}
        try:
            info_dict.update(sel.xpath(".//text()").extract() for sel
                             in response.xpath("//table[@cellspacing='1']/tr"))
            item["main_area"] = info_dict.get("主营地区")
            item["business_period"] = info_dict.get("经营期限")
            item["check_date"] = info_dict.get("最近年检时间")
            item["annual_turnover"] = info_dict.get("年营业额")
            item["annual_export_volume"] = info_dict.get("年营出口额")
        except Exception:
            self.logger.exception("")

        text_join = self.text_join

        try:
            info_dict.update(i.split("：", maxsplit=1) for i in
                             (text_join(sel.xpath(".//text()").extract()) for sel
                              in response.xpath("//ul[contains(@class,'l-txt')]/li")) if "：" in i)
            item["mobile"] = info_dict.get("手机")
            item["telephone"] = info_dict.get("电话") or info_dict.get("公司电话")
            item["address"] = info_dict.get("公司地址")
        except Exception:
            self.logger.exception("")

        try:
            info_dict.update(i.split("：", maxsplit=1) for i in
                             (text_join(sel.xpath(".//text()").extract()) for sel
                              in response.xpath("//ul[@class='con-txt']/li")) if "：" in i)
            item["legal_person"] = info_dict.get("企业法人")
            item["found_date"] = info_dict.get("成立时间")
            item["registered_capital"] = info_dict.get("注册资金")
            item["employee_scale"] = info_dict.get("员工人数")
            item["main_products"] = info_dict.get("主营产品")
        except Exception:
            self.logger.exception("")

        yield item
