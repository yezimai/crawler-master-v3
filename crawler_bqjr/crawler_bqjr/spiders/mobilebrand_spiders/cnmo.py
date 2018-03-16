# -*- coding: utf-8 -*-

from datetime import datetime

from scrapy.http import Request

from crawler_bqjr.items.mobilebrand_items import CnmoItem
from crawler_bqjr.spider_class import NoticeChangeSpider


class CnmoSpider(NoticeChangeSpider):
    name = "cnmo"
    allowed_domains = ["cnmo.com"]
    start_urls = ["http://product.cnmo.com/manu.html"]

    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        all_mobile_brands = response.xpath('//ul[@class="plist hot_plist clearfix"]/li')
        if not all_mobile_brands:
            self.notice_change("No brands found!!!!! " + response.url)

        for mobile_brand in all_mobile_brands:
            item = CnmoItem()
            item['brand_name'] = mobile_brand.xpath('.//a[@class="title"]/text()').extract_first()
            item['brand_pic'] = mobile_brand.xpath('.//a/img/@src').extract_first()
            item['brand_url'] = mobile_brand.xpath('.//a[@class="title"]/@href').extract_first()
            if item['brand_url']:
                yield Request(item['brand_url'],
                              self.parse_brand,
                              dont_filter=True,
                              meta={'item': item})

    def parse_brand(self, response):
        item = response.meta['item']
        all_mobiles = response.xpath('//li[@class="productlist-ul-li"]')
        # if not all_mobiles:
        #     self.notice_change("No mobile found!!!!! " + response.url)

        update_time = datetime.now()
        for mobile in all_mobiles:
            new_item = item.copy()
            new_item['product_url'] = mobile.xpath('.//a[@class="pul-title"]/@href|'
                                                   './/a[@class="pul-dp"]/@href|'
                                                   './/div/a/@href').extract_first()
            new_item['product_name'] = mobile.xpath('.//div/a/text()|'
                                                    './/div/a/@title|'
                                                    './/a[@class="pul-title"]/text()|'
                                                    './/a[@class="pul-tutle"]/@title').extract_first()
            new_item['product_pic'] = mobile.xpath('.//div/a/img/@src').extract_first()
            product_price = mobile.xpath('.//strong[@class="pul-rate"]/text()').extract_first()
            new_item['product_price'] = product_price
            new_item['for_sale'] = (product_price not in ['停产', '暂无报价'])
            new_item['update_time'] = update_time
            detail_url = mobile.xpath('.//a[contains(text(),"参数")]/@href').extract_first()
            if detail_url:
                yield Request(detail_url,
                              callback=self.parse_detail,
                              dont_filter=True,
                              meta={'item': new_item})
            else:
                yield new_item

        next_page = response.xpath('//a[contains(text(),"下一页")]/@href').extract_first()
        if next_page:
            yield Request(next_page,
                          callback=self.parse_brand,
                          dont_filter=True,
                          meta={'item': response.meta['item']})

    def parse_detail(self, response):
        item = response.meta['item']
        values = (x.strip() for x in response.xpath('//div[@class="clearfix"]/ul/li/text()').extract() if x.strip())
        keys = (x.replace('：', '') for x in response.xpath('//div[@class="clearfix"]/ul/li/span/text()').extract())
        item['detail_info'] = dict(zip(keys, values))

        for detail in response.xpath('//div[@id="paramList"]/div'):
            info_dict = {}
            for info in detail.xpath('.//ul/li'):
                left = info.xpath('.//span[@class="leftbiaoti"]/text()').extract_first()
                right = ','.join(info.xpath('.//em[@class="licont"]/text()').extract())
                info_dict[left] = right
            type_name = detail.xpath('.//strong[@name="typeName"]/text()').extract_first()
            item['detail_info'][type_name] = info_dict

        yield item
