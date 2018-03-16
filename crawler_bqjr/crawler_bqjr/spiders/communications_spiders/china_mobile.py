# -*- coding: utf-8 -*-

from base64 import b64encode
from collections import defaultdict
from datetime import date
from random import randint, random as rand_0_1, choice as rand_choice
from re import compile as re_compile
from time import time, sleep
from urllib.parse import urlencode

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from dateutil.relativedelta import relativedelta
from requests import get as http_get
from scrapy import Request
from scrapy.spidermiddlewares.httperror import HttpError

from crawler_bqjr.items.communications_items import UserStatus, CallType, MsgType
from crawler_bqjr.spider_class import CaptchaTimeout
from crawler_bqjr.spiders.communications_spiders.base import CommunicationsSpider
from crawler_bqjr.spiders_settings import COMMUNICATIONS_BRAND_DICT, CHINA_MOBILE_ENCRYPT_PUBLIC_KYE
from crawler_bqjr.utils import get_content_by_requests, get_content_by_requests_post, \
    get_numbers_in_text, get_in_nets_duration_by_start_date, get_last_month_from_date, \
    get_js_time, get_headers_from_response, get_cookiejar_from_response
from global_utils import json_loads
from proxy_api.proxy_check import get_web_html_by_requests as get_web_html_by_proxy


class ChinaMobileSpider(CommunicationsSpider):
    name = COMMUNICATIONS_BRAND_DICT["移动"]
    allowed_domains = ["10086.cn"]
    start_urls = ['https://login.10086.cn/login.html']

    custom_settings = {
        'REDIRECT_ENABLED': False,  # getArtifact会返回302重定向网页并set-cookies，Scrapy暂不支持重定向set-cookies，所以关闭重定向功能
        'HTTPERROR_ALLOWED_CODES': [302],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_detail_step = 200
        self.payment_channel_dic = {'01': '现金交费',
                                    '02': '充值卡充值',
                                    '03': '银行托收',
                                    '04': '营销活动预存受理',
                                    '05': '积分换话费业务受理',
                                    '06': '第三方支付',
                                    '07': '手机钱包',
                                    '08': '空中充值',
                                    '09': '代理商渠道办理',
                                    '10': '批量冲销',
                                    '11': '调账',
                                    '12': '其他',
                                    }
        self.err_msg_pattern = re_compile(r',"(?:desc|retMsg)":"(.*?)"')

    def pwd_encrypt(self, pwd):
        """移动服务密码加密"""
        rsakey = RSA.importKey(CHINA_MOBILE_ENCRYPT_PUBLIC_KYE)
        cipher = PKCS1_v1_5.new(rsakey)
        encry_pwd = cipher.encrypt(pwd.encode())
        return b64encode(encry_pwd).decode()

    def get_err_msg(self, text):
        try:
            return self.err_msg_pattern.search(text).group(1)
        except Exception:
            return text

    def get_logout_request(self, meta):
        return Request("http://shop.10086.cn/i/v1/auth/userlogout?_=" + get_js_time(),
                       self.parse_logout, dont_filter=True, meta=meta, errback=self.parse_logout)

    def get_logout_by_request(self, headers, cookies=None):
        """使用requests登出"""
        url = "http://shop.10086.cn/i/v1/auth/userlogout?_=" + get_js_time()
        http_get(url, headers=headers, cookies=cookies)

    def _get_a_proxy(self):
        req_header = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                      'Accept-Language': 'zh-CN,zh',
                      'Connection': 'close',
                      }
        check_url = "http://shop.10086.cn/i/v1/fee/real/15928016431?_=" + get_js_time()

        for proxy in self.proxy_api.get_proxy_all():
            if proxy in self.bad_proxy:
                continue

            try:
                resp = http_get(check_url, headers=req_header, timeout=3,
                                proxies={'https': 'https://' + proxy})
                if b'"retCode":"' in resp.content:
                    resp = get_web_html_by_proxy("https://login.10086.cn/captchazh.htm?type=12",
                                                 proxies={'https': 'https://' + proxy})
                    if resp is not None:
                        return proxy
            except Exception:
                self.logger.error("proxy error")

            self.bad_proxy.add(proxy)
        else:
            return rand_choice(list(self.good_proxy))

    def add_proxy(self, meta):
        proxy = self._get_a_proxy()
        meta["proxy"] = "https://" + proxy
        self.good_proxy.add(proxy)
        return

    def _retry_request(self, response):
        """
            重发请求
        """
        meta = response.meta
        retry_count = meta.setdefault("retry_count", 0)
        item = meta["item"]

        if retry_count < self.CAPTCHA_RETRY_TIMES:
            self.logger.error("移动---系统繁忙，重试：(username:%s, password:%s) %s"
                              % (item["username"], item["password"], response.text))
            sleep(1)
            request = response.request.copy()
            request.meta["retry_count"] += 1
            yield request
        else:
            username = item["username"]
            text = response.text
            yield from self.error_handle(username,
                                         "移动---请求重试多次失败：(username:%s, password:%s) %s"
                                         % (username, item["password"], text),
                                         tell_msg=self.get_err_msg(text),
                                         logout_request=self.get_logout_request(meta))

    def err_callback(self, failure):
        self.logger.error(repr(failure))

        try:
            request = failure.request
            meta = request.meta

            retry_count = meta.setdefault("err_callback_retry", 0)
            if retry_count < 50:
                sleep(0.1)
                new_request = request.copy()
                new_request.meta["err_callback_retry"] += 1

                if failure.check(HttpError):
                    response = failure.value.response
                    self.logger.info("当前请求url：{0} 异常，状态码为：{1}，重试次数：{2}"
                                     "".format(response.url, response.status, retry_count + 1))

                return new_request
            else:
                # if failure.check(HttpError):
                #     response = failure.value.response
                #     headers = get_headers_from_response(response)
                #     cookiejar = get_cookiejar_from_response(response)
                # else:
                #     cookiejar = dict(request.cookies)
                #     headers = dict(request.headers)
                # self.get_logout_by_request(headers, cookiejar)

                item = meta["item"]
                return list(self.error_handle(item["username"], "err_callback",
                                              logout_request=self.get_logout_request(meta)))
        except Exception:
            self.logger.exception("err_callback except")
            return self.get_next_request()

    def check_need_sms_captcha(self, response, username):
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        form_data = {"accountType": "01",
                     "account": username,
                     "timestamp": get_js_time(),
                     # "pwdType": "02",
                     }
        info = get_content_by_requests("https://login.10086.cn/needVerifyCode.htm?"
                                       + urlencode(form_data), headers=headers, cookie_jar=cookiejar)
        return b'"needVerifyCode":"1"' in info

    def verify_captcha(self, response, captcha_code):
        """
        移动有一个url可以在不提交表单的情况下，先检查验证码是否正确
        返回是否正确
        """
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        url = b"https://login.10086.cn/verifyCaptcha?inputCode=" \
              + captcha_code.encode('unicode-escape', "ignore").replace(b"\\u", b"")
        info = get_content_by_requests(url, headers=headers, cookie_jar=cookiejar)
        return b'"resultCode":"0"' in info

    def request_sms_code(self, response, username):
        """
        请求移动发送登录的短信验证码
        """
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)

        form_data = {"userName": username}

        # # 不知道这是干嘛的
        # url = "https://login.10086.cn/chkNumberAction.action"
        # info = get_content_by_requests_post(url, data=form_data,
        #                                     headers=headers, cookie_jar=cookiejar)

        form_data.update({"type": "01", "channelID": "12003"})
        url = "https://login.10086.cn/sendRandomCodeAction.action"
        info = get_content_by_requests_post(url, data=form_data,
                                            headers=headers, cookie_jar=cookiejar)
        return info == b'0'

    def _set_sms_captcha_headers_to_ssdb(self, username, response):
        """
        将当前headers信息放入ssdb中
        :param username:
        :param response:
        :return:
        """
        headers = get_headers_from_response(response)
        self.set_sms_captcha_headers_to_ssdb(headers, username)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        item["brand"] = "移动"

        try:
            # self.add_proxy(meta)

            # 请求验证码，并通过此请求获取cookie
            yield Request("https://login.10086.cn/captchazh.htm?type=12", self.parse_captchazh,
                          dont_filter=True, meta=meta, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta["item"]["username"], "移动---爬虫解析入口异常")

    def parse_captchazh(self, response):
        """
        解析验证码
        """
        meta = response.meta
        item = meta["item"]
        try:
            username = item["username"]
            password = item["password"]

            form_data = {"account": username,
                         "password": self.pwd_encrypt(password),
                         "accountType": "01",
                         "pwdType": "01",
                         "smsPwd": password,
                         "backUrl": "http://shop.10086.cn/i/",
                         "rememberMe": "0",
                         "channelID": "12003",
                         "protocol": "https:",
                         "timestamp": get_js_time(),
                         }
            if self.check_need_sms_captcha(response, username):
                self._set_sms_captcha_headers_to_ssdb(username, response)
                sms_uid = self.need_sms_captcha_type(username, type="login")
                form_data["smsPwd"] = self.ask_captcha_code(sms_uid)
                yield Request("https://login.10086.cn/login.htm?" + urlencode(form_data),
                              self.parse_login, dont_filter=True, meta=meta, errback=self.err_callback)
            else:
                yield Request("https://login.10086.cn/login.htm?" + urlencode(form_data),
                              self.parse_login, dont_filter=True, meta=meta, errback=self.err_callback)
        except CaptchaTimeout:
            yield from self.error_handle(item["username"], "移动---解析验证码失败，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。")
        except Exception:
            yield from self.except_handle(item["username"], "移动---解析验证码失败")

    def parse_login(self, response):
        """
        解析登录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"code":"0000"' in text:  # 登录成功
                datas = json_loads(text)
                form_data = {"backUrl": "http://shop.10086.cn/i/",
                             "artifact": datas.get("artifact", "-1"),
                             }

                # 登录成功后，需要访问assertAcceptURL才能让认证生效，才能继续爬取其它信息
                url = (datas.get("assertAcceptURL", "http://shop.10086.cn/i/v1/auth/getArtifact")
                       + "?" + urlencode(form_data))
                yield Request(url, self.parse_loginfo, dont_filter=True,
                              meta=meta, errback=self.err_callback)
            elif '"result":"9"' in text:
                username = item["username"]
                yield from self.error_handle(username,
                                             "移动---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg="访问过于频繁，请等3分钟后再试。")
            else:
                if '"code":"6002"' in text or '"code":"6001"' in text:
                    # 6001是短信随机码不正确或已过期
                    # 6002是短信随机码错误
                    tell_msg = "短信随机码错误或过期，请刷新页面重试。"
                elif '"code":"5002"' in text or '"code":"2036"' in text:  # 5002是密码错误
                    tell_msg = "密码错误，请刷新页面重试。"
                else:
                    tell_msg = self.get_err_msg(text)
                username = item["username"]
                yield from self.error_handle(username,
                                             "移动---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield from self.except_handle(item["username"], "移动---解析登录失败: %s" % text)

    def parse_loginfo(self, response):
        """
        解析登录跳转
        """
        meta = response.meta
        try:
            # 获取号码信息
            url = "http://shop.10086.cn/i/v1/cust/mergecust/" \
                  + meta["item"]["username"] + "?_=" + get_js_time()
            yield Request(url, self.parse_BindnumInfo, dont_filter=True,
                          meta=meta, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta["item"]["username"],
                                          "移动---解析登录跳转失败: %s" % response.text,
                                          logout_request=self.get_logout_request(meta))

    def parse_BindnumInfo(self, response):
        """
        解析号码信息
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"retCode":"000000"' in text:  # 成功
                datas = json_loads(text)["data"]
                info_data = datas["custInfoQryOut"]

                inNetDate = info_data["inNetDate"]
                registration_time = "-".join((inNetDate[:4], inNetDate[4:6], inNetDate[6:8]))

                item["registration_time"] = registration_time
                item["in_nets_duration"] = get_in_nets_duration_by_start_date(registration_time)
                item["status"] = UserStatus.Opened if info_data["status"] == "00" else UserStatus.Shutdown
                item["real_name"] = info_data["name"]
                item["is_real_name"] = (info_data["realNameInfo"] in ["2", "3"])
                item["contact_addr"] = info_data.get("address")

                item["package"] = datas["curPlanQryOut"]["curPlanName"]
            elif '"retCode":"570007"' in text:  # 系统繁忙！
                yield from self._retry_request(response)
                return
            elif '"retCode":"500003"' in text:  # session信息为空，请先登录!
                yield from self.error_handle(item["username"],
                                             "移动---获取号码信息失败: (username:%s, password:%s) %s"
                                             % (item["username"], item["password"], text),
                                             "认证失败，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return
            else:
                self.logger.error("移动---获取号码信息失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 获取余额信息
            url = "http://shop.10086.cn/i/v1/fee/real/" + item["username"] + "?_=" + get_js_time()
            yield Request(url, self.parse_fee, dont_filter=True, meta=meta, errback=self.err_callback)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析号码信息失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def parse_fee(self, response):
        """
        解析余额信息
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"retCode":"000000"' in text:  # 成功
                datas = json_loads(text)["data"]
                curFeeTotal = float(datas.get("curFeeTotal", 0))
                oweFee = float(datas.get("oweFee", 0))
                curFee = float(datas.get("curFee", curFeeTotal))
                item["balance"] = min(curFeeTotal, curFee) \
                    if curFeeTotal > 0 else min(curFeeTotal, curFee, -oweFee)

                self.logger.critical("curFeeTotal(%s) oweFee(%s) curFee(%s)"
                                     % (curFeeTotal, oweFee, curFee))
            elif '"retCode":"570007"' in text:  # 系统繁忙！
                yield from self._retry_request(response)
                return
            elif '"retCode":"500003"' in text:  # session信息为空，请先登录!
                yield item
                yield from self.error_handle(item["username"],
                                             "移动---获取余额信息失败: (username:%s, password:%s) %s"
                                             % (item["username"], item["password"], text),
                                             "认证失败，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return
            else:
                self.logger.error("移动---获取余额信息失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 获取交费记录
            yield self._get_historyPayment_request(response)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析余额信息失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def _get_historyPayment_request(self, response):
        """
        返回获取交费记录的请求
        """
        meta = response.meta
        this_month = date.today()
        six_before_month = this_month - relativedelta(months=self.BILL_COUNT_LIMIT - 1)
        form_data = {"startTime": six_before_month.strftime("%Y%m01"),
                     "endTime": this_month.strftime("%Y%m%d"),
                     "_": get_js_time(),
                     }
        return Request("http://shop.10086.cn/i/v1/cust/his/" + meta["item"]["username"]
                       + "?" + urlencode(form_data), self.parse_historyPayment,
                       dont_filter=True, meta=meta, errback=self.err_callback)

    def parse_historyPayment(self, response):
        """
        解析交费记录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"retCode":"000000"' in text:
                this_month = date.today()
                history_payment_dic = {(this_month - relativedelta(months=i)).strftime("%Y%m"): []
                                       for i in range(self.BILL_COUNT_LIMIT)}

                payment_channel_dic = self.payment_channel_dic
                # 近6个月的交费记录都已经包含着数据里
                for payment in json_loads(text)["data"]:
                    try:
                        the_date = payment["payDate"]
                        payment_data = {"time": "".join([the_date[:4], "-", the_date[4:6], "-",
                                                         the_date[6:8], " ", the_date[8:10], ":",
                                                         the_date[10:12], ":", the_date[12:]]),
                                        "fee": float(payment["payFee"]),
                                        "channel": payment_channel_dic.get(payment["payType"], "其它"),
                                        }
                        history_payment_dic[the_date[:6]].append(payment_data)
                    except KeyError:
                        continue
                item["history_payment"] = history_payment_dic
            elif '"retCode":"570007"' in text:  # 系统繁忙！
                yield from self._retry_request(response)
                return
            elif '"retCode":"500003"' in text:  # session信息为空，请先登录!
                yield item
                yield from self.error_handle(item["username"],
                                             "移动---获取交费记录失败: (username:%s, password:%s) %s"
                                             % (item["username"], item["password"], text),
                                             "认证失败，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return
            else:
                self.logger.error("移动---获取交费记录失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            # 获取账单记录
            yield self._get_historyBill_request(response)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析交费记录失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def _get_historyBill_request(self, response):
        """
        返回获取历史账单的请求
        """
        meta = response.meta
        this_month = date.today()
        six_before_month = this_month - relativedelta(months=self.BILL_COUNT_LIMIT - 1)
        form_data = {"bgnMonth": six_before_month.strftime("%Y%m"),  # 指定开始月份(远)
                     "endMonth": this_month.strftime("%Y%m"),  # 指定结束月份(最近)
                     "_": get_js_time(),
                     }
        return Request("http://shop.10086.cn/i/v1/fee/billinfo/" + meta["item"]["username"]
                       + "?" + urlencode(form_data), self.parse_queryHistoryBill,
                       dont_filter=True, meta=meta, errback=self.err_callback)

    def _get_sms_send_sleep_time(self, meta):
        return max(meta["last_sms_time"] + 61 - time(), 0) if "last_sms_time" in meta else 0

    def parse_queryHistoryBill(self, response):
        """
        解析账单信息
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"retCode":"000000"' in text:
                # 近6个月的账单都已经包含着数据里
                item["history_bill"] = {bill["billMonth"]: {"all_fee": float(bill["billFee"])}
                                        for bill in json_loads(text)["data"]}
            elif '"retCode":"570007"' in text:  # 系统繁忙！
                yield from self._retry_request(response)
                return
            elif '"retCode":"500003"' in text:  # session信息为空，请先登录!
                yield item
                yield from self.error_handle(item["username"],
                                             "移动---获取历史账单失败: (username:%s, password:%s) %s"
                                             % (item["username"], item["password"], text),
                                             "认证失败，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return
            else:
                self.logger.error("移动---获取历史账单失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            meta["sendSMSpwd_count"] = 1
            yield self.casual_request(response)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析历史账单失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def _get_callDetail_image_captcha(self, response, username):
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        url = "http://shop.10086.cn/i/authImg?t=" + str(rand_0_1())
        self.set_image_captcha_headers_to_ssdb(headers, username)
        return get_content_by_requests(url, headers=headers, cookie_jar=cookiejar)

    def _verify_callDetail_captcha(self, response, username, captcha_code):
        """
        返回是否正确
        """
        cookiejar = get_cookiejar_from_response(response)
        headers = get_headers_from_response(response)
        url = "http://shop.10086.cn/i/v1/res/precheck/" + username + "?captchaVal=" \
              + captcha_code + "&_=" + get_js_time()
        info = get_content_by_requests(url, headers=headers, cookie_jar=cookiejar)
        return b'"retCode":"000000"' in info

    def casual_request(self, response):
        """
        随便访问一个验证地址，没有实际意义；
        若不return Request()的话，会报错；
        """
        meta = response.meta
        url = "http://shop.10086.cn/i/authImg?t=" + str(rand_0_1())
        return Request(url, self.send_sms_and_img_captcha, meta=meta, errback=self.err_callback)

    def send_sms_and_img_captcha(self, response):
        # 获取通话记录时，移动要求再次认证，所以这里再向移动请求一次短信验证码
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        try:
            sms_password = ""
            for i in range(self.CAPTCHA_RETRY_TIMES):
                captcha_body = self._get_callDetail_image_captcha(response, username)
                if not sms_password:
                    # 先告诉web前端需要短信和图形验证码
                    self._set_sms_captcha_headers_to_ssdb(username, response)
                    img_uid, sms_uid = self.need_image_and_sms_captcha_type(captcha_body, username,
                                                                            ".png", type="general")
                    captcha_code, sms_password = self.ask_captcha_code(img_uid), self.ask_captcha_code(sms_uid)
                else:
                    img_uid = self.need_image_captcha(captcha_body, username, ".png")
                    captcha_code = self.ask_captcha_code(img_uid)
                if self._verify_callDetail_captcha(response, username, captcha_code):
                    break
            else:
                yield item
                yield from self.error_handle(username, "移动---图形验证码无法识别。",
                                             "图形验证码无法识别，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return

            form_data = {"pwdTempRandCode": b64encode(sms_password.encode()),
                         "pwdTempSerCode": b64encode(item["password"].encode()),
                         "captchaVal": captcha_code,
                         "callback": "jQuery1830" + str(randint(1E16, 1E17 - 1)) + "_" + get_js_time(),
                         "_": get_js_time(),
                         }
            # 发送认证请求
            yield Request("https://shop.10086.cn/i/v1/fee/detailbilltempidentjsonp/"
                          + meta["item"]["username"] + "?" + urlencode(form_data),
                          self.parse_billtempident, dont_filter=True, meta=meta, errback=self.err_callback)
        except CaptchaTimeout:
            yield item
            yield from self.error_handle(username, "移动---解析验证码失败，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。",
                                         logout_request=self.get_logout_request(meta))
        except Exception:
            yield item
            yield from self.except_handle(username, "移动---解析请求通信记录的验证码失败。",
                                          logout_request=self.get_logout_request(meta))

    def parse_billtempident(self, response):
        """
        解析请求通话记录的认证
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        try:
            if '"retCode":"000000"' in text:  # 成功
                self.crawling_login(item["username"])  # 通知授权成功

                meta["call_count"] = 0
                item["history_call"] = defaultdict(list)
                yield self._get_callDetail_request(response, date.today())
            elif '"retCode":"570007"' in text:  # 系统繁忙！
                yield from self._retry_request(response)
                return
            elif '"retCode":"500003"' in text:  # session信息为空，请先登录!
                yield item
                yield from self.error_handle(item["username"],
                                             "移动---获取请求通话记录的认证失败: (username:%s, password:%s) %s"
                                             % (item["username"], item["password"], text),
                                             "认证失败，请刷新页面重试。",
                                             logout_request=self.get_logout_request(meta))
                return
            else:
                username = item["username"]
                yield item
                if '"retCode":"2036"' in text or '"retCode":"570002"' in text:  # 服务密码错误
                    tell_msg = "服务密码错误，请刷新页面重试。"
                elif '"retCode":"570005"':
                    tell_msg = "短信验证码错误。"
                else:
                    tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "移动---获取请求通话记录的认证失败："
                                             "(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg,
                                             logout_request=self.get_logout_request(meta))
        except Exception:
            yield item
            yield from self.except_handle(item["username"],
                                          "移动---解析请求通话记录的认证失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def _get_callDetail_request(self, response, this_month, start_curor=1):
        """
        返回通话记录请求
        """
        meta = response.meta
        meta["last_call_month"] = this_month
        if start_curor == 1:
            meta["call_count"] += 1
        form_data = {"curCuror": str(start_curor),
                     "step": str(self.call_detail_step),
                     "qryMonth": this_month.strftime("%Y%m"),
                     "billType": "02",
                     "callback": "jQuery1830" + str(randint(1E16, 1E17 - 1)) + "_" + get_js_time(),
                     "_": get_js_time(),
                     }
        return Request("https://shop.10086.cn/i/v1/fee/detailbillinfojsonp/"
                       + meta["item"]["username"] + "?" + urlencode(form_data),
                       self.parse_callDetail, dont_filter=True, meta=meta, errback=self.err_callback)

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
            start_curor = 1
            if '"retCode":"000000"' in text:  # 成功
                datas = text[text.find('{"data":'):-1]
                datas = json_loads(datas)

                the_call_count = datas.get("totalNum", 0)
                if the_call_count > self.CALL_PAGE_SIZE_LIMIT:
                    self.logger.error("移动---单月通话次数过大：username:%s, "
                                      "password:%s, month:%s, totalNum:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_call_count))

                call_list = []
                this_year = this_month_str[0:4]
                for call in datas["data"]:
                    the_time = call["startTime"].replace("/", "-")
                    if len(the_time) == 14:
                        the_time = this_year + "-" + the_time
                    call_list.append({
                        "time": the_time,
                        "duration": ":".join("%02d" % int(i) for i
                                             in get_numbers_in_text(call["commTime"])),
                        "type": CallType.Caller if "主叫" == call["commMode"] else CallType.Called,
                        "other_num": call["anotherNm"],
                        "my_location": call["commPlac"],
                        "fee": float(call["commFee"]),
                    })

                month_call_list = item["history_call"][this_month_str]
                month_call_list.extend(call_list)
                if len(call_list) == self.call_detail_step:
                    start_curor += len(month_call_list)

            elif '"retCode":"2039"' in text:  # 选择时间段没有详单记录哦
                item["history_call"][this_month_str] = []
            elif '"retCode":"520001"' in text:
                yield item
                yield from self.error_handle(item["username"],
                                             "移动--用户{0}临时身份凭证不存在: {1}，返回状态码为："
                                             "{2}".format(item["username"], text, response.status),
                                             "移动--用户{0}认证失败，请重试。".format(item["username"]))
                return
            elif "call_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("移动---重试通话记录：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(1)
                request = response.request.copy()
                request.meta["call_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("移动---获取通话记录失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            if start_curor != 1:
                yield self._get_callDetail_request(response, this_month, start_curor)
            elif meta["call_count"] < self.CALL_COUNT_LIMIT:  # 只需要最近6个月的
                last_month = get_last_month_from_date(this_month)
                yield self._get_callDetail_request(response, last_month)
            else:
                # 处理完，返回爬取的结果
                yield from self.crawling_done(item, self.get_logout_request(meta))

                # # 获取过去6个月的短信记录
                # meta["msg_count"] = 0
                # item["history_msg"] = defaultdict(list)
                # yield self._get_msgDetail_request(response, date.today())
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析通话记录失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))

    def _get_msgDetail_request(self, response, this_month, start_curor=1):
        """
        返回短信记录请求
        """
        meta = response.meta
        meta["last_msg_month"] = this_month
        if start_curor == 1:
            meta["msg_count"] += 1
        form_data = {"curCuror": str(start_curor),
                     "step": str(self.call_detail_step),
                     "qryMonth": this_month.strftime("%Y%m"),
                     "billType": "03",
                     "msgback": "jQuery1830" + str(randint(1E16, 1E17 - 1)) + "_" + get_js_time(),
                     "_": get_js_time(),
                     }
        return Request("https://shop.10086.cn/i/v1/fee/detailbillinfojsonp/"
                       + meta["item"]["username"] + "?" + urlencode(form_data),
                       self.parse_msgDetail, dont_filter=True, meta=meta, errback=self.err_callback)

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
            start_curor = 1
            if '"retCode":"000000"' in text:  # 成功
                datas = text[text.find('{"data":'):-1]
                datas = json_loads(datas)

                the_msg_count = datas.get("totalNum", 0)
                if the_msg_count > self.CALL_PAGE_SIZE_LIMIT:
                    self.logger.error("移动---单月短信次数过大：username:%s, "
                                      "password:%s, month:%s, totalNum:%d"
                                      % (item["username"], item["password"],
                                         this_month, the_msg_count))

                msg_list = []
                this_year = this_month_str[0:4]
                for msg in datas["data"]:
                    the_time = msg["startTime"].replace("/", "-")
                    if len(the_time) == 14:
                        the_time = this_year + "-" + the_time
                    msg_list.append({
                        "time": the_time,
                        "type": MsgType.Receive if "接收" in msg["commMode"] else MsgType.Send,
                        "other_num": msg["anotherNm"],
                    })

                month_msg_list = item["history_msg"][this_month_str]
                month_msg_list.extend(msg_list)
                if len(msg_list) == self.call_detail_step:
                    start_curor += len(month_msg_list)

            elif '"retCode":"2039"' in text:  # 选择时间段没有详单记录哦
                item["history_msg"][this_month_str] = []
            elif '"retCode":"520001"' in text:
                # 若短信月份记录小于2个月，则判定为失败
                if len(item["history_msg"]) < 2:
                    yield item
                    yield from self.error_handle(item["username"],
                                                 "移动--用户{0}临时身份凭证不存在: {1}，返回状态码为："
                                                 "{2}".format(item["username"], text, response.status),
                                                 "移动--用户{0}认证失败，请重试。".format(item["username"]))
                else:
                    yield from self.crawling_done(item, self.get_logout_request(meta))
                return
            elif "msg_" + this_month_str + "_retry" not in meta:
                # 重发一次
                self.logger.error("移动---重试短信记录：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))
                sleep(1)
                request = response.request.copy()
                request.meta["msg_" + this_month_str + "_retry"] = 1
                yield request
                return
            else:
                self.logger.error("移动---获取短信记录失败：(username:%s, password:%s) %s"
                                  % (item["username"], item["password"], text))

            if start_curor != 1:
                yield self._get_msgDetail_request(response, this_month, start_curor)
            elif meta["msg_count"] < self.CALL_COUNT_LIMIT:  # 只需要最近6个月的
                last_month = get_last_month_from_date(this_month)
                yield self._get_msgDetail_request(response, last_month)
            else:
                # 处理完，返回爬取的结果
                yield from self.crawling_done(item, self.get_logout_request(meta))
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "移动---解析短信记录失败: %s" % text,
                                          logout_request=self.get_logout_request(meta))
