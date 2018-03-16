# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.other_spiders.gpsspg import GpsspgSpider
from run import run_multiple_spider_with_process


def crawl_other_info(process_count=1):
    spider_dict = {
        "Gpsspg": GpsspgSpider,
    }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_other_info(1)
