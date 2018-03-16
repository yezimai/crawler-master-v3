# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListCnlistSpider(CompanySpider):
    name = "cnlist"
    allowed_domains = ["cnlist.org"]
    start_urls = ["http://www.cnlist.org/shenzhen/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//ol[contains(@class,'firm_type_company')]/li/a")
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
            yield Request(url, callback=parse_company)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_strip = self.text_strip
        text_join = self.text_join

        item["name"] = response.xpath("//h1[@class='company_name']/text()").extract_first()
        item["summary"] = response.xpath("//div[@class='qynr']/p/text()").extract_first()

        info_dict = {}
        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath("*[starts-with(@class,'xg_cd')]/text()").extract())
                                 for sel in response.xpath("//div[contains(@class,'dpbj')]/ul/li/dl"))
                             if "资料不详" not in info)
            item["main_products"] = info_dict.get("主营产品")
        except Exception:
            self.logger.exception("")

        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath("*/text()").extract())
                                 for sel in response.xpath("//ul[contains(@class,'jtxx')]/li/dl"))
                             if "资料不详" not in info)
            item["mobile"] = info_dict.get("手机")
            item["telephone"] = info_dict.get("电话")
            item["address"] = info_dict.get("地址")
        except Exception:
            self.logger.exception("")

        for tr in response.xpath("//table[contains(@class,'xxtb')]/tbody/tr"):
            k1 = tr.xpath("td[1]/text()").extract_first("")
            v1 = tr.xpath("td[2]/text()").extract_first("")
            k2 = tr.xpath("td[3]/text()").extract_first("")
            v2 = tr.xpath("td[4]/text()").extract_first("")
            if v1 and '资料不详' not in v1:
                info_dict[text_strip(k1)] = v1
            if v2 and '资料不详' not in v2:
                info_dict[text_strip(k2)] = v2

        item["company_form"] = info_dict.get("企业类型")
        item["registered_capital"] = info_dict.get("注册资本")
        item["legal_person"] = info_dict.get("法定代表人/负责人")
        item["annual_turnover"] = info_dict.get("年营业额")
        item["employee_scale"] = info_dict.get("员工人数")

        yield item
