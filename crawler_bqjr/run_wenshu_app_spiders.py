# -*- coding: utf-8 -*-

from os import path as os_path, getpid
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.wenshu_spiders.wenshu_app import WenshuAppSpider
from crawler_bqjr.spiders.wenshu_spiders.wenshu_pc import WenshuPcSpider
from run import run_multiple_spider_with_process


def crawl_wenshu_info(process_count=1):
    spider_dict = {"WenshuAppSpider": WenshuAppSpider,
                   "WenshuPcSpider": WenshuPcSpider,
                   }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    with open("count.txt", "w") as f:
        f.write("0")
    with open("pid.txt", "w") as f:
        f.write(str(getpid()))
    crawl_wenshu_info(10)
