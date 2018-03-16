# -*- coding: utf-8 -*-

from datetime import date
from random import random
from re import compile as re_compile

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import NoSuchElementException

from crawler_bqjr.spider_class import PhantomJSWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import find_str_range, get_content_by_requests, \
    get_cookies_dict_from_webdriver, driver_screenshot_2_bytes


class PinganWapSpider(PhantomJSWebdriverSpider, BankSpider):
    """
        平安银行爬虫
    """
    name = "bank_pingan_wap"
    allowed_domains = ["pingan.com"]
    start_urls = ["http://m.pingan.com/t/QuickIndex.screen?f=ba&v=2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, load_images=False, **kwargs)
        self.headers = {
            "Host": "m.pingan.com",
            "Referer": "https://m.pingan.com/t/QuickIndex.screen?f=ba&v=2",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.date_delta = relativedelta(days=100)
        self.trade_sep_pattern = re_compile(r"[\n\t]+")

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]
        password = item["password"]

        driver = self.load_page_by_webdriver(response.url, "//img[@id='rndCodeCue']")
        try:
            driver.maximize_window()
            captcha_code = self._get_captcha_code_by_phantomJS(driver, username)
            driver.execute_script('document.getElementsByName("userId")[0].value="%s";'
                                  'document.getElementById("pwd").value="%s";'
                                  'document.getElementsByName("rndCode")[0].value="%s";'
                                  'submit_form();'
                                  % (username, password, captcha_code))
            page_source = driver.page_source
            if "名、密" in page_source or "证码输" in page_source:
                yield from self.error_handle(username, "平安银行---登录",
                                             driver.find_element_by_xpath("//p[@class='orange']").text)
            else:
                item["trade_records"] = self._login_success(driver)
                yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "平安银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "平安银行---爬取")
        finally:
            driver.quit()

    def _get_captcha_code_by_chrome(self, driver, username):
        captcha_xpath = "//img[@id='rndCodeCue']"
        self.wait_xpath(driver, captcha_xpath)
        captcha_element = driver.find_element_by_xpath(captcha_xpath)
        location = captcha_element.location
        size = captcha_element.size
        left = location["x"]
        top = location["y"]

        photo_base64 = driver.get_screenshot_as_base64()
        captcha_body = driver_screenshot_2_bytes(photo_base64,
                                                 (left, top, left + size["width"], top + size["height"]))
        return self.ask_image_captcha(captcha_body, username, file_type=".png")

    def _get_captcha_code_by_phantomJS(self, driver, username):
        url = "http://m.pingan.com/t/ImageGif.do?v=2&rd=%s&amp;imageNum=359" % random()
        cookiejar = get_cookies_dict_from_webdriver(driver)
        captcha_body = get_content_by_requests(url, self.headers, cookie_jar=cookiejar)
        captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".jpeg")
        return captcha_code

    def _login_success(self, driver):
        wait_xpath = self.wait_xpath

        account_xpath = "//a[text()='账户明细']"
        wait_xpath(driver, account_xpath)
        url = driver.find_element_by_xpath(account_xpath).get_attribute("href")
        driver.get(url)

        start_date_xpath = "//input[@id='startDate']"
        wait_xpath(driver, start_date_xpath)
        driver.execute_script('document.getElementById("startDate").value="%s";'
                              'document.getElementsByName("button")[1].click();'
                              % (date.today() - self.date_delta).strftime("%Y%m%d"))

        next_page_xpath = "//a[text()='下页']"
        trade_sep_pattern = self.trade_sep_pattern
        trade_records = []
        trade_set = set()

        while True:
            wait_xpath(driver, "//a[text()='返回重新查询']")

            html = find_str_range(driver.page_source, '<div class="com_div"', '<div class="atag_b')
            bs_obj = BeautifulSoup(html, "lxml")
            for div in bs_obj.findAll("div", {"class": "com_div"}):
                info_dict = dict(i.split("：", maxsplit=1) for i
                                 in trade_sep_pattern.split(div.get_text(strip=True)))
                trade_balance = info_dict.get("账户余额", "")
                trade_date = info_dict.get("交易日期", "")
                key = trade_date + trade_balance
                if key not in trade_set:
                    trade = {
                        "trade_date": trade_date,
                        "trade_remark": info_dict.get("摘要", ""),
                        "trade_balance": trade_balance,
                    }
                    trade_records.append(trade)
                    trade_set.add(key)

            try:
                url = driver.find_element_by_xpath(next_page_xpath).get_attribute("href")
            except NoSuchElementException:
                return trade_records
            else:
                driver.get(url)
