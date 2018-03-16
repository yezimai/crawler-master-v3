# -*- coding: utf-8 -*-

from re import compile as re_compile

from scrapy import Spider
from scrapy.http import FormRequest, Request

from crawler_bqjr.items.shixin_items import P2PItem


class ShixinKaikaidaiSpider(Spider):
    name = "shixin_kaikaidai"
    allowed_domains = ["kaikaidai.com"]
    start_urls = ["http://www.kaikaidai.com/lend/black.aspx"]

    custom_settings = {
        'DOWNLOAD_DELAY': 300,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.replace_pattern = re_compile(r"\s*")
        self.page_count_regex = re_compile(r"第(\d+)页/共(\d+)页")

    def parse(self, response):
        tr_list = response.xpath('//table[@class="hmd_ytab"]')
        replace_pattern = self.replace_pattern
        for tr in tr_list:
            item = P2PItem()
            item["from_web"] = ShixinKaikaidaiSpider.allowed_domains[0]
            item["name"] = replace_pattern.sub("", tr.xpath('tr[1]/td[3]/a/text()').extract_first(""))  # 真实姓名
            item["id"] = replace_pattern.sub("", tr.xpath('tr[2]/td[2]/text()').extract_first(""))  # 身份证
            item["debt_detail"] = {
                "几笔逾期未还款": replace_pattern.sub("", tr.xpath('tr[1]/td[7]/text()').extract_first("")),
                "几笔网站垫付款": replace_pattern.sub("", tr.xpath('tr[2]/td[6]/text()').extract_first("")),
                "最长逾期天数": replace_pattern.sub("", tr.xpath('tr[3]/td[6]/text()').extract_first("")),
                "逾期待还总额": replace_pattern.sub("", tr.xpath('tr[4]/td[6]/text()').extract_first("")),
                "详情": []
            }

            detail_url = tr.xpath('tr[1]/td[1]/a/@href').extract_first()
            if detail_url:
                detail_url = response.urljoin(detail_url)
                yield Request(detail_url, self.parse_detail, meta={"item": item}, dont_filter=True)

        page_current, page_count = self.page_count_regex.search(response.text).groups()
        if int(page_current) < int(page_count):
            post_data = {
                "__EVENTTARGET": "rpMessage",
                "__EVENTARGUMENT": "pager$" + page_current,
                "__VIEWSTATE": response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first(""),
                "rpMessage": ""
            }
            yield FormRequest(ShixinKaikaidaiSpider.start_urls[0], self.parse, formdata=post_data)

    def parse_detail(self, response):
        item = response.meta["item"]

        # 获取个人详细信息
        personal_detail = dict()
        table = response.xpath('//div[@class="hmd_xxzl"]/table')
        personal_detail["用户名"] = table.xpath('tr[1]/td[3]/a/text()').extract_first("").strip()
        for xpath in ["tr[2]/td[1]", "tr[2]/td[2]", "tr[3]/td[2]", "tr[4]/td[2]",
                      "tr[4]/td[1]", "tr[5]/td[1]", "tr[6]/td[1]", "tr[7]/td[1]"]:
            try:
                k, v = table.xpath(xpath + '/text()').extract_first("").strip().split("：", 1)
                personal_detail[k] = v
            except Exception:
                pass
        item["personal_detail"] = personal_detail

        # 获取账户详情
        account_detail = dict()
        li_list = response.xpath('//div[@class="black_detail"]/ul/li')
        for li in li_list:
            key = li.xpath("text()").extract_first("").split("：", 1)[0].strip()
            account_detail[key] = li.xpath("span/text()").extract_first("").strip()
        item["account_detail"] = account_detail

        # 获取欠款明细
        debt_detail = item["debt_detail"]
        tr_list = response.xpath('//div[@class="have_back"]/table/tr[not(contains(@class, "title2"))]')
        for tr in tr_list:
            tr_tmp = dict()
            tr_tmp["序号"] = tr.xpath("td[1]/text()").extract_first("").strip()
            tr_tmp["借款标题"] = tr.xpath("td[2]/a/span/text()").extract_first("").strip()
            tr_tmp["应还本息"] = tr.xpath("td[3]/text()").extract_first("").strip().split(":", 1)[-1]
            tr_tmp["已还本息"] = tr.xpath("td[3]/p/text()").extract_first("").strip().split(":", 1)[-1]
            tr_tmp["应还日期"] = tr.xpath("td[4]/text()").extract_first("").strip().split("：", 1)[-1]
            arr_tmp = tr.xpath("td[4]/p/text()").extract_first("").strip().split(":")
            tr_tmp["实还日期"] = arr_tmp[1] if len(arr_tmp) >= 2 else ""
            tr_tmp["逾期天数"] = tr.xpath("td[5]/text()").extract_first("").strip()
            tr_tmp["还款状态"] = tr.xpath("td[6]/span/text()").extract_first("").strip()
            debt_detail["详情"].append(tr_tmp)

        yield item
