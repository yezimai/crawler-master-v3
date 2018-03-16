# -*- coding: utf-8 -*-

from re import compile as re_compile

from scrapy import Request

from crawler_bqjr.items.proxy_items import ProxyItem, AnonymousLevel, SchemeType, SupportMethod
from crawler_bqjr.spider_class import PhantomjsRequestSpider, NoticeChangeSpider


class GoubanjiaSpider(PhantomjsRequestSpider, NoticeChangeSpider):
    name = "goubanjia"
    allowed_domains = ["goubanjia.com"]
    start_urls = ["http://www.goubanjia.com/free/gngn/index1.shtml",
                  "http://www.goubanjia.com/free/gnpt/index1.shtml",
                  # "http://www.goubanjia.com/free/index1.shtml",
                  # "http://www.goubanjia.com/free/gwgn/index1.shtml",
                  # "http://www.goubanjia.com/free/gwpt/index1.shtml",
                  ]

    custom_settings = {
        'DOWNLOAD_DELAY': 3000,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         phantomjs_finish_xpath="//div[@id='list']/table/tbody",
                         **kwargs)
        self.anonymous_level_dict = {"高匿": AnonymousLevel.HIGH,
                                     "匿名": AnonymousLevel.MIDDLE,
                                     "透明": AnonymousLevel.LOW,
                                     }
        self.scheme_type_dict = {"http": SchemeType.HTTP,
                                 "https": SchemeType.HTTPS,
                                 "http, https": SchemeType.HTTP_OR_HTTPS,
                                 }
        self.page_pattern = re_compile(r'/index(\d+)\.shtml$')

    def parse(self, response):
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

            ip = "".join(i for i in sel.xpath("td[1]/*[not(contains(@style,'none')) and "
                                              "not(contains(@class,'port'))]/text()").extract() if i)
            port = sel.xpath("td[1]/span[starts-with(@class,'port')]/text()").extract_first()
            level = sel.xpath("td[2]/a/text()").extract_first()
            type_str = sel.xpath("td[3]/a/text()").extract_first()
            location = " ".join(i for i in sel.xpath("td[4]/a/text()").extract() if i)

            item['ip'] = ip.strip()
            item['port'] = port
            item['anonymous_level'] = anonymous_level_dict.get(level, anonymous_level_default)
            item['scheme_type'] = scheme_type_dict.get(type_str, scheme_type_default)
            item['support_method'] = support_method_default
            item['location'] = location.strip()
            yield item

        parse_func = self.parse
        try:
            page = self.page_pattern.search(response.url).group(1)
            if int(page) == 1:
                last_page = response.xpath("(//div[@class='wp-pagenavi']/a)[last()]/text()").extract_first()
                for i in range(2, int(last_page) + 1):
                    url = response.urljoin("index" + str(i) + ".shtml")
                    yield Request(url, parse_func)
        except Exception:
            self.logger.warning("No page found.")
            yield Request(response.url, parse_func)
