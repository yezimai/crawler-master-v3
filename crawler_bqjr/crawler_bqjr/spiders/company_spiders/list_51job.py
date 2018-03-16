# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List51jobSpider(CompanySpider):
    name = "51job"
    allowed_domains = ["51job.com"]
    start_urls = ["http://jobs.51job.com/shenzhen"]

    custom_settings = {
        'DOWNLOAD_DELAY': 10,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//p[@class='info']/a[@class='name']")
        # if not sel_list:
        #     self.notice_change("No data found!!!!! " + response.url)

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

        url = response.xpath("//div[@id='cppageno']/ul/li/a[text()='下一页']/@href").extract_first()
        if url:
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join

        item["name"] = response.xpath("//h1/text()").extract_first()
        item["address"] = text_join(response.xpath("//p[@class='fp']/text()").extract(), " ")
        item["summary"] = text_join(response.xpath("//div[@class='con_msg']//p/text()").extract(), "\n")
        try:
            item["company_form"], item["employee_scale"], item["industry"] \
                = response.xpath("//p[@class='ltype']/text()").extract_first("").split("|")
        except ValueError:
            item["company_form"], item["employee_scale"], item["industry"] = "", "", ""

        yield item
