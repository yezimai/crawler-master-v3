# -*- coding: utf-8 -*-

from multiprocessing import Process
from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.proxy_spiders.goubanjia import GoubanjiaSpider
from crawler_bqjr.spiders.proxy_spiders.kuaidaili import KuaidailiSpider
from crawler_bqjr.spiders.proxy_spiders.xicidaili import XicidailiSpider
from crawler_bqjr.spiders.proxy_spiders.nianshao import NianshaoSpider
from crawler_bqjr.spiders.proxy_spiders.ip181 import Ip181Spider
from crawler_bqjr.spiders.proxy_spiders.ip3366 import Ip3366Spider
from proxy_api.proxy_check import check_proxy_usable

from run import ran_forever, run_scrapy_spider


def crawl_new_proxy():
    spider_list = [
        # GoubanjiaSpider,
        KuaidailiSpider,
        XicidailiSpider,
        # NianshaoSpider,  # 包含国外IP
        # Ip181Spider,  # 包含国外IP
        # Ip3366Spider,  # 包含国外IP
    ]

    run_scrapy_spider(spider_list)


if __name__ == '__main__':
    p = Process(target=check_proxy_usable)
    p.start()
    ran_forever(crawl_new_proxy)
    p.terminate()
