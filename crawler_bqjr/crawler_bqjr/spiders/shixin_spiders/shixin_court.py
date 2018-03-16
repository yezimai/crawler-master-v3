# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.shixin_items import ShixinListItem
from crawler_bqjr.spider_class import LoggingClosedSpider, NoticeChangeSpider, RecordSearchedSpider
from crawler_bqjr.spiders.company_spiders.base import BLANK_CHARS
from crawler_bqjr.spiders.shixin_spiders.shixin_kuaicha import SSDB_SHIXIN_LIST_ID_HSET_NAME


class ShixinCourtSpider(LoggingClosedSpider, NoticeChangeSpider, RecordSearchedSpider):
    name = "shixin_court"
    allowed_domains = ["court.gov.cn"]
    start_urls = ["http://shixin.court.gov.cn/index_publish_new.jsp"]

    custom_settings = {
        'DOWNLOAD_DELAY': 5000,  # 防封杀
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_SHIXIN_LIST_ID_HSET_NAME, **kwargs)

    def start_requests(self):
        parse = self.parse
        url = self.start_urls[0]
        while True:
            yield Request(url, parse, dont_filter=True)

    def parse(self, response):
        spider_name = self.name
        sel_list = response.xpath("//tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name_a = sel.xpath("td[1]/a")
                name = name_a.xpath("text()").extract_first("").strip(BLANK_CHARS)
                the_id = sel.xpath("td[2]/text()").extract_first("")

                key = name + the_id
                if self.is_search_name_exists(key):
                    continue
                self.record_search_name(key)

                item = ShixinListItem()
                item["name"] = name
                item["id"] = the_id
                item["from_web"] = spider_name
                item["link_id"] = int(name_a.xpath("@id").extract_first())
                yield item
            except Exception:
                self.logger.exception("")
