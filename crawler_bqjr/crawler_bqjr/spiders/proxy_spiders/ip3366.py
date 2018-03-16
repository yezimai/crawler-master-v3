# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import NoticeChangeSpider


class Ip3366Spider(NoticeChangeSpider):
    name = "ip3366"
    allowed_domains = ["ip3366.net"]
    start_urls = ["http://www.ip3366.net/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anonymous_level_dict = {"高匿代理IP": AnonymousLevel.HIGH,
                                     }
        self.scheme_type_dict = {"HTTP": SchemeType.HTTP,
                                 "HTTPS": SchemeType.HTTPS,
                                 }
        self.support_method_dict = {"GET, POST": SupportMethod.GET_OR_POST,
                                    }

    def parse(self, response):
        anonymous_level_dict = self.anonymous_level_dict
        scheme_type_dict = self.scheme_type_dict
        support_method_dict = self.support_method_dict

        anonymous_level_default = AnonymousLevel.LOW
        scheme_type_default = SchemeType.HTTP
        support_method_default = SupportMethod.GET

        sel_list = response.xpath("//div[@id='list']/table/tbody/tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            item = ProxyItem()
            tds = [td.xpath("text()").extract_first("") for td in sel.xpath("td")]
            ip, port, level, type_str, support_method, location, *_ = tds

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_dict.get(type_str, support_method_default)
            item['location'] = location.strip()
            yield item

        href = response.xpath("//div[@id='listnav']/ul/a[text()='下一页']/@href").extract_first()
        if href and not href.endswith("/./"):
            url = response.urljoin(href)
            yield Request(url, self.parse)
