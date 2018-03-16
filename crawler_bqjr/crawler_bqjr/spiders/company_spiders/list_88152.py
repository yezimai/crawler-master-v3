# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List88152Spider(CompanySpider):
    name = "88152"
    allowed_domains = ["88152.com"]
    start_urls = ["http://www.88152.com/shenzhen/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 15,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@class='company']/a")
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

        href = response.xpath("//div[@id='pageLink']/a[text()='下一页»']/@href").extract_first()
        if href and not href.endswith("/./"):
            url = response.urljoin(href)
            yield Request(url, self.parse, dont_filter=True)
        else:
            yield Request(self.start_urls[0], self.parse, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join

        name = response.xpath("//div[@class='companyname']/h1/text()").extract_first()
        if name:  # 模板1
            item["name"] = name
            item["summary"] = text_join((text_join(sel.xpath(".//text()").extract())
                                         for sel in response.xpath("//div[contains(@class,'shopcontent')]/p")),
                                        "\n")

            try:
                info_dict = dict(info.split("：", maxsplit=1) for info
                                 in (text_join(sel.xpath(".//text()").extract())
                                     for sel in response.xpath("//div[contains(@class,'contact')]/ul/li")))
                item["address"] = info_dict.get("公司地址")
                item["telephone"] = info_dict.get("公司传真")
            except Exception:
                self.logger.exception("")

            yield item
        else:  # 模板2
            name = response.xpath("//div[@id='companyname']/h1/a/text()").extract_first()
            if name:
                item["name"] = name
                request = Request(response.url.replace("/shop/", "/contact/"), self.parse_company_contact)
                request.meta["item"] = item
                yield request
            else:
                self.logger.error("Unknown template: " + response.url)
                return

    def parse_company_contact(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            info_dict = dict(tr.xpath("td/text()").extract() for tr in response.xpath("//table/tr"))
            item["address"] = info_dict.get("地　址：")
            item["telephone"] = info_dict.get("传　真：")
        except Exception:
            self.logger.exception("")

        yield Request(response.url.replace("/contact/", "/introduce/"),
                      self.parse_company_introduce, meta=meta)

    def parse_company_introduce(self, response):
        meta = response.meta
        item = meta["item"]

        text_join = self.text_join

        item["summary"] = text_join((text_join(sel.xpath(".//text()").extract()) for sel
                                     in response.xpath("//div[contains(@class,'intro-content')]/p")), "\n")

        yield item
