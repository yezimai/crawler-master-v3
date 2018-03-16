# -*- coding: utf-8 -*-

from datetime import date
from time import sleep

from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import TimeoutException
from xlrd import open_workbook

from crawler_bqjr.mail import send_mail_2_admin
from crawler_bqjr.spider_class import HeadlessChromeWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, \
    get_content_by_requests_post, get_content_by_requests, get_js_time
from global_utils import json_loads


class PinganSpider(HeadlessChromeWebdriverSpider, BankSpider):
    """
        平安银行爬虫
    """
    name = "bank_pingan"
    allowed_domains = ["pingan.com"]
    start_urls = ["https://bank.pingan.com.cn/ibp/bank/index.html#home/home/index/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, load_images=False, **kwargs)
        self.login_url = self._start_url_
        self.headers = {
            "Host": "bank.pingan.com.cn",
            "Referer": "https://bank.pingan.com.cn/ibp/bank/index.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.date_delta = relativedelta(years=1, days=-1)

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]
        password = item["password"]

        url = self.login_url + get_js_time() + "?returnURL=account%2Findex%2FtransferList"
        driver = self.load_page_by_webdriver(url, "//div[@id='pwdObject1-btn-pan']")
        try:
            try:
                if driver.find_element_by_id("verifyCode").is_displayed():
                    url = "https://bank.pingan.com.cn/ibp/portal/pc/getVcode2.do?" + get_js_time()
                    cookiejar = get_cookies_dict_from_webdriver(driver)
                    capcha_body = get_content_by_requests(url, headers=self.headers,
                                                          cookie_jar=cookiejar)
                    captcha_code = self.ask_image_captcha(capcha_body, username)
                    driver.execute_script('document.getElementById("verifyCode").value="'
                                          + captcha_code + '";')
            except CaptchaTimeout:
                raise
            except Exception:
                self.logger.exception("平安银行---图片验证码")

            # 填写用户名和密码
            driver.execute_script('document.getElementById("pwdObject1-btn-pan").click();'
                                  'document.getElementById("userName").value="%s";'
                                  'document.getElementById("pwdObject1-input").value="%s";'
                                  'document.getElementById("login_btn").click();'
                                  % (username, password))

            try:
                self.wait_xpath(driver, "//li[@id='safe_logout']", raise_timeout=True, timeout=6)
            except TimeoutException:
                page_source = driver.page_source
                if "密码错" in page_source:
                    yield from self.error_handle(username, "平安银行---登录",
                                                 driver.find_element_by_xpath("//span[@id='errorLoginMsg']").text)
                elif "证码错" in page_source:
                    yield from self.error_handle(username, "平安银行---登录",
                                                 driver.find_element_by_xpath("//span[@id='verifyError']").text)
                else:
                    yield from self.error_handle(username, "平安银行---登录异常(%s)" % page_source, "登录失败")
            else:
                item["balance"], item["trade_records"] = self._login_success(driver)
                yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "平安银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "平安银行---爬取", "爬取异常")
        finally:
            driver.quit()

    def _download_trades_by_requests(self, driver):
        self.wait_xpath(driver, "//input[@id='account_select']")
        self.wait_xpath(driver, "//input[@id='download_accNo']")

        account = (driver.find_element_by_id("download_accNo").get_attribute("value")
                   or driver.find_element_by_id("account_select").get_attribute("selectkey"))
        while not account:
            sleep(0.1)
            account = (driver.find_element_by_id("download_accNo").get_attribute("value")
                       or driver.find_element_by_id("account_select").get_attribute("selectkey"))

        today_date = date.today()
        form_data = {'pageNum': '1',
                     'pageSize': '99999',
                     'accNo': account,
                     'currType': 'RMB',
                     'startDate': (today_date - self.date_delta).strftime("%Y%m%d"),
                     'endDate': today_date.strftime("%Y%m%d")
                     }
        url = "https://bank.pingan.com.cn/ibp/ibp4pc/work/transfer/downloadTransferDetail.do"
        cookiejar = get_cookies_dict_from_webdriver(driver)
        datas = get_content_by_requests_post(url, data=form_data, headers=self.headers,
                                             cookie_jar=cookiejar)

        trade_records = []
        with open_workbook(file_contents=datas) as bk:
            infos_sheet = bk.sheet_by_index(0)
            for i in range(2, infos_sheet.nrows):
                trade = {}
                row_data = infos_sheet.row_values(i)
                (trade["trade_date"], trade["trade_acceptor_name"], trade["trade_acceptor_account"],
                 trade_type, trade_amount, trade["trade_balance"], trade["trade_remark"],
                 trade["trade_name"]) = row_data[:8]

                trade["trade_type"] = trade_type
                if trade_type == "转出":
                    trade["trade_amount"] = "-" + trade_amount
                    trade["trade_outcome"] = trade_amount
                elif trade_type == "转入":
                    trade["trade_amount"] = trade_amount
                    trade["trade_income"] = trade_amount
                else:
                    msg = "平安银行---未知trade_type: " + trade_type
                    self.logger.critical(msg)
                    send_mail_2_admin("平安银行---未知trade_type", msg)

                trade_records.append(trade)

        return trade_records

    def _get_balance_by_requests(self, driver):
        form_data = {'channelType': 'd',
                     'responseDataType': 'JSON',
                     }
        url = "https://bank.pingan.com.cn/ibp/ibp4pc/work/account/acctInfoForIndex.do"
        cookiejar = get_cookies_dict_from_webdriver(driver)
        datas = get_content_by_requests_post(url, data=form_data, headers=self.headers,
                                             cookie_jar=cookiejar)

        if b'"errCode":"000"' in datas:  # 成功
            return json_loads(datas)["responseBody"]["cardBalanceList"][0]["balance"]
        else:
            return None

    def _login_success(self, driver):
        # # 设置时间
        # start_date_xpath = "//input[@id='tranListDate_start']"
        # self.wait_xpath(driver, start_date_xpath)
        # driver.execute_script('document.getElementById("tranListDate_start").value="%s";'
        #                       'document.getElementById("query_tranList_btn").click();'
        #                       % (date.today() - self.date_delta).strftime("%Y-%m-%d"))
        #
        # # 点击下载
        # download_xpath = "//p[@id='downloadTransferDetailBtn']"
        # self.wait_xpath(driver, download_xpath)
        # driver.execute_script('document.getElementById("downloadTransferDetailBtn").click();')

        trade_records = self._download_trades_by_requests(driver)
        balance = self._get_balance_by_requests(driver)
        return balance, trade_records
