# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.b2c_ecommerce_spiders.jingdong import JingDongSpider
from crawler_bqjr.spiders.b2c_ecommerce_spiders.taobao import TaobaoSpider
from crawler_bqjr.spiders.b2c_ecommerce_spiders.alipay import AlipaySpider
# from crawler_bqjr.spiders.b2c_ecommerce_spiders.yhd import YhdSpider
from run import run_multiple_spider_with_process


def crawl_ecommerce_info(process_count=1):
    spider_dict = {
        "京东": JingDongSpider,
        "淘宝": TaobaoSpider,
        "支付宝": AlipaySpider,
        # "一号店": YhdSpider,
    }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_ecommerce_info(process_count=1)
