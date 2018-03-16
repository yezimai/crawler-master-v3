# -*- coding: utf-8 -*-

from crawler_bqjr.spider_class import NoticeClosedSpider
from scrapy.http import Request

from crawler_bqjr.items.wenshu_items import ChinacourtItem


class ChinacourtSpider(NoticeClosedSpider):
    """
    中国法院网爬虫
    """

    name = "chinacourt"
    allowed_domains = ["chinacourt.org"]
    start_urls = ["http://www.chinacourt.org/article/index/id/MzAwNDAwMyAOAAA%3D.shtml"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        province_list = response.xpath('//div[@class="dfpddh"]/ul/li')
        for province in province_list:
            item = ChinacourtItem()
            item['province'] = province.xpath('a/text()').extract_first()
            province_url = response.urljoin(province.xpath('a/@href').extract_first(""))
            yield Request(province_url, self.parse_province, meta={"item": item}, dont_filter=True)

    def parse_province(self, response):
        item = response.meta["item"]
        item['name'] = response.xpath('//div[@class="gy"]/a/text()|//div[@class="gy"]'
                                      '/text()').extract_first("").replace('高院', '高级人民法院')
        item['level'] = 'gy'
        yield item

        zy_list = response.xpath('//div[@class="zy"]')  # 中级人民法院
        for zy in zy_list:
            item['name'] = zy.xpath('a/text()|text()').extract_first("").replace('中院', '中级人民法院')
            item['level'] = 'zy'
            yield item

        jcy_list = response.xpath('//div[@class="jcy"]/ul/li/span')  # 基层法院
        for jcy in jcy_list:
            item['name'] = jcy.xpath('a/text()|text()').extract_first("").replace('法院', '人民法院')
            item['level'] = 'jcy'
            yield item
