# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListMakepoloSpider(CompanySpider):
    name = "makepolo"
    allowed_domains = ["company.makepolo.com"]
    start_urls = ("http://company.makepolo.com/guangdong/" + str(i) for i in range(1, 46156))

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//h2[@class='colist_item_title']/a")
        # if not sel_list:
        #     self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath('text()').extract_first())
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
        item["area"] = "guangdong"

        text_join = self.text_join

        item["name"] = response.xpath("//h1[@class='cd_title']/text()").extract_first()
        item["mobile"] = response.xpath("//span[@class='cd_mob']/text()").extract_first()
        item["telephone"] = response.xpath("//span[@class='cd_tel']/text()").extract_first("").strip("-")
        item["main_products"] = text_join(response.xpath("//span[@class='cd_major_item']/a/text()").extract(),
                                          ",")
        item["summary"] = response.xpath("//div[@class='cl_about']/text()").extract_first()

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in response.xpath("//div[contains(@class,'cd_param')]//span/text()").extract())
            item["name"] = info_dict.get("公司名称") or item["name"]
            item["legal_person"] = info_dict.get("法人代表")
            item["address"] = info_dict.get("公司地址")
            item["company_form"] = info_dict.get("公司类型")
            item["registered_capital"] = info_dict.get("注册资本", "").rstrip("万元")
            item["found_date"] = info_dict.get("成立时间")
            item["employee_scale"] = info_dict.get("员工人数")
            item["annual_turnover"] = info_dict.get("年营业额")
            item["annual_export_volume"] = info_dict.get("年出口额")
            item["main_area"] = info_dict.get("主要销售区域")
        except Exception:
            self.logger.exception("")

        yield item
