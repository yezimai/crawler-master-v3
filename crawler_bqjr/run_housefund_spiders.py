# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.housefund_spiders.chengdu import HousefundChengduSpider
from crawler_bqjr.spiders.housefund_spiders.guangzhou import HousefundGuangzhouSpider
from run import run_multiple_spider_with_process


def crawl_housefund_info(process_count=1):
    spider_dict = {"成都公积金": HousefundChengduSpider,
                   "广州公积金": HousefundGuangzhouSpider,
                   }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_housefund_info(1)
