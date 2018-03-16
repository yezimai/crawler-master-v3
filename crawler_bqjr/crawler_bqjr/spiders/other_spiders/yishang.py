# -*- coding: utf-8 -*-

from scrapy import Spider
from scrapy.http import Request

from crawler_bqjr.items.other_items import YishangItem


class YishangSpider(Spider):
    name = "yishang"
    allowed_domains = ["yishanggongyi.com"]
    start_urls = ["http://www.yishanggongyi.com/index.php?s=/home/bussiness/sj_credit/is_hege/1/p/1.html"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        urljoin = response.urljoin
        sellers = response.xpath('//div[@class="am-g"]')
        for seller in sellers:
            item = YishangItem()
            item['name'] = seller.xpath('div[@class="am-u-sm-9"]/p/text()').extract_first()
            item['address'] = seller.xpath('div[@class="am-u-sm-9"]/span/text()').extract_first()
            item['pic'] = urljoin(seller.xpath('div[@class="am-u-sm-3"]/img/@src').extract_first("").strip())
            yield item

        url = response.xpath("//div[@class='buliang']//a[@class='next']/@href").extract_first()
        if url:
            url = urljoin(url)
            yield Request(url, self.parse, dont_filter=True)
