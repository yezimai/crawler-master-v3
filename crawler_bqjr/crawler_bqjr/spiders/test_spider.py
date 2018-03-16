# -*- coding: utf-8 -*-

from crawler_bqjr.spider_class import PhantomjsRequestSpider


class TestSpider(PhantomjsRequestSpider):
    name = "test_spider"
    allowed_domains = ["xueqiu.com"]
    start_urls = ["https://xueqiu.com/S/SH601398/GBJG"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         phantomjs_finish_xpath="//table[contains(@class,'dataTable')]",
                         **kwargs)

    def parse(self, response):
        print(response.meta)
        print(response.headers)
        for sel in response.xpath("//table[contains(@class,'dataTable')]/tbody/tr"):
            print(sel.extract())
