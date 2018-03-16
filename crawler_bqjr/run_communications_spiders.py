# -*- coding: utf-8 -*-

from multiprocessing import Process
from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.communications_spiders.china_unicom import ChinaUnicomSpider
from crawler_bqjr.spiders.communications_spiders.china_mobile import ChinaMobileSpider
from crawler_bqjr.spiders.communications_spiders.china_telecom_app import ChinaTelecomAppSpider
# from crawler_bqjr.spiders.communications_spiders.yournumber_cn import YournumberSpider
from run import run_multiple_spider_with_process, run_scrapy_spider


def crawl_user_communication_info(process_count=1):
    # p = Process(target=run_scrapy_spider, args=(YournumberSpider,))
    # p.start()

    spider_dict = {"中国联通": ChinaUnicomSpider,
                   "中国移动": ChinaMobileSpider,
                   #"中国电信": ChinaTelecomAppSpider,
                   }
    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_user_communication_info(process_count=1)
