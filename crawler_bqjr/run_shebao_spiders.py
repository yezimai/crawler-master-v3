# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.shebao_spiders.shebao_chengdu import ShebaoChengduSpider
from crawler_bqjr.spiders.shebao_spiders.shebao_guangzhou import ShebaoGuangzhouSpider
from run import run_multiple_spider_with_process


def crawl_shebao_info(process_count=1):
    spider_dict = {"ShebaoChengdu": ShebaoChengduSpider,
                   "ShebaoGuangzhou": ShebaoGuangzhouSpider,
                   }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_shebao_info(1)
