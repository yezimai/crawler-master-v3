# -*- coding: utf-8 -*-

from re import compile as re_compile

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListYouboySpider(CompanySpider):
    name = "youboy"
    allowed_domains = ["youboy.com"]
    start_urls = ["http://qiye.youboy.com/pro1_1.html"]

    custom_settings = {
        'DOWNLOAD_DELAY': 7,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_num_pattern = re_compile(r"#page=(\d+)")

    def parse(self, response):
        yield from self.parse_company_name(response)

        href = response.xpath("//div[@id='digg']/a[text()='尾页']/@href").extract_first()
        if href:
            total_page = int(self.page_num_pattern.search(href).group(1))
            parse_company_name = self.parse_company_name
            for i in range(2, total_page + 1):
                url = "http://qiye.youboy.com/pro1_" + str(i) + ".html"
                yield Request(url, parse_company_name)

    def parse_company_name(self, response):
        spider_name = self.name
        response_url = response.url

        urljoin = response.urljoin
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//li[@class='dqscontit']/a")
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
            item["area"] = "guangdong"
            item["name"] = name

            url = sel.xpath("@href").extract_first("")
            url = urljoin(url)
            request = Request(url, callback=parse_company)
            request.meta["item"] = item
            yield request

    def parse_company(self, response):
        meta = response.meta
        item = meta["item"]
        item["from_url"] = response.url

        text_join = self.text_join

        info_dict = {}
        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='gsinfocon']/ul")))
            item["industry"] = info_dict.get("主营行业")
            item["main_products"] = info_dict.get("主营产品/服务")
        except Exception:
            self.logger.exception("")

        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='gslxcon']/ul")))
            item["address"] = info_dict.get("公司地址")
            item["telephone"] = info_dict.get("联系电话") or info_dict.get("公司传真")
            item["mobile"] = info_dict.get("手机")
        except Exception:
            self.logger.exception("")

        yield item
