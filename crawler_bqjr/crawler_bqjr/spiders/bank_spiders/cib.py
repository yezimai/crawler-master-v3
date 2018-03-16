# -*- coding: utf-8 -*-

from datetime import date
from re import compile as re_compile

from dateutil.relativedelta import relativedelta
from scrapy import FormRequest

from crawler_bqjr.spiders.bank_spiders.base import BankSpider


class CibSpider(BankSpider):
    """
        兴业银行爬虫
    """
    name = "bank_cib"
    allowed_domains = ["cib.com.cn"]
    start_urls = ["https://3g.cib.com.cn/app/00002.html"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_url = self._start_url_
        self.sleep_time = 3
        self.date_delta = relativedelta(years=1)
        self.count_pattern = re_compile(r"(\d+)笔")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
        }

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        item = request.meta["item"]
        item["identification_number"] = account_info["id"]
        return request

    def get_logout_request(self, meta):
        form_data = {"flowsn": "130",
                     }
        return FormRequest(self.login_url, self.parse_logout, meta=meta,
                           formdata=form_data, errback=self.parse_logout, dont_filter=True)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            password = item["password"]
            form_data = {"flowsn": "402",
                         "select_flag": "0",
                         "loginname": item["username"],
                         "pwd": password,
                         "hsm_pwd": password,
                         "req_zjhm": item["identification_number"],
                         "doyzm": "0",
                         # "yzmkey": "",
                         }
            yield FormRequest(self.login_url, self.parse_login, headers=self.headers, meta=meta,
                              formdata=form_data, errback=self.err_callback, dont_filter=True)
        except Exception:
            yield from self.except_handle(item["username"], "兴业银行---登录入口")

    def parse_login(self, response):
        try:
            if "欢迎登录" in response.text:
                # 账户查询
                form_data = {"flowsn": "50",
                             "secmenu": "0200000301",
                             }
                yield FormRequest("https://3g.cib.com.cn/app/80820.html",
                                  self.parse_inquiry, headers=self.headers,
                                  meta=response.meta, formdata=form_data,
                                  errback=self.err_callback, dont_filter=True)
            else:
                msg = response.xpath("//p[contains(@class,'result-describe')]/text()").extract_first()
                yield from self.error_handle(response.meta["item"]["username"], "登录失败", msg)
        except Exception:
            yield from self.except_handle(response.meta["item"]["username"], "兴业银行---登录")

    def parse_inquiry(self, response):
        meta = response.meta
        # 交易明细
        try:
            meta["item"]["balance"] = response.xpath("//span[@id='hqye_value']/text()").extract_first("").strip()
            today_date = date.today()
            form_data = {'flowsn': '15',
                         'month': '',
                         'xxh': '001',  # 人民币
                         'begindate': (today_date - self.date_delta).strftime("%Y%m%d"),
                         'enddate': today_date.strftime("%Y%m%d"),
                         'qsje': '',
                         'zzje': '',
                         'qrytype': '1'
                         }
            yield FormRequest("https://3g.cib.com.cn/app/10040.html",
                              self.parse_transaction, headers=self.headers, dont_filter=True,
                              meta=meta, formdata=form_data, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta["item"]["username"], "兴业银行---账户查询")

    def parse_transaction(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            trade_records = item["trade_records"]
            transaction_list = response.xpath("//div[@class='info-wrap']/a")
            for transaction in transaction_list:
                trade = {}
                trade["trade_date"], trade_amount = transaction.xpath("..//span/text()").extract()
                trade["trade_remark"] = transaction.xpath("h3/text()").extract_first("").rstrip()
                trade["trade_acceptor_name"] = transaction.xpath("..//p[@class='c1']/em/text()").extract_first()

                trade["trade_amount"] = trade_amount
                if trade_amount.startswith("-"):
                    trade["trade_outcome"] = trade_amount.lstrip("-")
                else:
                    trade["trade_income"] = trade_amount
                trade_records.append(trade)

            next_page = response.xpath("//a[text()='下一页' and @href]")
            if next_page and len(transaction_list) == 10:
                form_data = {'flowsn': '75',
                             'beginNo': str(len(trade_records) + 1),
                             }
                yield FormRequest("https://3g.cib.com.cn/app/10040.html",
                                  self.parse_transaction, headers=self.headers, dont_filter=True,
                                  meta=meta, formdata=form_data, errback=self.err_callback)
            else:
                income_count, outcome_count = response.xpath("//section[contains(@class,'all-income')]"
                                                             "/p/text()").extract()
                count_pattern = self.count_pattern
                trade_count = (int(count_pattern.search(income_count).group(1))
                               + int(count_pattern.search(outcome_count).group(1)))

                if trade_count != len(trade_records):
                    self.logger.error("兴业银行---交易记录数异常：(username:%s, password:%s)"
                                      % (item["username"], item["password"]))
                yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "兴业银行---交易明细")
