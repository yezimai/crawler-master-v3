# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import NoticeChangeSpider


class NianshaoSpider(NoticeChangeSpider):
    name = "nianshao"
    allowed_domains = ["nianshao.me"]
    start_urls = ("http://www.nianshao.me/?stype=" + str(i) for i in range(1, 15))

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anonymous_level_dict = {"高匿": AnonymousLevel.HIGH,
                                     }
        self.scheme_type_dict = {"HTTP": SchemeType.HTTP,
                                 "HTTPS": SchemeType.HTTPS,
                                 }

    def parse(self, response):
        yield from self.parse_proxy(response)

        total_page = response.xpath("//div[@id='listnav']/ul/strong/text()")
        if total_page:
            total_page = int(total_page.extract_first()[1:])
            father_url = response.url
            for i in range(2, min(101, total_page + 1)):
                url = father_url + "&page=" + str(i)
                yield Request(url, self.parse_proxy)

    def parse_proxy(self, response):
        anonymous_level_dict = self.anonymous_level_dict
        scheme_type_dict = self.scheme_type_dict

        anonymous_level_default = AnonymousLevel.LOW
        scheme_type_default = SchemeType.HTTP
        support_method_default = SupportMethod.GET

        sel_list = response.xpath("//table/tbody/tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            item = ProxyItem()
            tds = [td.xpath("text()").extract_first("") for td in sel.xpath("td")]
            ip, port, location, level, type_str, *_ = tds

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_default
            item['location'] = location.strip()
            yield item
