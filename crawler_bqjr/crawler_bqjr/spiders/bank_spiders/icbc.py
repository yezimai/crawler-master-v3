# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.mail import send_mail_2_admin
from crawler_bqjr.spider_class import IEWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import find_str_range, driver_screenshot_2_bytes


class IcbcSpider(IEWebdriverSpider, BankSpider):
    """
        工商银行爬虫
    """
    name = "bank_icbc"
    allowed_domains = ["icbc.com.cn"]
    start_urls = ["https://mybank.icbc.com.cn/icbc/newperbank/perbank3/frame/frame_index.jsp"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_url = self._start_url_
        self.retry_times = 10
        self.trade_sep_pattern = re_compile(r"\n+")

    def _first_auth(self, driver, username):
        for i in range(self.retry_times):
            try:
                # driver.find_element_by_xpath("//span[text()='短信认证']").click()
                driver.execute_script('document.getElementsByClassName("ebdp-pc4promote-menu-level1")[0]'
                                      '.getElementsByTagName("li")[1].click();')
                driver.switch_to.frame('integratemainFrame')
                driver.find_element_by_xpath("//span[@id='sendSMSCode']")
            except Exception:
                driver.switch_to.default_content()
                continue
            else:
                break
        else:
            self.logger.error('"短信认证"不能点击')
            raise Exception

        driver.execute_script('SendVerifyCode();')
        sms_code = self.ask_sms_captcha(username)
        driver.switch_to.default_content()
        driver.execute_script('document.getElementsByName("integratemainFrame")[0]'
                              '.contentDocument.getElementsByName("userSubmitSignVerifyCode")[0]'
                              '.value=%s;' % sms_code)
        # 输入验证码
        captcha_code = self.__get_captcha_code(driver, username, False)
        self.logger.info("图片验证码: %s" % captcha_code)
        driver.switch_to.default_content()

        pid = driver.iedriver.process.pid
        with Ddxoft(pid) as visual_keyboard:
            driver.execute_script('document.getElementsByName("integratemainFrame")[0]'
                                  '.contentDocument.getElementsByName("userSubmitSignVerifyCode")[0].focus();')
            sleep(1)
            visual_keyboard.dd_tab()
            for key in captcha_code:
                visual_keyboard.dd_keyboard(key)

        driver.switch_to.frame('integratemainFrame')
        driver.execute_script("formCheck('0');")

        sleep(1)
        html = driver.page_source
        if "交易失败" in html:
            info = driver.find_element_by_xpath("//div[@class='zzhk-jnhk-info']").text
            self.logger.info("认证失败:%s" % info)
        else:
            self.wait_xpath(driver, "//div[@id='queding']")
            driver.execute_script('document.getElementById("queding").click()')
            self.logger.info("--->认证成功")

    def _download_trades(self, driver):
        driver.switch_to.default_content()
        driver.execute_script('content_frame=document.getElementById("perbank-content-frame").'
                              'contentDocument.getElementById("content-frame").contentDocument;'
                              'content_frame.getElementById("styFlag").value=1;')
        driver.switch_to.frame("perbank-content-frame")
        driver.switch_to.frame("content-frame")
        download_func_str = driver.find_element_by_xpath("//div[@id='xiazai']/..").get_attribute("href")
        driver.execute_script(download_func_str + ";")

    def _get_trades(self, driver):
        trade_records = []
        next_page_xpath = "//a[text()='【下一页】']"
        trade_sep_pattern = self.trade_sep_pattern
        wait_xpath = self.wait_xpath
        html_set = set()
        page_count = 0
        trade_count_per_page = 20

        while True:
            sleep(0.1)
            wait_xpath(driver, "//div[contains(text(),'合计（人民币）')]")
            html = find_str_range(driver.page_source, '<table class="lst tblWidth"', '/tbody>')
            if html in html_set:
                continue  # 数据还没刷新

            bs_obj = BeautifulSoup(html, "lxml")
            trs = bs_obj.findAll("tr")[1:]
            trs_len = len(trs)

            if trs_len == 0 and page_count != 0:
                continue  # 非首页，应不会出现为空的情况
            elif trs_len < trade_count_per_page:
                try:
                    driver.find_element_by_xpath(next_page_xpath)
                except NoSuchElementException:
                    pass
                else:
                    continue

            html_set.add(html)
            for tr in trs:
                trade = {}
                try:
                    (trade["trade_date"], trade["trade_remark"], trade_amount,
                     trade["trade_currency"], trade["trade_balance"], trade["trade_acceptor_name"],
                     _) = trade_sep_pattern.split(tr.get_text(strip=True))

                    trade["trade_amount"] = trade_amount
                    if trade_amount.startswith("-"):
                        trade["trade_outcome"] = trade_amount.lstrip("-")
                    else:
                        trade["trade_income"] = trade_amount.lstrip("+")

                    more_info = tr.findAll("td")[-1].a.attrs["href"].split("',")
                    trade_type = more_info[0]
                    if trade_type.startswith("Detail", 15):
                        trade["trade_location"] = more_info[6].strip().strip("'")
                        trade["trade_acceptor_account"] = more_info[16].strip().strip("')")
                    elif trade_type.startswith("History", 15):
                        trade["trade_acceptor_account"] = more_info[6].strip().strip("')")
                    else:
                        msg = "工行---未知交易类型: " + tr.findAll("td")[-1].a
                        self.logger.critical(msg)
                        send_mail_2_admin("工行---未知交易类型", msg)
                except Exception:
                    self.logger.exception("工行---交易明细条目")
                finally:
                    trade_records.append(trade)

            try:
                if trs_len == trade_count_per_page:
                    wait_xpath(driver, next_page_xpath, timeout=3)
                next_func_str = driver.find_element_by_xpath(next_page_xpath).get_attribute("href")
            except NoSuchElementException:
                return trade_records
            else:
                driver.execute_script(next_func_str)
                page_count += 1

    def __switch_to_content_frame(self, driver):
        self.wait_xpath(driver, "//iframe[@id='perbank-content-frame']")
        driver.switch_to.frame("perbank-content-frame")
        self.wait_xpath(driver, "//iframe[@id='content-frame']")
        driver.switch_to.frame("content-frame")

    def _login_success(self, driver, account_num):
        # 点击我的账户
        account_xpath = "//p[text()='我的账户']"
        self.wait_xpath(driver, account_xpath)
        account_func_str = driver.find_element_by_xpath(account_xpath + "/../..").get_attribute("onclick")
        driver.execute_script(account_func_str)

        # 点击明细
        self.__switch_to_content_frame(driver)
        trade_xpath = "//li[text()='明细']"
        self.wait_xpath(driver, trade_xpath)

        balance = None
        html = find_str_range(driver.page_source, '<div class="kabao-main-item-box"', '/ul>')
        while ">人民币<" not in html:
            sleep(0.1)
            html = find_str_range(driver.page_source, '<div class="kabao-main-item-box"', '/ul>')

        onclick_func_str = driver.find_element_by_xpath(trade_xpath).get_attribute("onclick")
        bs_obj = BeautifulSoup(html, "lxml")
        for div in bs_obj.find_all("div", {"class": "kabao-main-item-box"}):
            try:
                tbody = div.find("tbody")
                if tbody.attrs["id"].endswith(account_num):
                    rmb_tr = tbody.find("span", text="人民币").parent.parent
                    balance = rmb_tr.findAll("td")[-1].get_text(strip=True)
                    onclick_func_str = div.find("li", text="明细")["onclick"]
                    break
            except Exception:
                self.logger.exception("工商银行---余额")

        driver.execute_script(onclick_func_str)

        # 选择明细时间
        driver.switch_to.default_content()
        self.__switch_to_content_frame(driver)
        self.wait_xpath(driver, "//span[@num='-1']")
        driver.execute_script("""$("span[num='-1']").click()""")  # 近一年

        query_func_str = driver.find_element_by_xpath("//div[@id='chaxun']/..").get_attribute("href")
        driver.execute_script(query_func_str)
        trade_records = self._get_trades(driver)

        return balance, trade_records

    def __get_captcha_code(self, driver, username, flag=True):
        if flag:
            driver.switch_to.frame('ICBC_login_frame')
        else:
            driver.switch_to.frame('integratemainFrame')
        driver.switch_to.frame('VerifyimageFrame')
        captcha_xpath = "//img[@title='点击图片可刷新']"
        self.wait_xpath(driver, captcha_xpath)
        location = driver.find_element_by_xpath(captcha_xpath).location_once_scrolled_into_view
        left = location["x"] + 8
        top = location["y"]

        driver.switch_to.default_content()
        photo_base64 = driver.get_screenshot_as_base64()
        captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, left + 90, top + 36))
        return self.ask_image_captcha(captcha_body, username, file_type=".png")

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]
        password = item["password"]

        driver = self.load_page_by_webdriver(self.login_url)
        try:
            driver.maximize_window()
            for i in range(100):
                sleep(0.1)
                page_source = driver.page_source.lower()
                if page_source.endswith("/html>"):
                    break
            else:
                raise Exception("首页加载失败")

            if "onemap" in page_source:  # 第一次使用提示
                driver.get(self.login_url)

            # 登录
            self.wait_xpath(driver, "//iframe[@id='ICBC_login_frame']", raise_timeout=True)

            pid = driver.iedriver.process.pid
            with Ddxoft(pid) as visual_keyboard:
                driver.execute_script('login_iframe=document.getElementById("ICBC_login_frame").contentDocument;'
                                      'username_input=login_iframe.getElementById("logonCardNum");'
                                      'username_input.focus();'
                                      'username_input.value="' + username + '";')
                visual_keyboard.dd_tab()
                for key in password:
                    visual_keyboard.dd_keyboard(key)

            captcha_code = self.__get_captcha_code(driver, username)
            driver.execute_script('login_iframe.getElementById("verifyCodeCn").value="'
                                  + captcha_code.lower() + '";')

            # 登录
            driver.switch_to.frame('ICBC_login_frame')
            driver.execute_script("loginSubmit();")
            sleep(3)

            # 处理弹出框
            try:
                alert = driver.switch_to.alert
                self.logger.info("Alert:%s" % alert.text)
                alert.accept()
            except Exception:
                pass

            if "onemap" in driver.page_source:  # 第一次使用提示
                driver.find_element_by_xpath("//form[@name='form']").submit()

            driver.switch_to.default_content()
            try:
                self.wait_xpath(driver, "//i[contains(text(),'欢迎您')]",
                                raise_timeout=True, timeout=6)
            except TimeoutException:
                if "短信认证" in driver.page_source:  # 第一使用本机登录的认证
                    self.logger.info("需要认证")
                    self._first_auth(driver, username)
                else:
                    driver.switch_to.frame('ICBC_login_frame')
                    error = driver.find_element_by_id("errors").text
                    yield from self.error_handle(username, "工商银行---登录失败", tell_msg=error)
                    return

            item["balance"], item["trade_records"] = self._login_success(driver, username)
            yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "工商银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "工商银行---爬取")
        finally:
            driver.quit()
