# -*- coding: utf-8 -*-

from datetime import date
from re import compile as re_compile
from time import sleep

from dateutil.relativedelta import relativedelta
from scrapy import Selector
from selenium.common.exceptions import NoSuchElementException

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import IE233WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, get_content_by_requests


class HxbSpider(IE233WebdriverSpider, BankSpider):
    name = "bank_hxb"
    allowed_domains = ["hxb.com.cn"]
    start_urls = ["http://www.hxb.com.cn/home/cn/", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        login_url = "https://sbank.hxb.com.cn/easybanking/jsp/indexComm.jsp"
        self.headers = {
            "Referer": login_url,
            "Origin": "http://www.hxb.com.cn/home/cn/",
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,en,*"
        }
        self.login_url = login_url
        self.history_pattern = re_compile(r'<.*?>')
        self.date_delta = relativedelta(months=6, days=-1)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        user_name = item['username']

        driver = self.load_page_by_webdriver(self.login_url, '//input[@name="qy_sut"]')
        pid = driver.iedriver.process.pid  # webdriver进程PID
        try:
            butt_submit = driver.find_element_by_name('qy_sut')
            # username = driver.find_element_by_name('alias')
            # username.send_keys(user_name)

            with Ddxoft(pid) as dd_opt:
                driver.execute_script('username_input=document.getElementById("alias");'
                                      'username_input.value="{0}";'
                                      'username_input.focus()'.format(user_name))
                dd_opt.dd_tab()
                sleep(0.5)
                for i in item['password']:
                    dd_opt.dd_keyboard(i)
                    sleep(0.1)

            if driver.find_element_by_id('validatePwd').is_displayed():
                captcha_url = 'https://sbank.hxb.com.cn/easybanking/validateservlet'
                capcha_cookies = get_cookies_dict_from_webdriver(driver)
                capcha_body = get_content_by_requests(captcha_url, headers=self.headers,
                                                      cookie_jar=capcha_cookies)
                captcha_code = self.ask_image_captcha(capcha_body, user_name)
                driver.execute_script('document.getElementById("verifyCode").value="{0}"'.format(captcha_code))
                sleep(0.5)
                if 'validateNoError' in driver.find_element_by_id('valdtErr').get_attribute('src'):
                    yield from self.error_handle(user_name,
                                                 "华夏银行---登录失败：(username:%s, password:%s) %s"
                                                 % (user_name, item["password"], '验证码输入错误'),
                                                 tell_msg='验证码错误')
                    return
            self.element_click_three_times(butt_submit)
            # driver.execute_script(butt_submit.get_attribute('onclick'))
            sleep(2)
            try:
                error_message = driver.find_element_by_id('mess')
                message = error_message.text
                yield from self.error_handle(user_name,
                                             "华夏银行---登录失败：(username:%s, password:%s) %s"
                                             % (user_name, item["password"], message),
                                             tell_msg=message)
                return
            except NoSuchElementException:
                pass

            self.element_click_three_times(driver.find_element_by_class_name('main_nav_1'))
            # my_account_onclick_js = driver.find_element_by_class_name('main_nav_1').get_attribute('onclick')
            # driver.execute_script(my_account_onclick_js)
            sleep(0.5)
            # account_detail_onclick_js = driver.find_element_by_xpath('//a[contains(text(),"账户明细查询")]').get_attribute('onclick')
            # driver.execute_script(account_detail_onclick_js)
            self.element_click_three_times(driver.find_element_by_xpath('//a[contains(text(),"账户明细查询")]'))
            from_day = (date.today() - self.date_delta).strftime("%Y%m%d")
            driver.execute_script('document.getElementsByName("queryStrDateYear")[0].value="%s";'
                                  'document.getElementsByName("queryStrDateMonth")[0].value="%s";'
                                  'document.getElementsByName("queryStrDateDay")[0].value="%s";'
                                  % (from_day[:4], from_day[4:6], from_day[6:8]))

            self.element_click_three_times(driver.find_element_by_id('form_submit'))
            sleep(0.5)
            page_source = driver.page_source
            result = self.__get_page_detail(page_source)
            for i in range(100):
                try:
                    pageDown_btn = driver.find_element_by_xpath('//a[contains(text(),"下一页")]')
                    self.element_click_three_times(pageDown_btn)
                    sleep(1)
                    page_source = driver.page_source
                    result.extend(self.__get_page_detail(page_source))
                except Exception:
                    break
                try:
                    pageDown_btn = driver.find_element_by_xpath('//a[contains(text(),"下一页")]')
                    if pageDown_btn.get_attribute('disabled') == 'disabled':
                        break
                except NoSuchElementException:
                    break

            item['trade_records'] = result

            if 'balance' not in item and result:
                item['balance'] = result[0].get('trade_balance', 0)

            yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(user_name, "华夏银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(user_name, "华夏银行---解析失败", tell_msg="解析失败")
        finally:
            driver.quit()

    def __get_page_detail(self, page_source):
        history_pattern = self.history_pattern
        history_records_table = [history_pattern.split(x)[1] for x in
                                 Selector(text=page_source).xpath('//table[@id="paccountQueryAccount'
                                                                  'DetailsList_row"]/tbody/tr/td').extract()]

        trade_records = []
        titles = ['trade_date', 'trade_accounting_date', 'trade_type', 'trade_currency',
                  'trade_income', 'trade_outcome', 'trade_balance', 'trade_acceptor_account',
                  'trade_acceptor_name', 'trade_acceptor_bank', 'trade_name', 'trade_remark',
                  'trade_amount']
        for records in (history_records_table[i:i + 13] for i in range(0, len(history_records_table), 13)):
            try:
                records[0] = records[1]
                records[12] = records[4] or ("-" + records[5])
                trade_records.append(dict(zip(titles, records)))
            except IndexError:
                continue

        return trade_records
