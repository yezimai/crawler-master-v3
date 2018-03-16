# -*- coding: utf-8 -*-

from time import strftime
from urllib.parse import unquote

from scrapy import FormRequest

from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from global_utils import json_loads


class BocomWapSpider(BankSpider):
    """
        交通银行wap端爬虫
    """
    name = "bank_bocom_wap"
    allowed_domains = ["95559.com.cn"]
    start_urls = ["https://wap.95559.com.cn/mobs/main.html#public/login/login"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Host": "wap.95559.com.cn",
            "Referer": "https://wap.95559.com.cn/mobs/main.html",
            "User-Agent": "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 "
                          "(KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.request_url = 'https://wap.95559.com.cn/mobs/MobileBank'
        self.page_size = '10'
        self.password_dict = {
            '1': 0,
            '2': 1,
            '3': 2,
            '4': 3,
            '5': 4,
            '6': 5,
            '7': 6,
            '8': 7,
            '9': 8,
            '0': 9,
            'q': 10,
            'w': 11,
            'e': 12,
            'r': 13,
            't': 14,
            'y': 15,
            'u': 16,
            'i': 17,
            'o': 18,
            'p': 19,
            'a': 20,
            's': 21,
            'd': 22,
            'f': 23,
            'g': 24,
            'h': 25,
            'j': 26,
            'k': 27,
            'l': 28,
            'z': 29,
            'x': 30,
            'c': 31,
            'v': 32,
            'b': 33,
            'n': 34,
            'm': 35,
            'Q': 36,
            'W': 37,
            'E': 38,
            'R': 39,
            'T': 40,
            'Y': 41,
            'U': 42,
            'I': 43,
            'O': 44,
            'P': 45,
            'A': 46,
            'S': 47,
            'D': 48,
            'F': 49,
            'G': 50,
            'H': 51,
            'J': 52,
            'K': 53,
            'L': 54,
            'Z': 55,
            'X': 56,
            'C': 57,
            'V': 58,
            'B': 59,
            'N': 60,
            'M': 61,
            '[': 62,
            ']': 63,
            '{': 64,
            '}': 65,
            '#': 66,
            '%': 67,
            '^': 68,
            '*': 69,
            '+': 70,
            '=': 71,
            '_': 72,
            '\\': 73,
            '|': 74,
            '~': 75,
            '<': 76,
            '>': 77,
            '€': 78,
            '￡': 79,
            '￥': 80,
            '·': 81,
            '-': 82,
            '/': 83,
            ':': 84,
            ';': 85,
            '(': 86,
            ')': 87,
            '$': 88,
            '&': 89,
            '@': 90,
            '"': 91,
            '.': 92,
            ',': 93,
            '?': 94,
            '!': 95,
            '\'': 96,
        }

    def parse(self, response):
        req_data = {
            'processCode': 'MB0035',
            'url': 'https://wap.95559.com.cn/mobs/main.html#public/login/login',
            'isWap': '1'
        }
        yield FormRequest(
            url=self.request_url,
            callback=self.parse_session,
            headers=self.headers,
            formdata=req_data,
            meta=response.meta,
            dont_filter=True,
            errback=self.err_callback
        )

    def parse_session(self, response):
        meta = response.meta

        try:
            json_response = json_loads(response.text)
            if json_response['RSP_HEAD']['TRAN_SUCCESS'] == '1':
                m_session_id = json_response['RSP_HEAD']['MSessionId']
                headers = self.headers.copy()
                headers['Cookie'] = 'MSessionId=' + m_session_id
                meta["m_session_id"] = m_session_id

                req_data = {
                    'processCode': 'MB0401',
                    'isWap': '1',
                    'MSessionId': m_session_id,
                    'pageCode': 'NLG0001',
                    'targetPageCode': 'NLG001'
                }
                yield FormRequest(
                    url=self.request_url,
                    callback=self.parse_keys,
                    headers=headers,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                yield from self.error_handle(meta['item']['username'], "交通银行wap---获取sessionId时返回不成功数据",
                                             tell_msg="获取sessionid响应状态不正确")
        except Exception:
            yield from self.except_handle(meta['item']['username'], "交通银行wap---获取sessionId",
                                          tell_msg="获取sessionid响应返回不成功")

    def parse_keys(self, response):
        meta = response.meta
        item = meta['item']

        try:
            json_response = json_loads(response.text)
            if json_response['RSP_HEAD']['TRAN_SUCCESS'] == '1':
                keys = json_response['RSP_BODY']['keys']
                real_keys = unquote(keys)

                password_keys = []
                password_dict = self.password_dict
                for char in item['password']:
                    password_keys.append(real_keys[password_dict.get(char, '')])
                req_password = ''.join(password_keys)

                req_data = {
                    'User-Agent': 'MbankView',
                    'processCode': 'MB0059',
                    'tokenAuth': 'F',
                    'SMSCertAuth': 'F',
                    'wisdomCertAuth': 'F',
                    'returnVal': '',
                    'visualTokenAuth': 'F',
                    'mobileAuth': 'T',
                    'optAuthMode': 'T',
                    'alias': item['username'],
                    'password': req_password,
                    'MSessionId': meta["m_session_id"],
                    'isWap': '1',
                    'pageCode': 'NLG0001',
                    'targetPageCode': 'NLG0001'
                }
                yield FormRequest(
                    url=self.request_url,
                    callback=self.parse_login,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                yield from self.error_handle(item['username'], "交通银行wap---获取密码keys时响应返回出错",
                                             tell_msg="获取keys响应状态出错")
        except Exception:
            yield from self.except_handle(item['username'], "交通银行wap---获取密码keys",
                                          tell_msg="获取keys响应返回不成功")

    def parse_login(self, response):
        meta = response.meta

        try:
            json_response = json_loads(response.text)
            if json_response['RSP_HEAD']['TRAN_SUCCESS'] == '1':
                req_data = {
                    'processCode': 'AC0001',
                    'accountType': '0',
                    'queryBalance': '0',
                    'lossFlag': '1',
                    'MSessionId': meta["m_session_id"],
                    'isWap': '1',
                    'pageCode': 'NAC0001',
                    'targetPageCode': 'NAC0001',
                }
                yield FormRequest(
                    url=self.request_url,
                    callback=self.parse_account,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                yield from self.error_handle(meta['item']['username'], "交通银行wap---登入时响应返回出错",
                                             tell_msg="账户或密码错误")
        except Exception:
            yield from self.except_handle(meta['item']['username'], "交通银行wap---登录",
                                          tell_msg="登录响应返回不成功")

    def parse_account(self, response):
        meta = response.meta
        item = meta['item']
        username = item['username']

        try:
            json_response = json_loads(response.text)
            if json_response['RSP_HEAD']['TRAN_SUCCESS'] == '1':
                card_list = json_response['RSP_BODY']['debitCardList']
                for card in card_list:
                    if card.get('account') == username:
                        item['balance'] = card.get('accUsableBalance')

                today = strftime("%Y%m%d")
                begin_day = str(int(today) - 10000)  # 一年
                meta["current_page"] = 1
                req_data = {
                    'timeout': '0',
                    'page': "1",
                    'pageSize': self.page_size,
                    'processCode': 'AC0005',
                    'account': username,
                    'beginDate': begin_day,
                    'endDate': today,
                    'minAmount': '',
                    'maxAmount': '',
                    'currency': 'CNY',
                    'otherCondition': '',
                    'DCFlag': '',
                    'endFlag': '0',
                    'beginRecord': '',
                    'tradeWay': '0',
                    'tradePlace': '',
                    'tradeBank': '',
                    'accName': '',
                    'accNo': '',
                    'remark': '',
                    'MSessionId': meta["m_session_id"],
                    'isWap': '1',
                    'pageCode': 'NAC0002',
                    'targetPageCode': 'NAC0002',
                }
                yield FormRequest(
                    url=self.request_url,
                    callback=self.parse_detail,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                yield from self.error_handle(username, "交通银行wap---账户余额信息响应返回出错",
                                             tell_msg="账户信息有误")
        except Exception:
            yield from self.except_handle(username, "交通银行wap---获取余额",
                                          tell_msg="账户余额信息响应返回不成功")

    def parse_detail(self, response):
        meta = response.meta
        item = meta['item']
        trade_records = item["trade_records"]
        try:
            json_response = json_loads(response.text)
            if json_response['RSP_HEAD']['TRAN_SUCCESS'] == '1':
                account_detail_list_10 = json_response['RSP_BODY']['accountDetailsList']
                if account_detail_list_10:
                    for account_detail in account_detail_list_10:
                        if account_detail['dcFlg'] == 'C':
                            income = account_detail['amount']
                            outcome = ''
                        else:
                            income = ''
                            outcome = account_detail['amount']

                        trade_records.append({
                            'trade_date': account_detail.get('dealTime', ''),
                            'trade_type': account_detail.get('dealType', ''),
                            'trade_currency': json_response['RSP_BODY']['currency'],
                            'trade_location': account_detail.get('txnBrpla', ''),
                            'trade_remark': account_detail.get('remark', ''),
                            'trade_accounting_date': account_detail.get('webTime', '')[:8]
                            if account_detail.get('remark', '') else '',
                            'trade_outcome': outcome,
                            'trade_income': income,
                            'trade_acceptor_account': account_detail.get('oppAc', ''),
                            'trade_acceptor_name': account_detail.get('oppAcNme', ''),
                            'trade_balance': account_detail.get('balance', ''),
                            'trade_amount': income or ("-" + outcome),
                        })

                    meta["current_page"] += 1
                    today = strftime("%Y%m%d")
                    req_data = {
                        'timeout': '0',
                        'page': str(meta["current_page"]),
                        'pageSize': self.page_size,
                        'processCode': 'AC0005',
                        'account': item['username'],
                        'beginDate': str(int(today) - 10000),  # 一年,
                        'endDate': today,
                        'minAmount': '',
                        'maxAmount': '',
                        'currency': 'CNY',
                        'otherCondition': '',
                        'DCFlag': '',
                        'endFlag': '0',
                        'beginRecord': '',
                        'tradeWay': '0',
                        'tradePlace': '',
                        'tradeBank': '',
                        'accName': '',
                        'accNo': '',
                        'remark': '',
                        'MSessionId': meta["m_session_id"],
                        'isWap': '1',
                        'pageCode': 'NAC0002',
                        'targetPageCode': 'NAC0002',
                    }
                    yield FormRequest(
                        url=self.request_url,
                        callback=self.parse_detail,
                        formdata=req_data,
                        meta=meta,
                        dont_filter=True,
                        errback=self.err_callback
                    )
                else:
                    if 'balance' not in item and trade_records:
                        item['balance'] = trade_records[-1].get('trade_balance', 0)

                    yield from self.crawling_done(item)
            else:

                if 'balance' not in item and trade_records:
                    item['balance'] = trade_records[-1].get('trade_balance', 0)

                yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item['username'], "交通银行wap---获取详情时响应返回不为200",
                                          tell_msg="数据响应返回不成功")
