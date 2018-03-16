# -*- coding: utf-8 -*-

from math import ceil
from random import choice as rand_choice
from re import compile as re_compile, S as re_S

from scrapy.http import Request, FormRequest

from crawler_bqjr.items.wenshu_items import WenshuItem
from crawler_bqjr.spiders.wenshu_spiders.base import WenshuSpider
from global_utils import json_loads

test_condition = [
    '[["case_type","0"],["court","上海市高级人民法院"],["date","2017-03-01 TO 2017-03-31"]]',
    '[["case_type","0"],["court","上海市第一中级人民法院"],["date","2017-03-01 TO 2017-03-05"]]',
]
DEBUG = True


class WenshuPcSpider(WenshuSpider):
    """
    爬取策略：
    wenshu_old爬虫，按照上传日期并以裁判日期倒序爬取，爬取上传日期范围：1995-12-31 TO 2017-04-11
    wenshu_today爬虫，在此过程中网站还在不停更新文书内容，更新的文书内容则按照上传日期进行检索爬取，更新的爬虫爬取2017年4月12日及之后的数据即可

    去重：
    爬取过程中需在ssdb中记录当前的start_index（当前爬取到的数据位置）及已经爬取到的文书id，避免重复爬取

    """

    name = "wenshu_pc_spider"
    allowed_domains = ["wenshu.court.gov.cn"]

    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPERROR_ALLOWED_CODES": [400, 401, 403, 404, 500, 501, 502, 503],
        # "RETRY_ENABLED": True,
        # "RETRY_TIMES": 1000,
        # "DOWNLOAD_TIMEOUT": 180,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_url = "http://wenshu.court.gov.cn/List/ListContent"  # app 文书列表
        self.doc_url = "http://wenshu.court.gov.cn/CreateContentJS/CreateContentJS.aspx?DocID=%s"  # app 文件内容
        self.page_size = 20  # 分页大小
        self.start_index = 1
        self.condition = {}  # 当前查询条件
        self.headers = {
            "Origin": "http://wenshu.court.gov.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "http://wenshu.court.gov.cn",
            "X-Requested-With": "XMLHttpRequest",
        }
        self.req_data = {
            "Param": "",
            "Index": str(self.start_index),
            "Page": str(self.page_size),
            "Order": "法院层级",
            "Direction": "asc",
        }
        self.data_pattern = re_compile(r'var.*?jsonHtmlData = "(.*?)";', re_S)

    def set_proxy(self, request):
        #  设置代理
        self.logger.info("current proxy->%s" % self.proxy)
        request.meta["proxy"] = "http://" + self.proxy

    def reset_req(self):
        """
        重置请求，拿出新的查询条件，并将请求起始位置重置为0
        :return:
        """
        # 从查询条件的ssdb队列中获取查询条件
        if DEBUG:
            self.condition = dict(eval(rand_choice(test_condition)))
        else:
            self.condition = dict(eval(self.get_wenshu_condition()))
        if self.condition["case_type"] == "0":
            self.req_data["Param"] = "法院名称:%s,裁判日期:%s" \
                                     % (self.condition["court"], self.condition["date"])
        else:
            if self.condition["case_type"] == "1":
                self.condition["case_type"] = "刑事案件"
            elif self.condition["case_type"] == "2":
                self.condition["case_type"] = "民事案件"
            elif self.condition["case_type"] == "3":
                self.condition["case_type"] = "行政案件"
            elif self.condition["case_type"] == "4":
                self.condition["case_type"] = "赔偿案件"
            elif self.condition["case_type"] == "5":
                self.condition["case_type"] = "执行案件"
            self.req_data["Param"] = "法院名称:%s,案件类型:%s,裁判日期:%s" \
                                     % (self.condition["court"], self.condition["case_type"],
                                        self.condition["date"])
        self.start_index = 1

    def start_requests(self):
        # 重置请求
        self.reset_req()

        try:
            request = FormRequest(
                url=self.list_url,
                callback=self.parse,
                formdata=self.req_data,
                headers=self.headers,
                dont_filter=True,
                errback=self.err_callback
            )
            self.set_proxy(request)
            yield request
        except Exception:
            self.exception_handle(self.condition, "start_requests error")

    def parse(self, response):
        self.exception_response(self.condition, response)
        self.logger.info("list_req_data->%s" % self.req_data)
        self.logger.info("start_index->%s" % self.start_index)

        try:
            result = response.text
            self.logger.info("parse response text->%s" % result)
            docs = json_loads(eval(result))

            total_count = 0
            for doc in docs:
                if "Count" in doc:
                    total_count = int(doc["Count"])
                    continue

                item = WenshuItem()
                item["case_type"] = doc.get("案件类型", "")
                item["sentence_date"] = doc.get("裁判日期", "")
                item["case_name"] = doc.get("案件名称", "")
                item["file_id"] = doc.get("文书ID", "")
                item["trial_procedure"] = doc.get("审判程序", "")
                item["case_no"] = doc.get("案号", "")
                item["court_name"] = doc.get("法院名称", "")
                item["relation"] = doc.get("关联文书", "")
                # 文书ID为空则跳过
                if not item["file_id"] or self.is_wenshu_id_exists(item["file_id"]):
                    self.logger.info("%s has saved!continue!" % item["file_id"])
                    continue
                self.logger.info("parse doc_req_data->%s" % item["file_id"])
                request = Request(
                    url=self.doc_url % item["file_id"],
                    callback=self.parse_doc,
                    meta={"item": item},
                    headers=self.headers,
                    dont_filter=True,
                    errback=self.err_callback
                )
                self.set_proxy(request)
                yield request

            # # 让数据起始值加分页大小，好下一次请求可以请求到下一页的数据,
            self.start_index += 1
            # # 记录查询条件的爬取状态(已经爬取过的状态改为1)
            self.record_query_condition(self.dict_sorted(self.condition), 1)
            # 查询结果至少第一页应该有数据，否则就可能是代理的问题
            if not docs and self.start_index <= 2:
                self.logger.info("查询结果至少第一页应该有数据，否则就可能是代理的问题")
                self.push_wenshu_condition(self.condition)
                self.proxy = self.proxy_api.get_proxy_one()  # 更换代理
                self.reset_req()

            # 如果start_index大于220了则读取下一个查询条件并改变查询的条件，且让start_index变为0
            if not docs or self.start_index > ceil(total_count / self.page_size):
                # 重置请求
                self.reset_req()
            self.req_data["Index"] = str(self.start_index)

            request = FormRequest(
                url=self.list_url,
                callback=self.parse,
                formdata=self.req_data,
                headers=self.headers,
                dont_filter=True,
                errback=self.err_callback
            )
            self.set_proxy(request)
            yield request
        except Exception:
            self.exception_handle(self.condition, "parse error")

    def parse_doc(self, response):
        self.exception_response(self.condition, response)
        self.logger.info("%s" % response.url)
        item = response.meta["item"]
        text = response.text
        try:
            self.logger.info("parse_doc_response->%s" % text)
            match_obj = self.data_pattern.search(text)
            if match_obj:
                content = match_obj.group(1).replace("\\", "")
                # 过滤掉反斜线
                content = content.replace("\\", "")
                doc = json_loads(content)
                item["title"] = doc.get("Title", "")  # 文书标题
                item["pub_date"] = doc.get("PubDate", "")  # 发布日期
                html = doc.get("Html", "")
                if html:  # 文书内容
                    item["html"] = '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8">' + html
            else:
                item["title"] = ""
                item["pub_date"] = ""
                item["html"] = ""
            yield item
        except Exception as e:
            self.record_wenshu_id_error(item["file_id"])
            self.exception_handle(self.condition, "parse_doc error:" + str(e))
