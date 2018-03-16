# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.wenshu_spiders.wenshu_pc import WenshuPcSpider
from run import run_scrapy_spider


def crawl_wenshu_info():
    run_scrapy_spider(WenshuPcSpider)


if __name__ == '__main__':
    crawl_wenshu_info()
