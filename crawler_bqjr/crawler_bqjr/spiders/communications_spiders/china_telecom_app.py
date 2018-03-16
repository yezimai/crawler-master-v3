# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date
from re import compile as re_compile
from time import strftime, sleep

from dateutil.relativedelta import relativedelta
from scrapy import Request

from crawler_bqjr.items.communications_items import UserStatus, Sex
from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spider_class import CaptchaTimeout
from crawler_bqjr.spiders.communications_spiders.base import CommunicationsSpider
from crawler_bqjr.spiders_settings import COMMUNICATIONS_BRAND_DICT
from crawler_bqjr.tools.dianxin_data_convert import DXConvertData
from crawler_bqjr.utils import get_months_str_by_number, get_month_last_date_by_date, \
    get_last_month_from_date
from global_utils import json_dumps, json_loads

"""
1、电信App没有登出接口(在App端登出，其token还可以使用);
2、因电信服务器原因，所有接口都有概率返回空("")，App端则显示网络问题，所以通话记录可以重试50次;
3、获取通话记录之前有一个身份验证码，但是可以绕过，只验证短信验证码。
"""


class ChinaTelecomAppSpider(CommunicationsSpider):
    name = COMMUNICATIONS_BRAND_DICT["电信"]
    allowed_domains = ["cservice.client.189.cn", "appgo.189.cn"]
    start_urls = [DO_NOTHING_URL]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_call_times = 10
        self.dx_conver = DXConvertData()
        self.appgo_headers = {
            "Accept": "application/json",
            "User-Agent": "Huawei DUK-AL20/6.2.1",
            "Content-Type": "application/json",
            "Connection": "Keep-Alive",
            "Host": "appgo.189.cn:8443"
        }
        self.cservice_headers = {
            "User-Agent": "Huawei DUK-AL20/6.2.1",
            "Content-Type": "text/xml",
            "Connection": "Keep-Alive",
            "Host": "cservice.client.189.cn:8004"
        }
        self.err_msg_pattern = re_compile(r',\s?"resultDesc":\s?"(.*?)"')
        self.special_err_msg_pattern = re_compile(r'"ResultDesc":\s?\{"value":\s?"(.*?)"\}')
        self.internet_age_pattern = re_compile(r'"title":"网龄","subtitle":"(.*?)",')
        self.age_arr_pattern = re_compile(r'(\d+)年(\d+)个月')

    def get_err_msg(self, text, is_special=False):
        try:
            if is_special:
                return self.special_err_msg_pattern.search(text).group(1)
            else:
                return self.err_msg_pattern.search(text).group(1)
        except Exception:
            return text

    def conversion_internet_age(self, text):
        """
        将网龄字符串转换为月
        """
        age_arr = self.age_arr_pattern.search(text)
        if age_arr:
            year, month = age_arr.groups()
            return str(int(year) * 12 + int(month))
        else:
            return text

    def get_registration_time_by_internet_age(self, text):
        """
        根据在网时长倒推注册时间,"日"默认为"01"
        """
        registration_time = date.today() - relativedelta(months=int(text))
        return registration_time.strftime("%Y-%m-01")

    def _set_sms_captcha_headers_to_ssdb(self, username, token):
        """
        将当前的token放入ssdb中
        :param username: 用户名
        :param token   : 用户唯一凭证
        :return        : None
        """
        json_str = json_dumps({"token": token})
        self.set_sms_captcha_headers_to_ssdb(json_str, username)

    def retry_call_list(self, response, text):
        """
        重试通话记录
        """
        sleep(1)
        meta = response.meta
        item = meta["item"]
        request = response.request.copy()
        this_month_str = meta["last_call_month"].strftime("%Y%m")

        if "call_" + this_month_str + "_retry" not in meta:
            request.meta["call_" + this_month_str + "_retry"] = 0
        # 重发一次
        request.meta["call_" + this_month_str + "_retry"] += 1
        self.logger.error("电信---重试-{}-通话记录，第{}次！：(username:{}, password:{}) {}"
                          "".format(this_month_str, str(request.meta["call_" + this_month_str + "_retry"]),
                                    item["username"], item["password"], text))
        return request

    def parse(self, response):
        yield from self.login(response)

    def login(self, response):
        """
        电信App登录
        """
        meta = response.meta
        item = meta["item"]
        item["brand"] = "电信"
        username = item["username"]
        password = item["password"]

        form_data = {
            "content": {
                "fieldData": {
                    "accountType": "c2000004",
                    "phoneNum": username,
                    "isChinatelecom": "0",
                    "systemVersion": "4.4.4",
                    "authentication": password,
                    "deviceUid": "860096537016542",
                    "loginType": "4"
                },
                "attach": "test"
            },
            "headerInfos": {
                "timestamp": strftime("%Y%m%d%H%M%S"),
                "code": "loginNormal",
                "source": "110003",
                "token": "null",
                "userLoginName": username,
                "sourcePassword": "Sid98s",
                "clientType": "#6.2.1#channel29#Huawei DUK-AL20#"
            }
        }
        yield Request("https://appgo.189.cn:8443/login/normal", self.parse_login, "POST",
                      self.appgo_headers, json_dumps(form_data), meta=meta, dont_filter=True,
                      errback=self.err_callback)

    def parse_login(self, response):
        """
        解析登录
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 登录成功！")
                datas = json_loads(text)["responseData"]["data"]["loginSuccessResult"]

                if item["city"] == "":
                    item["city"] = datas["cityName"]
                meta.setdefault("login_token", datas["token"])
                meta.setdefault("phoneType", datas["phoneType"])

                form_data = {
                    "content": {
                        "fieldData": {
                            "queryflag": "",
                            "payflag": "0",
                            "destinationid": username,
                            "shopId": "20002"
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryExpense",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#samsung SM-N935F#"
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/balance/queryExpense",
                              self.parse_balance, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
            elif '"resultCode":"3001"' in text:
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg="账号或密码错误！")
            elif '"resultCode":"3002"' in text:
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg="该手机号还未进行注册！")
            elif '"resultCode":"8105"' in text:
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg="弱密码，请重置服务密码后登录！")
            elif '"code":"X102"' in text:
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg="设备机型不能为空！")
            elif text == "":
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], "电信服务器异常"),
                                             tell_msg="电信服务器异常，请稍后再试！")
            else:
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield from self.except_handle(username, "电信---解析登录失败: %s" % text)

    def parse_balance(self, response):
        """
        解析余额
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 获取余额成功！")

                datas = json_loads(text)["responseData"]["data"]
                if datas:
                    item["balance"] = datas["totalBalance"]

                form_data = {
                    "content": {
                        "fieldData": {
                            "accnbr": username,
                            "phoneType": meta["phoneType"],
                            "starGrade": "11",
                            "shopId": "20002"
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryPersonalInfo",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/personal/queryPersonalInfo",
                              self.parse_person_info_one, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
            else:
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---获取余额失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield from self.except_handle(username, "电信---解析余额失败: %s" % text)

    def parse_person_info_one(self, response):
        """
        解析个人信息1
        """
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 获取个人信息1成功！")

                # 在网时长(月)
                internet_age = self.internet_age_pattern.search(text)
                if internet_age:
                    item["in_nets_duration"] = self.conversion_internet_age(internet_age.group(1))
                    # 注册时间
                    item["registration_time"] = self.get_registration_time_by_internet_age(item["in_nets_duration"])
                else:
                    item["in_nets_duration"], item["registration_time"] = "", ""

                form_data = {
                    "Request": {
                        "HeaderInfos": {
                            "ClientType": "#6.2.1#channel8#samsung SM-N935F#",
                            "Source": "110003",
                            "SourcePassword": "Sid98s",
                            "Token": meta["login_token"],
                            "UserLoginName": username,
                            "Code": "custIdInfo",
                            "Timestamp": strftime("%Y%m%d%H%M%S")
                        },
                        "Content": {
                            "Attach": "test",
                            "FieldData": {
                                "Account": username,
                                "ShopId": "20002",
                                "AccountType": "201"
                            }
                        }
                    }
                }
                from_str = self.dx_conver.convert_request_data(form_data)
                yield Request("http://cservice.client.189.cn:8004/map/clientXML?encrypted=true",
                              self.parse_person_info_two, "POST", self.cservice_headers, from_str,
                              meta=meta, dont_filter=True, errback=self.err_callback)
            else:
                yield item
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---获取个人信息1失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析个人信息1失败: %s" % text)

    def parse_person_info_two(self, response):
        """
        解析个人信息2
        """
        meta = response.meta
        item = meta["item"]
        login_token = meta["login_token"]
        username = item["username"]

        text = ""
        try:
            res_dict = self.dx_conver.convert_response_data(response.text)
            text = json_dumps(res_dict, ensure_ascii=False)

            if '"ResultCode":{"value":"0000"}' in text:
                self.logger.info("[电信-" + username + "]: 获取个人信息2成功！")

                datas = res_dict["Response"]["ResponseData"]["Data"]
                basic_info = datas["BasicInfo"]
                item["is_real_name"] = (datas["Authenticate"]["value"] == "true")
                item["sex"] = Sex.Male if basic_info["Sex"]["value"] == "0" else Sex.Female
                item["identification_number"] = basic_info["IdCardNo"]["value"]
                item["contact_addr"] = basic_info["Address"]["value"]

                # 个人信息3暂时不使用
                # form_data = {
                #     "Request": {
                #         "HeaderInfos": {
                #             "ClientType": "#6.2.1#channel8#samsung SM-N935F#",
                #             "Source": "110003",
                #             "SourcePassword": "Sid98s",
                #             "Token": login_token,
                #             "UserLoginName": username,
                #             "Code": "custInfo",
                #             "Timestamp": strftime("%Y%m%d%H%M%S")
                #         },
                #         "Content": {
                #             "Attach": "test",
                #             "FieldData": {
                #                 "PhoneNbr": username
                #             }
                #         }
                #     }
                # }
                # from_str = self.dx_conver.convert_request_data(form_data)
                # yield Request("http://cservice.client.189.cn:8004/map/clientXML?encrypted=true",
                #               self.parse_person_info_three, "POST", self.cservice_headers, from_str,
                #               meta=meta, dont_filter=True, errback=self.err_callback)

                # 查询通话记录需要短信验证码、身份证号码、姓名
                # self._set_sms_captcha_headers_to_ssdb(username, login_token)
                # uid = self.need_name_idcard_sms_captcha_type(username)
                # sms_str = self.ask_captcha_code(uid)
                # sms_arr = sms_str.split("_")
                # sms_code, name, id_card,  = sms_arr[0], sms_arr[1], sms_arr[2]
                # item["is_real_name"] = True
                # item["real_name"] = name
                # item["identification_number"] = id_card

                # 电信App bug，可以绕过身份证和姓名的检验，只需要短信验证码
                self._set_sms_captcha_headers_to_ssdb(username, login_token)
                uid = self.need_sms_captcha_type(username)
                sms_code = self.ask_captcha_code(uid)

                item["history_call"] = {}
                meta["call_count"] = 0
                yield self.get_call_detail(response, sms_code, date.today())
            else:
                yield item
                tell_msg = self.get_err_msg(text, True)
                yield from self.error_handle(username,
                                             "电信---获取个人信息2失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except CaptchaTimeout:
            yield item
            yield from self.error_handle(username, "电信---解析验证码失败，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。")
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析个人信息2失败: %s" % text)

    def parse_person_info_three(self, response):
        """
        解析个人信息3
        注：方法请求参数和app请求参数加密后不一致。经对比后也不能查找到不同点；
            猜测可能是加密/解密函数影响了参数显示。
        """
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        text = ""
        try:
            res_dict = self.dx_conver.convert_response_data(response.text)
            text = json_dumps(res_dict, ensure_ascii=False)

            if '"ResultCode":{"value":"0000"}' in text:
                self.logger.info("[电信-" + username + "]: 获取个人信息3成功！")

                datas = res_dict["Response"]["ResponseData"]["Data"]
                item["real_name"] = datas["Cust_Name"]["value"]
                item["status"] = UserStatus.Opened if datas["NumberStatus"] == "100000" else UserStatus.Shutdown

                form_data = {
                    "content": {
                        "fieldData": {
                            "accnbr": username,
                            "queryflag": "0",
                            "queryType": "0",
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryThisMonthBill",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/bill/queryThisMonthBill",
                              self.parse_this_month_bill, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
            else:
                yield item
                tell_msg = self.get_err_msg(text, True)
                yield from self.error_handle(username,
                                             "电信---获取个人信息3失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析个人信息3失败: %s" % text)

    def get_call_detail(self, response, sms_code, this_month):
        """
        获取通话记录
        """
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        meta["sms_code"] = sms_code
        meta["call_count"] += 1
        meta["last_call_month"] = this_month

        # 每个月的第一天和最后一天
        start_time = this_month.strftime("%Y%m01")
        end_time = min(strftime("%Y%m%d"),
                       get_month_last_date_by_date(this_month).replace("-", ""))

        form_data = {
            "Request": {
                "HeaderInfos": {
                    "ClientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    "Source": "110003",
                    "SourcePassword": "Sid98s",
                    "Token": meta["login_token"],
                    "UserLoginName": username,
                    "Code": "jfyBillDetail",
                    "Timestamp": strftime("%Y%m%d%H%M%S")
                },
                "Content": {
                    "Attach": "test",
                    "FieldData": {
                        "EndTime": end_time,
                        "StartTime": start_time,
                        "Random": sms_code,
                        "PhoneNum": username,
                        "Type": "1"
                    }
                }
            }
        }
        from_str = self.dx_conver.convert_request_data(form_data)
        return Request("http://cservice.client.189.cn:8004/map/clientXML?encrypted=true",
                       self.parse_call_list, "POST", self.cservice_headers, from_str,
                       meta=meta, dont_filter=True, errback=self.err_callback)

    def parse_call_list(self, response):
        """解析通话记录"""
        meta = response.meta
        item = meta["item"]
        sms_code = meta["sms_code"]
        username = item["username"]

        res_text = ""
        try:
            this_month = meta["last_call_month"]
            this_month_str = this_month.strftime("%Y%m")
            res_dict = self.dx_conver.convert_response_data(response.text)
            res_text = json_dumps(res_dict, ensure_ascii=False)

            if '"ResultCode":{"value":"0000"}' in res_text:
                self.crawling_login(username)  # 通知授权成功

                self.logger.info("[电信-" + username + "]: 获取-" + this_month_str + "-通话记录成功！")

                item["history_call"][this_month_str] = []
                datas = res_dict["Response"]["ResponseData"]["Data"]
                if datas:
                    call_arr = datas["Items"]["Item"]
                    if isinstance(call_arr, list):
                        item["history_call"][this_month_str] = [{
                            "time": data["CallTime"]["value"],
                            "duration": data["CallTimeCost"]["value"],
                            "type": "1" if data["CallType"]["value"] == "0" else "0",
                            "other_num": data["CallMobile"]["value"],
                            "my_location": data["CallArea"]["value"],
                            "fee": data["CallFee"]["value"]
                        } for data in call_arr]
                    else:
                        item["history_call"][this_month_str] = [{
                            "time": call_arr["CallTime"]["value"],
                            "duration": call_arr["CallTimeCost"]["value"],
                            "type": "1" if call_arr["CallType"]["value"] == "0" else "0",
                            "other_num": call_arr["CallMobile"]["value"],
                            "my_location": call_arr["CallArea"]["value"],
                            "fee": call_arr["CallFee"]["value"]
                        }]
            elif '"ResultCode":{"value":"9152"}' in res_text:
                # 短信验证码超时,需要重新发送验证码
                self.logger.info("[电信]短信验证码超时，请求重新发送短信验证码！")
                self._set_sms_captcha_headers_to_ssdb(username, meta["login_token"])
                sms_uid = self.need_sms_captcha_type(username)
                sms_code = self.ask_captcha_code(sms_uid)
                meta["call_count"] -= 1
                yield self.get_call_detail(response, sms_code, this_month)
                return
            elif '"ResultCode":{"value":"8204"}' in res_text:
                yield item
                yield from self.error_handle(username,
                                             "电信---获取通话记录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], res_text),
                                             tell_msg="此账号不支持通话记录查询，请联系电信运营商。")
                return
            elif meta.get("call_" + this_month_str + "_retry", 0) < self.retry_call_times:
                if '"ResultCode":{"value":"1"}' in res_text:
                    self.logger.error("电信---获取通话记录失败：服务器异常！")
                elif response.text == "":
                    self.logger.error("电信---获取通话记录失败：服务器返回值为空！")
                else:
                    self.logger.error("电信---获取通话记录失败：{}".format(res_text))
                yield self.retry_call_list(response, res_text)
                return
            else:
                self.logger.error("电信---获取通话记录失败：(username:%s, password:%s) %s"
                                  % (username, item["password"], res_text))

            # 继续请求下一个月通话记录
            if meta["call_count"] < self.CALL_COUNT_LIMIT:
                last_month = get_last_month_from_date(this_month)
                yield self.get_call_detail(response, sms_code, last_month)
            else:
                # 请求账单
                form_data = {
                    "content": {
                        "fieldData": {
                            "accnbr": username,
                            "queryflag": "0",
                            "queryType": "0",
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryThisMonthBill",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/bill/queryThisMonthBill",
                              self.parse_this_month_bill, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
        except CaptchaTimeout:
            yield item
            yield from self.error_handle(username, "电信---解析验证码失败，等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。")
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析通话记录失败: %s" % res_text)


    def parse_this_month_bill(self, response):
        """解析当前月份话费账单"""
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 获取当前月份话费账单成功！")

                datas = json_loads(text)["responseData"]["data"]
                item["history_bill"] = defaultdict(dict)
                item["history_bill"][strftime('%Y%m')] = {"all_fee": datas["sumCharge"]}
                # 用户名
                item["real_name"] = datas["accNbrDetail"]

                form_data = {
                    "content": {
                        "fieldData": {
                            "accnbr": username,
                            "queryflag": "",
                            "queryType": "0",
                            "billingcycle": get_months_str_by_number(6, False)
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryBill",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/bill/queryBill",
                              self.parse_bill_list, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
            else:
                yield item
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---获取当前月份话费账单失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析当前月份话费账单失败: %s" % text)

    def parse_bill_list(self, response):
        """解析最近6个月份话费账单(不包含本月)"""
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 获取最近6个月份话费账单成功！")

                datas = json_loads(text)["responseData"]["data"]["chargeEntities"]
                item["history_bill"].update({
                    bill["month"]: {"all_fee": bill["sumCharge"] if bill["sumCharge"] else "0.0"}
                    for bill in datas})

                form_data = {
                    "content": {
                        "fieldData": {
                            "accnbr": username,
                            "billingcycle": get_months_str_by_number(6)
                        },
                        "attach": "test"
                    },
                    "headerInfos": {
                        "timestamp": strftime("%Y%m%d%H%M%S"),
                        "code": "queryCallRecharge",
                        "source": "110003",
                        "token": meta["login_token"],
                        "userLoginName": username,
                        "sourcePassword": "Sid98s",
                        "clientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                    }
                }
                yield Request("https://appgo.189.cn:8443/query/payMent/queryCallRecharge",
                              self.parse_payment_list, "POST", self.appgo_headers,
                              json_dumps(form_data), meta=meta, dont_filter=True,
                              errback=self.err_callback)
            else:
                yield item
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---获取最近6个月份话费账单失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析最近6个月份话费账单失败: %s" % text)

    def parse_payment_list(self, response):
        """解析缴费记录"""
        text = response.text
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            if '"resultCode":"0000"' in text:
                self.logger.info("[电信-" + username + "]: 获取缴费记录成功！")

                # 近6个月的交费记录都已经包含着数据里
                datas = json_loads(text)["responseData"]["data"]["billingCycles"]
                history_payment_dic = {month: [] for month in get_months_str_by_number(6).split(",")}
                for payments in datas:
                    if not payments["paymentDetails"]:
                        continue

                    for payment in payments["paymentDetails"]:
                        pay_date = payment["stateDate"]
                        history_payment_dic[payments["billCycle"]].append({
                            "time": pay_date[0:4] + "-" + pay_date[4:6] + "-" + pay_date[6:] + " 00:00:00",
                            "channel": payment["payChannelId"],
                            "fee": payment["paymentAmount"]
                        })
                item["history_payment"] = history_payment_dic

                # 处理完，返回爬取的结果
                yield from self.crawling_done(item)
            else:
                yield item
                tell_msg = self.get_err_msg(text)
                yield from self.error_handle(username,
                                             "电信---获取缴费记录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], text),
                                             tell_msg=tell_msg)
        except Exception:
            yield item
            yield from self.except_handle(username, "电信---解析缴费记录失败: %s" % text)
