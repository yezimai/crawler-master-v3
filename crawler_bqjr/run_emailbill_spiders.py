# -*- coding: utf-8 -*-

from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from crawler_bqjr.spiders.emailbill_spiders.imap_spider import EmailImapSpider
from crawler_bqjr.spiders.emailbill_spiders.email163_spider import Email163Spider
from crawler_bqjr.spiders.emailbill_spiders.emailqq_spider import EmailqqSpider
# from crawler_bqjr.spiders.emailbill_spiders.email_sina_driver_spider import EmailSinaDriverSpider
from crawler_bqjr.spiders.emailbill_spiders.email_sina_scrapy_spider import EmailSinaSpider
from crawler_bqjr.spiders.emailbill_spiders.email_sohu_scrapy_spider import EmailSohuSpider
# from crawler_bqjr.spiders.emailbill_spiders.email_sohu_driver_spider import EmailSohuDriverSpider
from run import run_multiple_spider_with_process


def crawl_emailbill_info(process_count=1):
    spider_dict = {
        "163": Email163Spider,
        "qq": EmailqqSpider,
        "sina": EmailSinaSpider,
        'sohu': EmailSohuSpider,
        'IMAP': EmailImapSpider,
    }

    run_multiple_spider_with_process(spider_dict, process_count)


if __name__ == '__main__':
    crawl_emailbill_info(1)
