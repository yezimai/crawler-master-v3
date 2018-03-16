# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.mobilebrand_spiders.cnmo import CnmoSpider

from run import ran_forever, run_scrapy_spider


def crawl_mobile_info():
    run_scrapy_spider([
        CnmoSpider,
    ])


if __name__ == '__main__':
    ran_forever(crawl_mobile_info)
