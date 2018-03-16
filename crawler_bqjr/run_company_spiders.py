# -*- coding: utf-8 -*-

from multiprocessing import Process
from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.company_spiders.base import push_all_company_id, \
    record_all_company_name, del_duplicate_company
from crawler_bqjr.spiders.company_spiders.list_51job import List51jobSpider
from crawler_bqjr.spiders.company_spiders.list_zhaopin import ListZhaopinSpider
from crawler_bqjr.spiders.company_spiders.list_makepolo import ListMakepoloSpider
from crawler_bqjr.spiders.company_spiders.list_huangye88 import ListHuangye88Spider
from crawler_bqjr.spiders.company_spiders.list_cnlist import ListCnlistSpider
from crawler_bqjr.spiders.company_spiders.list_cnlinfo import ListCnlinfo88Spider
from crawler_bqjr.spiders.company_spiders.list_88152 import List88152Spider
from crawler_bqjr.spiders.company_spiders.list_qincai import ListQincaiSpider
from crawler_bqjr.spiders.company_spiders.list_qiye import ListQiyeSpider
from crawler_bqjr.spiders.company_spiders.list_qy6 import ListQy6Spider
from crawler_bqjr.spiders.company_spiders.list_51sole import List51SoleSpider
from crawler_bqjr.spiders.company_spiders.list_soudh import ListSoudhSpider
from crawler_bqjr.spiders.company_spiders.list_8671 import List8671Spider
from crawler_bqjr.spiders.company_spiders.list_56ye import List56YeSpider
from crawler_bqjr.spiders.company_spiders.list_ynshangji import ListYnshangjiSpider
from crawler_bqjr.spiders.company_spiders.list_youboy import ListYouboySpider
from crawler_bqjr.spiders.company_spiders.list_zhaoshang100 import ListZhaoshang100Spider
from crawler_bqjr.spiders.company_spiders.list_ganji import ListGanjiSpider
from crawler_bqjr.spiders.company_spiders.list_99114 import List99114Spider
from crawler_bqjr.spiders.company_spiders.list_58 import List58Spider
from crawler_bqjr.spiders.company_spiders.detail_szmqs import DetailSzmqsSpider
from crawler_bqjr.spiders.company_spiders.detail_58 import Detail58Spider
from crawler_bqjr.spiders.company_spiders.detail_tianyancha import DetailTianyanchaSpider, \
    push_all_tianyancha_company_id
from crawler_bqjr.spiders.company_spiders.detail_gsxt import DetailGSXTSpider
from run import run_scrapy_spider


def crawl_company_info():
    spider_list = [
        List51jobSpider,
        List51SoleSpider,
        List56YeSpider,
        List58Spider,
        List8671Spider,
        List88152Spider,
        List99114Spider,
        ListCnlinfo88Spider,
        ListCnlistSpider,
        ListGanjiSpider,
        ListHuangye88Spider,
        ListMakepoloSpider,
        ListQincaiSpider,
        ListQiyeSpider,
        ListQy6Spider,
        ListSoudhSpider,
        ListYnshangjiSpider,
        ListYouboySpider,
        ListZhaopinSpider,
        ListZhaoshang100Spider,

        DetailTianyanchaSpider,  # 会被封
        Detail58Spider,
        DetailSzmqsSpider,
    ]

    run_scrapy_spider(spider_list)


if __name__ == '__main__':
    del_duplicate_company()
    # push_all_company_id()  # 将所有公司重新加入SSDB队列
    # push_all_tianyancha_company_id()
    # record_all_company_name()  # 记录所有爬取过的公司名单,避免重复爬取

    # 该国家企网的爬虫使用了PhantomJS进行爬取，
    # 由于其执行较慢，会阻塞其它爬虫，所以它单独开进程执行
    # p = Process(target=run_scrapy_spider, args=(DetailGSXTSpider,))
    # p.start()

    crawl_company_info()

    # p.terminate()
    print("Company spider finished.")
