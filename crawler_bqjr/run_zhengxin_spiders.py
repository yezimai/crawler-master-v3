# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.zhengxin_spiders.zhengxin_pbc import ZhengxinPbcSpider
from crawler_bqjr.spiders.zhengxin_spiders.zhengxin_bank import ZhengxinBankSpider
from run import run_multiple_spider_with_process


def crawl_zhengxin_info(process_count=1):
    spider_dict = {
        "人行征信": ZhengxinPbcSpider,
        # "银行征信": ZhengxinBankSpider,
    }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_zhengxin_info(1)
