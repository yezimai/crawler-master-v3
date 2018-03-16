# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.wenshu_spiders.query_condition import *
from run import run_multiple_spider_with_process


def crawl_wenshu_info():
    """
    201609到201301
    :return:
    """
    date_list = ["201609", "201608", "201607", "201606", "201605", "201604", "201603", "201602", "201601",
                 "201512", "201511", "201510", "201509", "201508", "201507", "201506", "201505", "201504",
                 "201503", "201502", "201501", "201412", "201411", "201410", "201409", "201408", "201407",
                 "201406", "201405", "201404", "201403", "201402", "201401", "201312", "201311", "201310",
                 "201309", "201308", "201307", "201306", "201305", "201304", "201303", "201302", "201301"]
    spider_dict = dict()
    for date in date_list:
        spider_dict["ConditionSpider_%s" % date] = eval("ConditionSpider_%s" % date)

    run_multiple_spider_with_process(spider_dict, process_count=1)


if __name__ == '__main__':
    crawl_wenshu_info()
