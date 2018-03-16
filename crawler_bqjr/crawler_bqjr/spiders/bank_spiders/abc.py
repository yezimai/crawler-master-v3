# -*- coding: utf-8 -*-

from datetime import date
from time import sleep

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import TimeoutException

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import IEWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes, find_str_range


#################################################
# 农行爬虫
#################################################
class ABCSpider(IEWebdriverSpider, BankSpider):
    name = "bank_abc"
    allowed_domains = ["abchina.com"]
    start_urls = ["http://www.abchina.com/cn/"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_delta = relativedelta(years=1)

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]

        driver = self.load_page_by_webdriver("https://perbank.abchina.com/EbankSite/startup.do",
                                             "//input[@id='username']")
        pid = driver.iedriver.process.pid
        try:
            driver.maximize_window()

            with Ddxoft(pid) as visual_keyboard:
                driver.execute_script("username_input=document.getElementById('username');"
                                      "username_input.value='%s';"
                                      "username_input.focus();" % username)
                visual_keyboard.dd_tab()
                sleep(0.1)
                for key in item["password"]:
                    visual_keyboard.dd_keyboard(key)
                    sleep(1.3)  # 这样输入密码比较安全

            # driver.execute_script("document.getElementById('userNameForm').pwdField.value='"
            #                       + item["password"] + "';")

            # 检查是否需要输入验证码
            if driver.find_element_by_id("code").is_displayed():
                with Ddxoft(pid) as visual_keyboard:
                    visual_keyboard.dd_tab()
                captcha_image = driver.find_element_by_id("vCode")
                location = captcha_image.location
                size = captcha_image.size
                left = location["x"] - 8
                top = location["y"]
                right = left + size["width"]
                bottom = top + size["height"]

                photo_base64 = driver.get_screenshot_as_base64()
                captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".png")
                with Ddxoft(pid) as visual_keyboard:
                    driver.execute_script("captcha_input=document.getElementById('code');"
                                          "captcha_input.value='%s';"
                                          "captcha_input.focus();" % captcha_code)
                    visual_keyboard.dd_tab()
                try:
                    self.wait_xpath(driver, "//span[@class='v-code-error right']",
                                    raise_timeout=True, timeout=3)
                except TimeoutException:
                    yield from self.error_handle(username, "农业银行---图形验证码错误",
                                                 "图形验证码错误，请刷新页面重试。")
                    return

            driver.execute_script("document.getElementById('logo').click();")
            try:
                self.wait_xpath(driver, "//a[@id='logout_a']", raise_timeout=True, timeout=6)
            except TimeoutException:
                tell_msg = driver.find_element_by_id('powerpass_ie_dyn_Msg').text or \
                           driver.find_element_by_class_name("logon-error").get_attribute("title")
                yield from self.error_handle(username, "农业银行---登录失败:(username:%s, password:%s) %s"
                                             % (username, item["password"], '登录失败'),
                                             tell_msg=tell_msg)
                return

            self.wait_xpath(driver, "//iframe[@id='contentFrame']")
            driver.switch_to.frame("contentFrame")
            self.wait_xpath(driver, "//div[@id='m-paycardcontent']")
            item['balance'] = driver.find_element_by_id("dnormal").text

            # 跳转到银行流水界面
            onclick_fun_str = "toDetail('%s')" % username
            self.wait_xpath(driver, '//a[@onclick="%s"]' % onclick_fun_str)
            driver.switch_to.default_content()
            driver.execute_script('document.getElementById("contentFrame").contentWindow.'
                                  + onclick_fun_str + ';')

            self.wait_xpath(driver, "//iframe[@id='contentFrame']")
            driver.switch_to.frame("contentFrame")
            self.wait_xpath(driver, '//input[@id="startDate"]')
            driver.switch_to.default_content()
            end_date = date.today()

            # 有可能失败，执行两次
            start_date_str = (end_date - self.date_delta).strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            for i in range(2):
                driver.execute_script('data_iframe=document.getElementById("contentFrame").contentDocument;'
                                      'data_iframe.getElementById("startDate").value="%s";'
                                      'data_iframe.getElementById("endDate").value="%s";'
                                      % (start_date_str, end_date_str))
                sleep(0.6)
            driver.execute_script('data_iframe.getElementById("btn_query").click();')

            item["trade_records"] = self.parse_item_from_webpage(driver)

            yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "农业银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, msg="农业银行---错误信息",
                                          tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        finally:
            driver.quit()

    #######################################################
    # 从银行流水页面解析出item
    #######################################################
    def parse_item_from_webpage(self, driver):
        trade_detail = []
        html_set = set()
        page_count = 0
        trade_count_per_page = 10

        wait_xpath = self.wait_xpath
        while True:
            driver.switch_to.default_content()
            wait_xpath(driver, "//iframe[@id='contentFrame']")
            driver.switch_to.frame("contentFrame")
            wait_xpath(driver, "//tbody[@id='AccountTradeDetailTable']", displayed=True)

            html = find_str_range(driver.page_source, '<tbody id="AccountTradeDetailTable"', '/tbody>')
            if html in html_set:
                continue  # 数据还没刷新

            bs_obj = BeautifulSoup(html, "lxml")
            trs = bs_obj.findAll("tr")
            trs_len = len(trs)

            if (trs_len == 0 and page_count != 0) \
                    or (trs_len < trade_count_per_page
                        and driver.find_element_by_id("nextPage").is_displayed()):
                continue

            html_set.add(html)
            for data_item in trs:
                try:
                    trade = {}
                    (trade["trade_date"], trade_amount, trade["trade_balance"],
                     trade["trade_acceptor_name"], trade["trade_type"], trade["trade_channel"],
                     trade["trade_remark"], _) = [i.get_text(strip=True) for i in data_item.findAll("td")]

                    trade["trade_amount"] = trade_amount
                    if trade_amount.startswith("-"):
                        trade["trade_outcome"] = trade_amount.lstrip("-")
                    else:
                        trade["trade_income"] = trade_amount.lstrip("+")

                    trade_detail.append(trade)
                except Exception:
                    self.logger.exception("农业银行---解析交易详情数据出错")

            try:
                if trs_len == trade_count_per_page and driver.find_element_by_id("nextPage").is_displayed():
                    driver.switch_to.default_content()
                    driver.execute_script('document.getElementById("contentFrame").contentDocument'
                                          '.getElementById("nextPage").click();')
                    page_count += 1
                else:
                    return trade_detail
            except Exception:
                return trade_detail
