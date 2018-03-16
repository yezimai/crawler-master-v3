# -*- coding: utf-8 -*-

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import PhantomjsRequestSpider, NoticeChangeSpider


class XicidailiSpider(PhantomjsRequestSpider, NoticeChangeSpider):
    name = "xicidaili"
    allowed_domains = ["xicidaili.com"]
    start_urls = ["http://www.xicidaili.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         phantomjs_finish_xpath="//table[@id='ip_list']",
                         **kwargs)
        self.anonymous_level_dict = {"高匿": AnonymousLevel.HIGH,
                                     "透明": AnonymousLevel.LOW,
                                     }
        self.scheme_type_dict = {"HTTP": SchemeType.HTTP,
                                 "HTTPS": SchemeType.HTTPS,
                                 }

    def parse(self, response):
        anonymous_level_dict = self.anonymous_level_dict
        scheme_type_dict = self.scheme_type_dict

        anonymous_level_default = AnonymousLevel.LOW
        scheme_type_default = SchemeType.HTTP
        support_method_default = SupportMethod.GET

        sel_list = response.xpath("//table[@id='ip_list']/tbody/tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            item = ProxyItem()
            tds = [td.xpath("text()").extract_first("") for td in sel.xpath("td")]
            if not tds:
                continue

            country = sel.xpath("td[@class='country']/img/@alt").extract_first()
            if "Cn" != country:
                continue

            _, ip, port, location, level, type_str, *_ = tds
            if "socks4/5" == type_str:
                continue

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_default
            item['location'] = location.strip()
            yield item
