# -*- coding: utf-8 -*-

from datetime import datetime
from re import compile as re_compile

from scrapy.http import Request

from crawler_bqjr.items.mobilebrand_items import ZolAccessoryItem
from crawler_bqjr.spider_class import NoticeChangeSpider


class ZolAccessorySpider(NoticeChangeSpider):
    name = "zol"
    allowed_domains = ["zol.com.cn"]

    custom_settings = {
        'DOWNLOAD_DELAY': 50,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_page_pattern = re_compile(r'(.*/)(\d+).html')
        self.img_url_pattern = re_compile(r'src="(.*?)"')

    def start_requests(self):
        urls = {'手机充电器': 'http://detail.zol.com.cn/cellcharger/1.html',
                '手机电池': 'http://detail.zol.com.cn/phonebattery/1.html',
                '手机数据线': 'http://detail.zol.com.cn/datacable/1.html',
                '手机底座': 'http://detail.zol.com.cn/mobile-base/1.html',
                '手机贴膜': 'http://detail.zol.com.cn/mobile-laoding/1.html',
                '手机保护套': 'http://detail.zol.com.cn/mobile-demeo/1.html',
                '手机车载配件': 'http://detail.zol.com.cn/mobile-car-accessories/1.html',
                '手机其他配件': 'http://detail.zol.com.cn/phone_annex/1.html',
                '手机存储卡': 'http://detail.zol.com.cn/flash_memory/s741/1.html',
                '手机耳机': 'http://detail.zol.com.cn/microphone/shenzhen/1.html',
                }
        for k, v in urls.items():
            yield Request(v, meta={'category': k})

    def parse(self, response):

        all_products = response.xpath('//ul[@class="clearfix"]/li')
        if all_products:
            # 本页有产品就继续下一页直到没有
            temp = self.next_page_pattern.search(response.url).groups()
            next_page_url = temp[0] + str(int(temp[1]) + 1) + '.html'
            yield Request(next_page_url, callback=self.parse, meta=response.meta)

        for product in all_products:
            item = ZolAccessoryItem()
            item['update_time'] = datetime.now()
            item['category'] = response.meta['category']
            item['name'] = product.xpath('.//h3/a/text()').extract_first()
            pic_url = self.img_url_pattern.search(product.xpath('.//a/img').extract_first(""))
            item['pic_url'] = pic_url.group(1) if pic_url else ""

            item['status'] = product.xpath('.//span[@class="price-status"]/text()').extract_first('正常').replace('[', '').replace(']', '')

            price = ''.join(product.xpath('.//span[contains(@class,"price")]/b/text()').extract())
            item['price'] = price
            if price == '停产':
                item['status'] = '停产'
            elif price == '即将上市':
                item['status'] = '即将上市'

            item['url'] = 'http://detail.zol.com.cn' + product.xpath('.//h3/a/@href').extract_first("")

            info = {}
            params = product.xpath('.//h3/a/span/text()').extract_first("")
            if params:
                for param in params.split(" "):
                    the_datas = param.split(":")
                    if len(the_datas) == 2:
                        k, v = the_datas
                        info[k] = v
            item['info'] = info

            yield item
