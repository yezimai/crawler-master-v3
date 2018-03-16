# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListZhaopinSpider(CompanySpider):
    name = "zhaopin"
    allowed_domains = ["company.zhaopin.com"]
    start_urls = ["http://company.zhaopin.com/shenzhen/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 500,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        spider_name = self.name
        response_url = response.url

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@class='jobs-list-box']/div/a")
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

            url = sel.xpath("@href").extract_first("")
            if "//special.zhaopin.com/" in url:
                item = CompanyItem()
                item["from_web"] = spider_name
                item["from_url"] = response_url
                item["area"] = "shenzhen"
                item["name"] = name
                yield item
            else:
                yield Request(url, callback=parse_company)

        url = response.xpath("//div[contains(@class,'pageBar')]/span/a[@title='下一页']/@href").extract_first()
        if url:
            url = response.urljoin(url)
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        item["name"] = response.xpath("//h1/text()").extract_first()
        item["company_form"] = response.xpath("//span[text()='公司性质：']/../../td[2]/span/text()").extract_first()
        item["employee_scale"] = response.xpath("//span[text()='公司规模：']/../../td[2]/span/text()").extract_first()
        item["industry"] = response.xpath("//span[text()='公司行业：']/../../td[2]/span/text()").extract_first()
        item["address"] = response.xpath("//span[text()='公司地址：']/../../td[2]/span/text()").extract_first()
        item["summary"] = self.text_join(response.xpath("//div[@class='company-content']//text()").extract())

        yield item
