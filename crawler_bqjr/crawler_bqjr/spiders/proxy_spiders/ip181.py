# -*- coding: utf-8 -*-

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import NoticeChangeSpider


class Ip181Spider(NoticeChangeSpider):
    name = "ip181"
    allowed_domains = ["ip181.com"]
    start_urls = ["http://www.ip181.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anonymous_level_dict = {"高匿": AnonymousLevel.HIGH,
                                     "普匿": AnonymousLevel.MIDDLE,
                                     "透明": AnonymousLevel.LOW,
                                     }
        self.scheme_type_dict = {"HTTP": SchemeType.HTTP,
                                 "HTTPS": SchemeType.HTTPS,
                                 "HTTP,HTTPS": SchemeType.HTTP_OR_HTTPS,
                                 }

    def parse(self, response):
        anonymous_level_dict = self.anonymous_level_dict
        scheme_type_dict = self.scheme_type_dict

        anonymous_level_default = AnonymousLevel.LOW
        scheme_type_default = SchemeType.HTTP
        support_method_default = SupportMethod.GET

        sel_list = response.xpath("//table/tbody/tr[position()>1]")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            item = ProxyItem()
            tds = [td.xpath("text()").extract_first("") for td in sel.xpath("td")]
            ip, port, level, type_str, _, location, *_ = tds

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_default
            item['location'] = location.strip()
            yield item
