# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List56YeSpider(CompanySpider):
    name = "56ye"
    allowed_domains = ["56ye.net"]
    start_urls = ["http://qiye.56ye.net/search.php?areaid=233"]

    custom_settings = {
        'DOWNLOAD_DELAY': 50,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//li[@class='sup-name']/a[not(@rel)]")
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

            url = sel.xpath("@href").extract_first("") + "introduce/"
            yield Request(url, callback=parse_company)

        url = response.xpath("//div[@class='pages']/a[contains(text(),'下一页')]/@href").extract_first("")
        if "&page=" in url:
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        item["name"] = response.xpath("//div[@class='head']/div/strong/text()").extract_first()
        main_products = response.xpath("//div[@class='head']/div/h4/text()").extract_first("")
        item["main_products"] = main_products.split("：", maxsplit=1)[-1]
        item["summary"] = self.text_join(response.xpath("//table[@cellspacing='3']/tr/td//text()").extract(),
                                         "\n")

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in response.xpath("//div[@class='qy_body']//li/text()").extract() if "：" in info)
            item["company_form"] = info_dict.get("公司类型")
            item["found_date"] = info_dict.get("成立时间")
            item["employee_scale"] = info_dict.get("公司规模")
            item["registered_capital"] = info_dict.get("注册资本")
            item["address"] = info_dict.get("地址")
            item["mobile"] = info_dict.get("手机")
            item["telephone"] = info_dict.get("电话") or info_dict.get("传真")
        except Exception:
            self.logger.exception("")

        yield item
