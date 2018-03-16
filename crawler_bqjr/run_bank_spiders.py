# -*- coding: utf-8 -*-

from os import path as os_path
from platform import system as get_os
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.bank_spiders.cgb_phone import CgbWapSpider
from crawler_bqjr.spiders.bank_spiders.cmbc import CMBCSpider
from crawler_bqjr.spiders.bank_spiders.icbc import IcbcSpider
from crawler_bqjr.spiders.bank_spiders.boc import BocSpider
from crawler_bqjr.spiders.bank_spiders.cmb import CmbSpider
from crawler_bqjr.spiders.bank_spiders.psbc import PsbcSpider
from crawler_bqjr.spiders.bank_spiders.cib import CibSpider
from crawler_bqjr.spiders.bank_spiders.spdb import SpdbSpider
from crawler_bqjr.spiders.bank_spiders.cncb import CncbSpider
from crawler_bqjr.spiders.bank_spiders.bocom_phone import BocomWapSpider
from crawler_bqjr.spiders.bank_spiders.abc import ABCSpider
from crawler_bqjr.spiders.bank_spiders.ccb import CCBSpider
from crawler_bqjr.spiders.bank_spiders.ceb import CebSpider
from crawler_bqjr.spiders.bank_spiders.pingan import PinganSpider
from crawler_bqjr.spiders.bank_spiders.hxb import HxbSpider
from run import run_multiple_spider_with_process


def crawl_bank_info(process_count=1):
    if 'Windows' == get_os():
        spider_dict = {
            "农业银行": ABCSpider,
            "建设银行": CCBSpider,
            "邮政银行": PsbcSpider,
            "工商银行": IcbcSpider,
            "中国银行": BocSpider,
            "招商银行": CmbSpider,
            "民生银行": CMBCSpider,
            "光大银行": CebSpider,
            "中信银行": CncbSpider,
            "浦发银行": SpdbSpider,
            "华夏银行": HxbSpider,

            "平安银行": PinganSpider,
        }
    else:
        spider_dict = {
            "交通银行": BocomWapSpider,
            "兴业银行": CibSpider,
            "广发银行": CgbWapSpider,
        }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_bank_info(process_count=1)
