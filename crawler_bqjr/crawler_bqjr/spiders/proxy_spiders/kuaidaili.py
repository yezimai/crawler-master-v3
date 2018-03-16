# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep

from scrapy import Request

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import PhantomjsRequestSpider, NoticeChangeSpider


class KuaidailiSpider(PhantomjsRequestSpider, NoticeChangeSpider):
    name = "kuaidaili"
    allowed_domains = ["kuaidaili.com"]
    start_urls = ["http://www.kuaidaili.com/free/inha/1/",
                  "http://www.kuaidaili.com/free/intr/1/",
                  # "http://www.kuaidaili.com/free/outha/1/",
                  # "http://www.kuaidaili.com/free/outtr/1/",
                  ]

    custom_settings = {
        'DOWNLOAD_DELAY': 200,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         phantomjs_finish_xpath="//div[@id='list']/table/tbody",
                         **kwargs)
        self.anonymous_level_dict = {"高匿名": AnonymousLevel.HIGH,
                                     "匿名": AnonymousLevel.MIDDLE,
                                     "透明": AnonymousLevel.LOW,
                                     }
        self.scheme_type_dict = {"HTTP": SchemeType.HTTP,
                                 "HTTPS": SchemeType.HTTPS,
                                 "HTTP, HTTPS": SchemeType.HTTP_OR_HTTPS,
                                 }
        self.support_method_dict = {"GET, POST": SupportMethod.GET_OR_POST,
                                    }
        self.page_pattern = re_compile(r'/(\d+)/$')

    def parse(self, response):
        if "云节点工作中" in response.text:
            sleep(31)
            yield response.request.copy()
            return

        anonymous_level_dict = self.anonymous_level_dict
        scheme_type_dict = self.scheme_type_dict

        anonymous_level_default = AnonymousLevel.LOW
        scheme_type_default = SchemeType.HTTP
        support_method_default = SupportMethod.GET

        sel_list = response.xpath("//div[@id='list']/table/tbody/tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            item = ProxyItem()
            tds = [td.xpath("text()").extract_first("") for td in sel.xpath("td")]
            if len(tds) != 7:
                continue

            ip, port, level, type_str, location, *_ = tds

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_default
            item['location'] = location.strip()
            yield item

        parse_func = self.parse
        page_pattern = self.page_pattern
        response_url = response.url
        try:
            page = page_pattern.search(response_url).group(1)
            if int(page) == 1:
                last_page = response.xpath("(//div[@id='listnav']/ul/li/a)[last()]/text()").extract_first()
                for i in range(2, int(last_page) + 1):
                    url = page_pattern.sub("/" + str(i) + "/", response_url, 1)
                    yield Request(url, parse_func)
        except Exception:
            self.logger.warning("No page found.")
            yield Request(response_url, parse_func)
