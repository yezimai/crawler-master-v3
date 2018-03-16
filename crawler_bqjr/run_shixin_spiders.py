# -*- coding: utf-8 -*-

from multiprocessing import Process
from os import path as os_path
from sys import path as sys_path
from time import sleep

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.find_name_words import NameWords
from crawler_bqjr.spiders.shixin_spiders.shixin_dlm import ShixinDLMSpider
from crawler_bqjr.spiders.shixin_spiders.shixin_baidu import ShixinBaiduSpider, \
    record_all_shixin_id, del_duplicate_shixin
from crawler_bqjr.spiders.shixin_spiders.shixin_kuaicha import ShixinKuaichaSpider, \
    record_all_shixinlist_id, del_duplicate_shixinlist
from crawler_bqjr.spiders.shixin_spiders.shixin_shixinmingdan import ShixinmingdanSpider
from crawler_bqjr.spiders.shixin_spiders.shixin_court import ShixinCourtSpider
from crawler_bqjr.spiders.shixin_spiders.zhixing_court import ZhixingCourtSpider, \
    record_all_zhixing_id, del_duplicate_zhixing
from crawler_bqjr.spiders.shixin_spiders.p2p.shixin_kaikaidai import ShixinKaikaidaiSpider
from crawler_bqjr.spiders.shixin_spiders.p2p.shixin_my089 import ShixinMy089Spider
from run import run_scrapy_spider

from run import ran_forever


def crawl_shixin_baidu():
    run_scrapy_spider(ShixinBaiduSpider)


def crawl_shixin_kuaicha():
    run_scrapy_spider(ShixinKuaichaSpider)


def crawl_shixin_other():
    run_scrapy_spider([
        ShixinCourtSpider,
        ShixinmingdanSpider,
        ShixinDLMSpider,
    ])


def crawl_shixin_p2p():
    run_scrapy_spider([
        ShixinKaikaidaiSpider,
        ShixinMy089Spider,
    ])


def crawl_zhixing_court():
    run_scrapy_spider(ZhixingCourtSpider)


def crawl_zhixing_dlm():
    run_scrapy_spider(ShixinDLMSpider)


if __name__ == '__main__':
    del_duplicate_shixinlist()
    del_duplicate_shixin()
    del_duplicate_zhixing()

    # record_all_shixinlist_id()
    # record_all_shixin_id()
    # record_all_zhixing_id()

    process_list = []
    for t in [crawl_shixin_baidu, crawl_shixin_kuaicha, crawl_shixin_other, crawl_shixin_p2p]:
        p = Process(target=ran_forever, args=(t,))
        p.start()

        sleep(1)

    crawl_zhixing_court()

    for p in process_list:
        p.terminate()
