# -*- coding: utf-8 -*-

from datetime import datetime
from re import compile as re_compile

from scrapy import Request

from crawler_bqjr.items.shixin_items import ShixinDetailItem
from crawler_bqjr.spider_class import LoggingClosedSpider, NoticeChangeSpider, RecordSearchedSpider
from crawler_bqjr.spiders.company_spiders.base import BLANK_CHARS
from crawler_bqjr.spiders.shixin_spiders.shixin_baidu import SSDB_SHIXIN_ID_HSET_NAME


class ShixinmingdanSpider(LoggingClosedSpider, NoticeChangeSpider, RecordSearchedSpider):
    name = "shixinmingdan"
    allowed_domains = ["shixinmingdan.com"]
    start_urls = ["http://www.shixinmingdan.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 11,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_SHIXIN_ID_HSET_NAME, **kwargs)
        self.link_id_pattern = re_compile(r"(\d+)\.html")
        self.from_web = "1"

    def start_requests(self):
        parse_item = self.parse_item
        yield Request(self.start_urls[0], self.parse, dont_filter=True)
        for i in range(2215, 158281):
            url = "http://www.shixinmingdan.com/a/%d.html" % i
            yield Request(url, parse_item)

    def parse(self, response):
        urljoin = response.urljoin
        parse_item = self.parse_item

        sel_list = response.xpath("//div[contains(@class,'_ullist')]/ul/li/a")
        # if not sel_list:
        #     self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            href = sel.xpath("@href").extract_first("")
            url = urljoin(href)
            yield Request(url, parse_item)

    def text_join(self, text_iterable, link_str=""):
        text_list = (i.strip(BLANK_CHARS) for i in text_iterable)
        return link_str.join(i for i in text_list if i)

    def parse_item(self, response):
        yield from self.parse(response)

        response_url = response.url
        text_join = self.text_join
        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='content']/dl")))

            if not info_dict:
                # self.notice_change("No data found!!!!! " + response_url)
                return

            from_web = self.from_web
            link_id = int(self.link_id_pattern.search(response_url).group(1))
            link_name = from_web + "_" + str(link_id)
            if self.is_search_name_exists(link_name):
                return
            self.record_search_name(link_name)

            item = ShixinDetailItem()
            item["from_web"] = from_web
            item["link_id"] = link_id
            item["update_time"] = datetime.now()
            item["name"] = info_dict.get("被执行人姓名/名称")
            item["id"] = info_dict.get("身份证号码/组织机构代码")

            item["execution_court"] = info_dict.get("执行法院")
            item["province"] = info_dict.get("省份")
            item["execution_file_code"] = info_dict.get("执行依据文号")
            item["on_file_date"] = info_dict.get("立案时间")
            item["file_code"] = info_dict.get("案号")
            item["adjudge_court"] = info_dict.get("做出执行依据单位")
            item["duty"] = info_dict.get("生效法律文书确定的义务")
            item["fulfill_status"] = info_dict.get("被执行人的履行情况")
            item["fulfill_situation"] = info_dict.get("失信被执行人行为具体情形")
            item["publish_date"] = info_dict.get("发布时间")

            for k, v in item.items():
                if v is None:
                    self.logger.error("URL(%s)表格异常：(%s)" % (response_url, k))
                    break

            item["legal_person"] = info_dict.get("法定代表人或者负责人姓名")
            item["sex"] = info_dict.get("性别")
            item["age"] = info_dict.get("年龄")

            yield item
        except Exception:
            self.logger.exception("")
