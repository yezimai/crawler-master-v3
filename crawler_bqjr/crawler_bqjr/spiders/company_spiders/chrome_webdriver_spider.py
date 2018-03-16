# -*- coding: utf-8 -*-

from crawler_bqjr.spider_class import ProxyPhantomjsSpider
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class AbstractWebdriverSpider(CompanySpider, ProxyPhantomjsSpider):
    def __getwebdriver__(self):
        raise NotImplementedError()

    def __getwait_20__(self):
        raise NotImplementedError

    def __getwait_10__(self):
        raise NotImplementedError
