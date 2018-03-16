# -*- coding: utf-8 -*-

from scrapy.http import FormRequest

from crawler_bqjr.spiders.housefund_spiders.base import HousefundSpider
from crawler_bqjr.spiders_settings import HOUSEFUND_CITY_DICT
from global_utils import json_loads


class HousefundGuangzhouSpider(HousefundSpider):
    name = HOUSEFUND_CITY_DICT["广州"]
    allowed_domains = ["gzgjj.gov.cn"]
    start_urls = ["https://gzgjj.gov.cn:8180/app/user/login", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.userdeposit_url = "https://gzgjj.gov.cn:8180/app/query/userDeposit"  # 缴存信息
        self.userview_url = "https://gzgjj.gov.cn:8180/app/query/userView"  # 缴存明细
        self.userloan_url = "https://gzgjj.gov.cn:8180/app/query/userLoan"  # 贷款信息
        self.userrepayment_url = "https://gzgjj.gov.cn:8180/app/query/userRepayment"  # 贷款还款明细
        self.extraction_url = "https://gzgjj.gov.cn:8180/app/query/extraction"  # 提取进度查询

        self.key = "FDDF3D15B98D5551EC9D16539309395B"
        self.version = "1.0"

        self.headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "Mozilla/5.0 (Linux; Android 7.0; FRD-AL10 Build/HUAWEIFRD-AL10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/55.0.2883.91 Mobile Safari/537.36 Appcan/3.1",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def parse(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            req_data = {
                "yhmm": item["password"],
                "dllx": "0",
                "qqly": "1001",
                "yhhm": item["username"],
                "key": self.key,
                "version": self.version,
            }
            # 请求登录接口
            yield FormRequest(
                url=response.url,
                callback=self.parse_login,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---爬虫解析入口异常")

    def parse_login(self, response):
        """
        登录数据解析
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            data = info["datalist"][0]

            if data["jyjg"] != "1":
                msg = data["sbyy"]
                yield from self.error_handle(item["username"], msg, tell_msg=msg)
                return
            else:
                item["mobile"] = data.get("sjhm", "")
                item["private_no"] = data.get("gjjzh", "")
                item["real_name"] = data.get("xm", "")
                item["identification_number"] = data.get("zjh", "")
                item["identification_type"] = "身份证"

            # 请求缴存信息接口
            self.logger.info("请求缴存信息接口->%s" % self.userdeposit_url)
            req_data = {
                "gjjzh": item["private_no"],
                "zjh": item["identification_number"],
                "qqly": "1001",
                "key": self.key,
                "version": self.version,
            }
            yield FormRequest(
                url=self.userdeposit_url,
                callback=self.parse_userdeposit,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---登录数据解析异常")

    def parse_userdeposit(self, response):
        """
        缴存信息处理
        :param self:
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            new_acct = list()
            for acct in info.get("datalist", []):
                acct_dict = dict()
                acct_dict["private_no"] = acct["gjjzh"]
                acct_dict["corpcode"] = acct["dwdjh"]
                acct_dict["corpname"] = acct["dwmc"]
                acct_dict["accmny"] = acct["ye"]
                acct_dict["mperpaystate"] = acct["zhztms"]
                acct_dict["basemny"] = acct["grjcjs"]
                acct_dict["corpscale"] = acct["dwjcbl"]
                acct_dict["perscale"] = acct["grjcbl"]
                acct_dict["perdepmny"] = acct["grjce"]
                acct_dict["corpdepmny"] = acct["dwjce"]
                new_acct.append(acct_dict)
            item["account_detail"] = new_acct

            # 请求缴存明细接口
            self.logger.info("请求缴存明细接口->%s" % self.userview_url)
            req_data = {
                "pageno": "1",
                "gjjzh": item["private_no"],
                "pagesize": "20",
                "qqly": "1001",
                "key": self.key,
                "version": self.version,
            }
            yield FormRequest(
                url=self.userview_url,
                callback=self.parse_userview,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---缴存信息数据解析异常")

    def parse_userview(self, response):
        """
        缴存明细信息处理
        :param self:
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            new_data = list()
            for data in info.get("datalist", []):
                data_dict = dict()
                data_dict["depmny"] = data["fse"]
                data_dict["acctime"] = data["ywrq"]
                data_dict["bustype"] = data["ywlxms"]
                new_data.append(data_dict)
            item["payment_detail"] = new_data

            # 请求贷款信息接口
            self.logger.info("请求贷款信息接口->%s" % self.userloan_url)
            req_data = {
                "zjh": item["identification_number"],
                "qqly": "1001",
                "key": self.key,
                "version": self.version,
            }
            yield FormRequest(
                url=self.userloan_url,
                callback=self.parse_userloan,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---缴存明细数据解析异常")

    def parse_userloan(self, response):
        """
        贷款信息处理
        :param self:
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            item["loan_detail"] = info.get("datalist", [])

            # 请求贷款还款明细
            self.logger.info("请求还款明细接口->%s" % self.userrepayment_url)
            req_data = {
                "pageno": "1",
                "gjjzh": item["private_no"],
                "pagesize": "20",
                "zjh": item["identification_number"],
                "qqly": "1001",
                "key": self.key,
                "version": self.version,
            }
            yield FormRequest(
                url=self.userrepayment_url,
                callback=self.parse_userrepayment,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---贷款信息解析异常")

    def parse_userrepayment(self, response):
        """
        贷款还款明细
        :param self:
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            item["repayment_detail"] = info.get("datalist", [])

            # 请求提取进度
            self.logger.info("请求提取进度接口->%s" % self.extraction_url)
            req_data = {
                "gjjzh": item["private_no"],
                "qqly": "1001",
                "key": self.key,
                "version": self.version,
            }
            yield FormRequest(
                url=self.extraction_url,
                callback=self.parse_extraction,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心---贷款还款明细解析异常")

    def parse_extraction(self, response):
        """
        贷款还款明细
        :param self:
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            item["fetch_detail"] = info.get("datalist", [])

            # 抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "广州公积金中心--提取进度解析异常")
