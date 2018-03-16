# -*- coding: utf-8 -*-

from hashlib import sha1
from time import localtime
from urllib.parse import quote

from scrapy.http import FormRequest

from crawler_bqjr.spiders.housefund_spiders.base import HousefundSpider
from crawler_bqjr.spiders_settings import HOUSEFUND_CITY_DICT
from crawler_bqjr.utils import get_js_time
from global_utils import json_loads


class HousefundChengduSpider(HousefundSpider):
    name = HOUSEFUND_CITY_DICT["成都"]
    allowed_domains = ["m.cdzfgjj.gov.cn"]
    start_urls = ["http://m.cdzfgjj.gov.cn/cdnt/mt/router", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.req_url = self._start_url_
        self.app_key = "e33ff3416588cc973d83"  # app key
        self.app_secret = "0efaeb4f88b73917a783"  # 签名的秘钥
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/5.0 (Linux; Android 7.0; FRD-AL10 Build/HUAWEIFRD-AL10; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/55.0.2883.91 Mobile Safari/537.36 Appcan/3.1",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://m.cdzfgjj.gov.cn",
            "Referer": "http://m.cdzfgjj.gov.cn/cdnt/weixin/app/login.html",
            "X-Requested-With": "XMLHttpRequest",
        }

        self.user_login = "user.login"
        self.user_perInfo = "user.perInfo"
        self.user_getPerDepRecord = "user.getPerDepRecord"
        self.user_getPerFetchRecord = "user.getPerFetchRecord"
        self.user_queryPerLoanAccount = "user.queryPerLoanAccount"
        self.user_queryRepayRecord = "user.queryRepayRecord"

    def parse(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            self.logger.info("请求登录接口->%s" % self.user_login)
            req_data = self.get_req_data(self.user_login, loginacc=item["username"], loginpwd=item["password"])
            # 请求登录接口
            yield FormRequest(
                url=self.req_url,
                callback=self.parse_login,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---爬虫解析入口异常")

    def parse_login(self, response):
        """
        登录处理
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            msg = info["resmsg"]

            if "resmsg" in info and msg:
                yield from self.error_handle(item["username"], msg, tell_msg=msg)
                return
            item["mobile"] = info.get("phone", "")

            # 请求个人账户信息接口
            self.logger.info("请求个人账户信息接口->%s" % self.user_perInfo)
            req_data = self.get_req_data(self.user_perInfo)
            yield FormRequest(
                url=self.req_url,
                callback=self.parse_perInfo,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---登录数据解析异常")

    def parse_perInfo(self, response):
        """
        个人账户信息处理
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            item["private_no"] = info.get("percode", "")
            item["real_name"] = info.get("pername", "")
            item["birthday"] = info.get("birthday", "")
            item["identification_number"] = info.get("codeno", "")
            item["identification_type"] = info.get("codetype", "")
            item["phone"] = info.get("fixedphone", "")
            item["nation"] = info.get("nation", "")
            item["sex"] = info.get("sex", "")
            item["signflag"] = info.get("signflag", "")
            item["mail"] = info.get("mail", "")
            item["remark"] = info.get("remark", "")
            # 按照items重命名字段对应名称
            new_acct = list()
            for acct in info.get("acct", []):
                acct_dict = dict()
                acct_dict["private_no"] = acct["percode"]
                acct_dict["corpcode"] = acct["corpcode"]
                acct_dict["corpname"] = acct["corpname"]
                acct_dict["accmny"] = acct["accmny"]
                acct_dict["mperpaystate"] = acct["mperpaystate"]
                acct_dict["basemny"] = acct["basemny"]
                acct_dict["corpscale"] = acct["corpscale"]
                acct_dict["perscale"] = acct["perscale"]
                acct_dict["perdepmny"] = acct["perdepmny"]
                acct_dict["corpdepmny"] = acct["corpdepmny"]
                acct_dict["mpayendmnh"] = acct["mpayendmnh"]
                new_acct.append(acct_dict)
            item["account_detail"] = new_acct

            # 根据当前日期生成最近三年的年份
            year_list = self.get_queryyear()
            year = year_list.pop()
            meta["year_list"] = year_list
            meta["detail_list"] = list()

            # 请求个人明细账(汇补缴明细)接口
            self.logger.info("请求缴存明细接口->%s" % self.user_getPerDepRecord)
            req_data = self.get_req_data(self.user_getPerDepRecord, year=year)
            yield FormRequest(
                url=self.req_url,
                callback=self.parse_getPerDepRecord,
                headers=self.headers,
                meta=meta,
                formdata=req_data,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---个人账户信息数据解析异常")

    def parse_getPerDepRecord(self, response):
        """
        缴存明细接口
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        year_list = meta["year_list"]
        detail_list = meta["detail_list"]
        try:
            info = json_loads(response.text)
            new_detail = list()
            for detail in info.get("list", []):
                detail_dict = dict()
                detail_dict["acctime"] = detail["acctime"]
                detail_dict["bustype"] = detail["bustype"]
                detail_dict["depmny"] = detail["depmny"]
                detail_dict["corpdepmny"] = detail["corpdepmny"]
                detail_dict["perdepmny"] = detail["perdepmny"]
                detail_dict["corpcode"] = detail["corpcode"]
                detail_dict["corpname"] = detail["corpname"]
                detail_dict["remark"] = detail["remark"]
                new_detail.append(detail_dict)
            detail_list.append(new_detail)

            if year_list:
                year = year_list.pop()
                meta["year_list"] = year_list
                meta["detail_list"] = detail_list
                self.logger.info("请求缴存明细接口->%s" % self.user_getPerDepRecord)
                req_data = self.get_req_data(self.user_getPerDepRecord, year=year)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_getPerDepRecord,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                item["payment_detail"] = list()
                for detail in detail_list:
                    item["payment_detail"].extend(detail)

                # 根据当前日期生成最近三年的年份
                year_list = self.get_queryyear()
                year = year_list.pop()
                meta["year_list"] = year_list
                meta["detail_list"] = list()

                # 请求个人明细账(提取明细)接口
                self.logger.info("请求提取明细接口->%s" % self.user_getPerFetchRecord)
                req_data = self.get_req_data(self.user_getPerFetchRecord, year=year)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_getPerFetchRecord,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---缴存明细信息数据解析异常")

    def parse_getPerFetchRecord(self, response):
        """
        个人明细账(提取明细)
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        year_list = meta["year_list"]
        detail_list = meta["detail_list"]
        try:
            info = json_loads(response.text)
            detail_info = info.get("list", [])
            detail_list.append(detail_info)

            if year_list:
                year = year_list.pop()
                meta["year_list"] = year_list
                meta["detail_list"] = detail_list
                self.logger.info("请求提取明细接口->%s" % self.user_getPerFetchRecord)
                req_data = self.get_req_data(self.user_getPerFetchRecord, year=year)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_getPerFetchRecord,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                item["fetch_detail"] = list()
                for detail in detail_list:
                    item["fetch_detail"].extend(detail)

                del meta["year_list"]
                del meta["detail_list"]

                self.logger.info("请求贷款信息接口->%s" % self.user_queryPerLoanAccount)
                req_data = self.get_req_data(self.user_queryPerLoanAccount)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_queryPerLoanAccount,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---提取明细信息数据解析异常")

    def parse_queryPerLoanAccount(self, response):
        """
        贷款信息接口
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            info = json_loads(response.text)
            loan = info.get("list", {})
            info_dict = dict()
            info_dict["agrcode"] = loan["agrcode"]
            info_dict["loancode"] = loan["loancode"]
            info_dict["loanbank"] = loan["loanbank"]
            info_dict["depname"] = loan["depname"]
            info_dict["repayway"] = loan["repayway"]
            info_dict["loanbal"] = loan["loanbal"]
            info_dict["ratetotal"] = loan["ratetotal"]
            info_dict["nobase"] = loan["nobase"]
            info_dict["norate"] = loan["norate"]
            info_dict["address"] = loan["address"]
            info_dict["mntpay"] = loan["mntpay"]
            info_dict["loanmnhs"] = loan["loanmnhs"]
            info_dict["loanmny"] = loan["loanmny"]

            item["loan_detail"] = info_dict
            if info_dict:
                year_list = self.get_queryyear()
                year = year_list.pop()
                meta["year_list"] = year_list
                meta["detail_list"] = list()

                # 请求还款记录接口
                loancode = info_dict["agrcode"]
                self.logger.info("请求还款记录接口->%s" % self.user_queryRepayRecord)
                req_data = self.get_req_data(self.user_queryRepayRecord, year=year, loancode=loancode)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_queryRepayRecord,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---贷款信息数据解析异常")

    def parse_queryRepayRecord(self, response):
        """
        还款记录
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        year_list = meta["year_list"]
        detail_list = meta["detail_list"]
        try:
            info = json_loads(response.text)
            new_info = list()
            for loan in info.get("list", []):
                info_dict = dict()
                info_dict["ratemny"] = loan["ratemny"]
                info_dict["basemny"] = loan["basemny"]
                info_dict["bkdate"] = loan["bkdate"]
                info_dict["paytype"] = loan["paytype"]
                info_dict["loanrate"] = loan["loanrate"]
                info_dict["loanbal"] = loan["loanbal"]
                new_info.append(info_dict)
            detail_list.append(new_info)

            if year_list:
                year = year_list.pop()
                meta["year_list"] = year_list
                meta["detail_list"] = detail_list
                loancode = item["loan_detail"]["agrcode"]
                self.logger.info("请求还款记录接口->%s" % self.user_queryRepayRecord)
                req_data = self.get_req_data(self.user_queryRepayRecord, year=year, loancode=loancode)
                yield FormRequest(
                    url=self.req_url,
                    callback=self.parse_queryRepayRecord,
                    headers=self.headers,
                    meta=meta,
                    formdata=req_data,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                item["repayment_detail"] = list()
                for detail in detail_list:
                    item["repayment_detail"].extend(detail)
                del meta["year_list"]
                del meta["detail_list"]

                # 抓取完成
                yield from self.crawling_done(item)

        except Exception:
            yield from self.except_handle(item["username"], "成都公积金中心---还款记录信息数据解析异常")

    def get_queryyear(self):
        now_year = int(localtime().tm_year)
        return [str(year) for year in range(now_year - 2, now_year + 1)]

    def get_sign(self, data):
        """
        生成sha1签名
        :param data:
        :return:
        """
        if not data:
            data = {}
        sign_str = self.app_secret
        sign_str += "".join(k + quote(data[k]) for k in sorted(data.keys()))
        sign_str += self.app_secret
        hash_method = sha1()
        hash_method.update(sign_str.encode('utf-8'))
        return hash_method.hexdigest()

    def get_req_data(self, method, loginacc=None, loginpwd=None, year=None, loancode=None):
        data = dict()
        if method == self.user_login:
            data["loginacc"] = loginacc
            data["loginpwd"] = loginpwd
        elif method == self.user_queryRepayRecord:
            data["loanConNo"] = loancode
        elif method in [self.user_getPerDepRecord,
                        self.user_getPerFetchRecord,
                        self.user_queryRepayRecord]:
            data["year"] = year

        data["method"] = method
        data["v"] = "1.0"
        data["appkey"] = self.app_key
        data["timestamp"] = get_js_time()  # 获取当前系统时间戳
        data["sign"] = self.get_sign(data)

        return data
