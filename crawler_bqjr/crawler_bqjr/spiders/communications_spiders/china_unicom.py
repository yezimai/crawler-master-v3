# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date
from itertools import islice
from random import randint
from re import compile as re_compile
from time import sleep, time
from urllib.parse import urlencode

from scrapy import Request, FormRequest

from crawler_bqjr.items.communications_items import UserStatus, CallType, MsgType, Sex
from crawler_bqjr.spider_class import CaptchaTimeout
from crawler_bqjr.spiders.communications_spiders.base import CommunicationsSpider
from crawler_bqjr.spiders_settings import COMMUNICATIONS_BRAND_DICT
from crawler_bqjr.utils import get_content_by_requests, get_response_by_requests, get_numbers_in_text, \
    get_js_time, get_month_last_date_by_date, get_last_month_from_date, get_in_nets_duration_by_start_date, \
    get_cookiejar_from_response, get_headers_from_response
from global_utils import json_loads


class ChinaUnicomSpider(CommunicationsSpider):
    """
    联通爬虫
    """
    name = COMMUNICATIONS_BRAND_DICT["联通"]
    allowed_domains = ["10010.com"]
    start_urls = ['https://uac.10010.com/portal/homeLogin']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.err_msg_pattern = re_compile(r",msg:'(.*?)'")

    def get_err_msg(self, text):
        try:
            return self.err_msg_pattern.search(text).group(1)
        except Exception:
            return text

    def _get_sms_send_sleep_time(self, meta):
        return max(meta["last_sms_time"] + 61 - time(), 0) if "last_sms_time" in meta else 0

    def _set_sms_captcha_headers_to_ssdb(self, username, response, cookies_dict):
        """将当前headers信息放入ssdb中"""
        headers = get_headers_from_response(response)
        if not headers.setdefault("cookie", ""):
            headers["cookie"] = ";".join(k + "=" + v for k, v in cookies_dict.items())
        else:
            headers["cookie"] += ";" + ";".join(k + "=" + v for k, v in cookies_dict.items())
        self.set_sms_captcha_headers_to_ssdb(headers, username)

    def get_unisecid_request(self, response):
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        the_time = get_js_time()

        url = "https://uac.10010.com/oauth2/genqr?" + the_time
        r = get_response_by_requests(url, headers=headers, cookie_jar=cookiejar)
        cookie = r.headers.get('Set-Cookie')
        result = {}
        k_v_list = cookie.split(';')
        name, value = k_v_list[0].split('=')
        result['name'] = name
        result['value'] = value
        for k_v in islice(k_v_list, 1, None):
            k, v = k_v.split('=', 1)
            result[k] = v

        return result

    def parse(self, response):
        yield from self.parse_again(response)

        # item = response.meta["item"]
        # try:
        #     # 联通是用JS设置的cookie，所以需要用phantomjs来执行JS获取cookie
        #     cookies = get_cookies_list_from_phantomjs(response.url, sleep_time=1)
        #     # uniseid = self.get_unisecid_request(response)
        #     # cookies.append(uniseid)
        #     yield Request(response.url, self.parse_again, cookies=cookies,
        #                   dont_filter=True, meta=response.meta, errback=self.err_callback)
        # except Exception:
        #     yield from self.except_handle(item["username"], "联通---登录入口")

    def parse_again(self, response):
        item = response.meta["item"]
        try:
            item["brand"] = "联通"
            username = item["username"]
            password = item["password"]

            if password:
                # 服务密码登录
                yield from self.get_login_request(response, username, password, "01")
            else:
                # 短信验证码登录
                yield from self.get_login_request(response, username, None, "02")
                # yield self.get_smsPwd_request(response, username)
        except CaptchaTimeout:
            yield from self.error_handle(item["username"], "联通---带cookie登录入口，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(item["username"], "联通---带cookie登录入口")

    def get_need_captcha_response(self, response, username, pwd_type="02"):
        """
        询问是否需要验证码
        """
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        the_time = get_js_time()
        form_data = {'userName': username,
                     'pwdType': pwd_type,
                     '_': int(the_time) + 1,
                     'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                     }
        url = "http://uac.10010.com/portal/Service/CheckNeedVerify?" + urlencode(form_data)
        return get_response_by_requests(url, headers=headers, cookie_jar=cookiejar)

    def cheek_need_img_captcha(self, response, username, pwd_type="02"):
        resp = self.get_need_captcha_response(response, username, pwd_type)
        return (b'"resultCode":"true"' in resp.content), resp.cookies.get_dict()

    def cheek_need_ck_captcha(self, response, username):
        resp = self.get_need_captcha_response(response, username, "01")
        info = resp.content
        return (b'"ckCode":"2"' in info or b'"ckCode":"3"' in info), resp.cookies.get_dict()

    def get_captcha(self, response, username="", cookie_dict=None):
        """
        获取验证码并识别，返回识别的验证码, cookies
        """
        # cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        url = "http://uac.10010.com/portal/Service/CreateImage?t=" + get_js_time()
        resp = get_response_by_requests(url, headers=headers, cookie_jar=cookie_dict)
        return resp.content, resp.cookies.get_dict()

    def get_ckPwd_request(self, response, username, cookie_dict=None):
        meta = response.meta
        sleep(self._get_sms_send_sleep_time(meta))
        the_time = get_js_time()
        form_data = {'mobile': username,
                     'req_time': the_time,
                     '_': int(the_time) + 1,
                     'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                     }
        # cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        url = "https://uac.10010.com/portal/Service/SendCkMSG?" + urlencode(form_data)
        resp = get_response_by_requests(url, headers=headers, cookie_jar=cookie_dict)
        meta["last_sms_time"] = time()
        text = resp.text
        return ('resultCode:"0000"' in text), text

    def verify_captcha(self, response, captcha_code, cookies_dict):
        """
        联通有一个url可以在不提交表单的情况下，先检查验证码是否正确
        返回是否正确
        """
        headers = get_headers_from_response(response)
        the_time = get_js_time()
        form_data = {'verifyCode': captcha_code,
                     'verifyType': "1",
                     '_': int(the_time) + 1,
                     'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                     }
        url = "https://uac.10010.com/portal/Service/CtaIdyChk?" + urlencode(form_data)
        info = get_content_by_requests(url, headers=headers, cookie_jar=cookies_dict)
        return b'"resultCode":"true"' in info

    def get_login_request(self, response, username, password=None, pwd_type="02"):
        """
        :param pwd_type: 02代表短信验证码，01代表服务密码
        """
        meta = response.meta
        the_time = get_js_time()
        form_data = {'userName': username,
                     'password': password,
                     'pwdType': pwd_type,
                     'productType': "01",
                     'redirectType': "01",
                     'rememberMe': "0",
                     'req_time': the_time,
                     'redirectURL': "https://uac.10010.com/cust/userinfo/userInfoInit",
                     '_': int(the_time) + 1,
                     'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                     }

        try:
            # 判断是否有验证码
            if "02" == pwd_type and password is None:
                headers = get_headers_from_response(response)
                self.set_sms_captcha_headers_to_ssdb(headers, username)
                sms_uid = self.need_sms_captcha_type(username, type="general")
                sms_password = self.ask_captcha_code(sms_uid)
                form_data['password'] = sms_password
                meta["sms_password"] = sms_password
            elif "01" == pwd_type:
                need_ck, cookies_dict = self.cheek_need_ck_captcha(response, username)
                meta["cookies_dict"] = cookies_dict
                if need_ck:
                    self._set_sms_captcha_headers_to_ssdb(username, response, cookies_dict)
                    ck_uid = self.need_sms_captcha_type(username, type="login")
                    ck_password = self.ask_captcha_code(ck_uid)
                    form_data['verifyCKCode'] = ck_password
                    meta["ck_password"] = ck_password
        except CaptchaTimeout:
            yield from self.error_handle(username, "联通---发送登录请求，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        else:
            meta.setdefault('cookies_dict', {})
            login_url = "https://uac.10010.com/portal/Service/MallLogin?" + urlencode(form_data)
            meta["login_url"] = login_url
            yield Request("https://uac.10010.com/portal/homeLogin", self.parse_homeLogin,
                          dont_filter=True, meta=meta, errback=self.err_callback)

    def parse_homeLogin(self, response):
        # 发送登录请求
        meta = response.meta
        yield Request(meta["login_url"], self.parse_login, dont_filter=True,
                      cookies=meta['cookies_dict'], meta=meta, errback=self.err_callback)

    def parse_login(self, response):
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        try:
            if 'resultCode:"0000"' in text:  # 登录成功
                self.crawling_login(item["username"])  # 通知授权成功

                # 获取号码信息，需要服务密码登录才能获取余额信息
                yield Request("https://uac.10010.com/cust/userinfo/getBindnumInfo",
                              self.parse_BindnumInfo, dont_filter=True,
                              meta=meta, errback=self.err_callback)
            elif 'resultCode:"7003"' in text or 'resultCode:"7002"' in text:
                # 7002是不支持简单密码登录
                # 7003是不支持初始密码登录
                # 使用短信验证码登录
                self.logger.info("联通---不支持简单/初始密码登录：(username:%s, password:%s) %s，即将使用短信验证码登录。"
                                 % (item["username"], item["password"], text))
                yield from self.get_login_request(response, item["username"], None, "02")
                # yield self.get_smsPwd_request(response, item["username"])
            elif 'resultCode:"7007"' in text:  # 7007是服务密码错误，使用短信验证码登录
                meta["passwd_err"] = 1
                # tell_msg = "服务密码错误，请刷新页面重试。(如忘记密码，请输入123456)"
                self.logger.info("联通---服务密码错误：(username:%s, password:%s) %s"
                                 % (item["username"], item["password"], text))
                # yield self.get_smsPwd_request(response, item["username"])
                yield from self.get_login_request(response, item["username"], None, "02")
            elif 'resultCode:"7001"' in text:  # 7001是ck验证码错误
                username = item["username"]
                if "sms_password" in meta:
                    pwd_type = "02"
                    password = meta["sms_password"]
                else:
                    pwd_type = "01"
                    password = item["password"]
                self.logger.info("联通---ck验证码错误：(username:%s, password:%s) %s，重新登录。"
                                 % (item["username"], item["password"], text))
                yield from self.get_login_request(response, username, password, pwd_type)
            elif 'resultCode:"7038"' in text or 'resultCode:"7231"' in text:  # 7038是动态随机密码不正确
                # tell_msg = "短信验证码错误，请刷新页面重试。"
                self.logger.info("联通---短信验证码错误：(username:%s, password:%s) %s，重新登录。"
                                 % (item["username"], item["password"], text))
                yield from self.get_login_request(response, username, None, "02")
            else:
                # 7217是系统忙，请稍后再试
                # 7299是尝试次数过多，请次日重试
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "联通---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except CaptchaTimeout:
            yield from self.error_handle(item["username"], "联通---解析登录失败，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(item["username"], "联通---解析登录失败: %s" % text)

    def parse_BindnumInfo(self, response):
        """
        解析号码信息
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"result_code":"0000"' in text:  # 成功
                datas = json_loads(text)["defBindnumInfo"]
                balance = datas["costInfo"].get("balance")
                item["balance"] = float(balance) if balance is not None else None
            elif '"result_code":"0001"' not in text:  # 0001是不允许短信验证码查询余额
                self.logger.error("联通---获取号码信息失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 获取身份证信息
            yield Request("http://iservice.10010.com/e3/static/check/checklogin?_="
                          + get_js_time(), self.parse_checklogin, dont_filter=True,
                          meta=meta, method="POST", errback=self.err_callback)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析号码信息失败: %s" % text)

    def parse_checklogin(self, response):
        """
        解析身份证信息
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"userInfo":' in text:  # 成功
                datas = json_loads(text)["userInfo"]

                opendate = datas["opendate"]
                registration_time = opendate[:4] + "-" + opendate[4:6] + "-" + opendate[6:8]
                item["registration_time"] = registration_time
                item["in_nets_duration"] = get_in_nets_duration_by_start_date(registration_time)
                item["identification_number"] = datas["certnum"]
                item["identification_addr"] = datas["certaddr"]
                item["real_name"] = datas["custName"]
                item["sex"] = Sex.Male if datas["custsex"] == "1" else Sex.Female
                item["package"] = datas["brand_name"] + "-" + datas["packageName"]
                item["status"] = UserStatus.Opened if datas["status"] == "开通" else UserStatus.Shutdown
            else:
                self.logger.error("联通---获取身份证信息失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # # 获取是否实名制
            # yield Request("http://iservice.10010.com/e3/static/transact/supRegistCheckController"
            #               "?_=" + get_js_time(), self.parse_supRegistCheck, dont_filter=True,
            #               meta=meta, method="POST", errback=self.err_callback)

            # 获取通话记录
            sleep(0.6)
            meta["call_count"] = 0
            item["history_call"] = defaultdict(dict)
            yield self._get_callDetail_request(response, date.today())
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析身份证信息失败: %s" % text)

    def parse_supRegistCheck(self, response):
        """
        解析是否实名制，此函数已没有调用
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"issuccess":true' in text:  # 成功
                item["is_real_name"] = (json_loads(text)["result"]["checktype"] != "1")
            else:
                self.logger.error("联通---获取是否实名制失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 获取过去6个月的账单信息
            sleep(0.6)
            meta["bill_count"] = 0
            item["history_bill"] = defaultdict(dict)
            yield self._get_historyBill_request(response, date.today())
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析是否实名制失败: %s" % text)

    def _get_callDetail_request(self, response, this_month):
        """
        返回通话记录请求
        """
        meta = response.meta
        meta["last_call_month"] = this_month
        meta["call_count"] += 1
        form_data = {"pageNo": "1",
                     "pageSize": str(self.CALL_PAGE_SIZE_LIMIT),
                     "beginDate": this_month.strftime("%Y-%m-01"),
                     "endDate": get_month_last_date_by_date(this_month)
                     }
        # sleep(0.6)
        return FormRequest("http://iservice.10010.com/e3/static/query/callDetail?_="
                           + get_js_time(), self.parse_callDetail, dont_filter=True, meta=meta,
                           formdata=form_data, errback=self.err_callback)

    def parse_callDetail(self, response):
        """
        解析通话记录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            this_month = meta["last_call_month"]
            this_month_str = this_month.strftime("%Y%m")
            if '"pageMap":' in text:
                datas = json_loads(text)["pageMap"]

                the_call_count = datas.get("totalCount", 0)
                if the_call_count > self.CALL_PAGE_SIZE_LIMIT:
                    self.logger.error("联通---单月通话次数过大：username:%s, "
                                      "password:%s, month:%s, totalCount:%d"
                                      % (item["username"], item["password"], this_month, the_call_count))

                call_list = [{"time": call["calldate"] + " " + call["calltime"],
                              "duration": ":".join("%02d" % int(i) for i
                                                   in get_numbers_in_text(call["calllonghour"])),
                              "type": CallType.Caller if "主叫" == call["calltypeName"] else CallType.Called,
                              "other_num": call["othernum"],
                              "my_location": call["homeareaName"],
                              "other_location": call["calledhome"],
                              "fee": float(call["totalfee"]),
                              "land_type": call["landtype"],
                              }
                             for call in datas["result"]]

                if len(call_list) != the_call_count:
                    self.logger.error("联通---通话次数异常：username:%s, password:%s, "
                                      "month:%s, totalCount:%d, call_list_len:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_call_count, len(call_list)))

                item["history_call"][this_month_str] = call_list
            elif 'respCode":"2114030170"' in text:  # 无通话
                item["history_call"][this_month_str] = []
            elif "call_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("联通---重试通话记录：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(0.6)
                request = response.request.copy()
                request.meta["call_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("联通---获取通话记录失败：(username:%s, password:%s, month:%s) %s"
                                  % (item["username"], item["password"], this_month, text))

            # 继续获取另一个月的通话记录
            if meta["call_count"] < self.CALL_COUNT_LIMIT:  # 只需要最近6个月的
                last_month = get_last_month_from_date(this_month)
                yield self._get_callDetail_request(response, last_month)
            else:
                # 获取过去6个月的账单信息
                meta["bill_count"] = 0
                item["history_bill"] = defaultdict(dict)
                yield self._get_historyBill_request(response, date.today())

                # # 获取过去6个月的短信记录
                # meta["msg_count"] = 0
                # item["history_msg"] = defaultdict(dict)
                # this_month = date.today()
                # meta["msg_" + this_month.strftime("%Y%m") + "_retry"] = 1
                # yield self._get_msgDetail_request(response, this_month)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析通话记录失败: %s" % text)

    def _get_msgDetail_request(self, response, this_month):
        """
        返回短信记录请求
        """
        meta = response.meta
        meta["last_msg_month"] = this_month
        meta["msg_count"] += 1
        form_data = {"pageNo": "1",
                     "pageSize": str(self.CALL_PAGE_SIZE_LIMIT),
                     "begindate": this_month.strftime("%Y%m01"),
                     "enddate": get_month_last_date_by_date(this_month).replace("-", "")
                     }
        # sleep(0.6)
        return FormRequest("http://iservice.10010.com/e3/static/query/sms?_="
                           + get_js_time(), self.parse_msgDetail, dont_filter=True,
                           meta=meta, formdata=form_data, errback=self.err_callback)

    def parse_msgDetail(self, response):
        """
        解析短信记录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            this_month = meta["last_msg_month"]
            this_month_str = this_month.strftime("%Y%m")
            if '"pageMap":' in text:
                datas = json_loads(text)["pageMap"]

                the_msg_count = datas.get("totalCount", 0)
                if the_msg_count > self.CALL_PAGE_SIZE_LIMIT:
                    self.logger.error("联通---单月短信次数过大：username:%s, "
                                      "password:%s, month:%s, totalCount:%d"
                                      % (item["username"], item["password"], this_month, the_msg_count))

                msg_list = [{"time": msg["smsdate"] + " " + msg["smstime"],
                             "type": MsgType.Send if "2" == msg["smstype"] else MsgType.Receive,
                             "other_num": msg["othernum"],
                             }
                            for msg in datas["result"]]

                if len(msg_list) != the_msg_count:
                    self.logger.error("联通---短信次数异常：username:%s, password:%s, "
                                      "month:%s, totalCount:%d, msg_list_len:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_msg_count, len(msg_list)))

                item["history_msg"][this_month_str] = msg_list
            elif 'respCode":"2114030170"' in text:  # 无记录
                item["history_msg"][this_month_str] = []
            elif "msg_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("联通---重试短信记录：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(0.6)
                request = response.request.copy()
                request.meta["msg_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("联通---获取短信记录失败：(username:%s, password:%s, month:%s) %s"
                                  % (item["username"], item["password"], this_month, text))

            # 继续获取另一个月的通话记录
            if meta["msg_count"] < self.CALL_COUNT_LIMIT:  # 只需要最近6个月的
                last_month = get_last_month_from_date(this_month)
                yield self._get_msgDetail_request(response, last_month)
            else:
                # 获取过去6个月的账单信息
                meta["bill_count"] = 0
                item["history_bill"] = defaultdict(dict)
                yield self._get_historyBill_request(response, date.today())
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析短信记录失败: %s" % text)

    def _get_historyBill_request(self, response, this_month):
        """
        返回账单请求
        """
        meta = response.meta
        last_month = get_last_month_from_date(this_month)
        meta["last_bill_month"] = last_month
        meta["bill_count"] += 1  # 请求次数加1
        form_data = {"querytype": "0001",
                     "querycode": "0001",
                     "billdate": last_month.strftime("%Y%m"),  # 指定请求的月份
                     "flag": "2"
                     }
        # sleep(0.6)
        return FormRequest("http://iservice.10010.com/e3/static/query/queryHistoryBill?_="
                           + get_js_time(), self.parse_queryHistoryBill, dont_filter=True,
                           meta=meta, formdata=form_data, errback=self.err_callback)

    def parse_queryHistoryBill(self, response):
        """
        解析账单
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            this_month = meta["last_bill_month"]
            this_month_str = this_month.strftime("%Y%m")
            if '"result":' in text:
                datas = json_loads(text)["result"]
                fee = datas.get("allfee")
                if fee is not None:
                    fee = float(fee)
                item["history_bill"][this_month_str] = {"all_fee": fee}
            elif '"historyResultList"' in text and "企业套餐" in text:
                yield item
                yield from self.error_handle(item["username"], "联通---暂不支持企业套餐用户验证。",
                                             "联通---暂不支持企业套餐用户验证。")
                return
            elif "bill_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("联通---重试账单：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(0.6)
                request = response.request.copy()
                request.meta["bill_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("联通---获取账单失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 继续获取另一个月的账单
            if meta["bill_count"] < self.BILL_COUNT_LIMIT:  # 只需要最近6个月的
                yield self._get_historyBill_request(response, this_month)
            else:
                # 获取交费记录
                meta["payment_count"] = 0
                item["history_payment"] = defaultdict(dict)
                yield self._get_payment_request(response, date.today())
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析账单失败: %s" % text)

    def _get_payment_request(self, response, this_month):
        """
        返回交费记录请求
        """
        meta = response.meta
        meta["last_payment_month"] = this_month
        meta["payment_count"] += 1
        form_data = {"pageNo": "1",
                     "pageSize": str(self.CALL_PAGE_SIZE_LIMIT),
                     "beginDate": this_month.strftime("%Y%m01"),
                     "endDate": min(date.today().strftime("%Y%m%d"),
                                    get_month_last_date_by_date(this_month).replace("-", ""))
                     }
        # sleep(0.6)
        return FormRequest("http://iservice.10010.com/e3/static/query/paymentRecord?_="
                           + get_js_time(), self.parse_payment, dont_filter=True, meta=meta,
                           formdata=form_data, errback=self.err_callback)

    def parse_payment(self, response):
        """
        解析交费记录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            this_month = meta["last_payment_month"]
            this_month_str = this_month.strftime("%Y%m")
            if '"pageMap":' in text:
                datas = json_loads(text)["pageMap"]

                the_payment_count = datas.get("totalCount", 0)
                if the_payment_count > self.CALL_PAGE_SIZE_LIMIT:
                    self.logger.error("联通---单月交费次数过大：username:%s, "
                                      "password:%s, month:%s, totalCount:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_payment_count))

                payment_list = [{"time": payment["paydate"],
                                 "fee": float(payment["payfee"]),
                                 "channel": payment["payment"],
                                 }
                                for payment in datas["result"]]

                if len(payment_list) != the_payment_count:
                    self.logger.error("联通---交费次数异常：username:%s, password:%s, "
                                      "month:%s, totalCount:%d, payment_list_len:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_payment_count, len(payment_list)))

                item["history_payment"][this_month_str] = payment_list
            elif 'respCode":"2114000283"' in text:  # 无交费记录
                item["history_payment"][this_month_str] = []
            elif "payment_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("联通---重试交费记录：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(0.6)
                request = response.request.copy()
                request.meta["payment_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("联通---获取交费记录失败：(username:%s, password:%s, month:%s) %s"
                                  % (item["username"], item["password"], this_month, text))

            # 继续获取另一个月的交费记录
            if meta["payment_count"] < self.CALL_COUNT_LIMIT:  # 只需要最近6个月的
                last_month = get_last_month_from_date(this_month)
                yield self._get_payment_request(response, last_month)
            else:
                # 处理完，返回爬取的结果
                yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "联通---解析交费记录失败: %s" % text)
