# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List99114Spider(CompanySpider):
    name = "99114"
    allowed_domains = ["99114.com"]
    start_urls = ["http://shop.99114.com/list/area/101119103_1"]

    custom_settings = {
        'DOWNLOAD_DELAY': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        urljoin = response.urljoin
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@id='footerTop']/ul/li/a")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("strong/text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            url = urljoin(url) + "/ch10"
            yield Request(url, callback=parse_company)

        url = response.xpath("//div[@class='pagination']/form"
                             "/a[contains(text(),'下一页')]/@href").extract_first()
        if url:
            url = urljoin(url)
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        name = response.xpath("//p[@class='companyname']/span/text()").extract_first()
        if not name:
            return

        item["name"] = name
        text_join = self.text_join
        info_dict = {}
        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='comBorder']//p"))
                             if "：" in info and "暂未填写" not in info)
            item["main_products"] = info_dict.get("主营业务")
        except Exception:
            self.logger.exception("")

        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract()).replace("\xa0", "")
                                 for sel in response.xpath("//li[contains(@class,'addIntro')]"))
                             if "：" in info and "暂未填写" not in info)
            item["address"] = info_dict.get("地址")
        except Exception:
            self.logger.exception("")

        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='companytxt']/p"))
                             if "暂未填写" not in info)
            item["company_form"] = info_dict.get("企业类型")
            item["registered_capital"] = info_dict.get("注册资本")
            item["legal_person"] = info_dict.get("法定代表人")
            item["main_products"] = info_dict.get("主要供应产品") or item["main_products"]
            item["main_area"] = info_dict.get("主要面向地区")
            item["employee_scale"] = info_dict.get("员工数量")
            item["annual_turnover"] = info_dict.get("年营业额")
        except Exception:
            self.logger.exception("")

        yield item
