# -*- coding: utf-8 -*-

from datetime import date
from time import sleep

from dateutil.relativedelta import relativedelta
from scrapy import Selector
from selenium.common.exceptions import NoSuchElementException

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import IE233WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes


class BocomSpider(IE233WebdriverSpider, BankSpider):
    name = "bank_bocom"
    allowed_domains = ['95595.com']
    start_urls = ["https://pbank.95559.com.cn/personbank/logon.jsp", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.date_delta = relativedelta(years=1)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        user_name = item['username']

        driver = self.load_page_by_webdriver(response.url)
        try:
            driver.maximize_window()
            # username_input = driver.find_element_by_id('alias')
            # username_input.send_keys(user_name)

            pid = driver.iedriver.process.pid
            with Ddxoft(pid) as dd_opt:
                driver.execute_script('document.getElementById("alias").value="{0}";'
                                      'document.getElementById("alias").focus()'.format(user_name))
                sleep(0.5)
                dd_opt.dd_tab()
                sleep(0.5)
                for i in item['password']:
                    dd_opt.dd_keyboard(i)

            try:
                captcha_img = driver.find_element_by_class_name('captchas-img-bg')
                input_captcha = driver.find_element_by_id('input_captcha')
                if captcha_img.is_displayed():
                    photo_base64 = driver.get_screenshot_as_base64()

                    left = captcha_img.location['x'] - 8
                    top = captcha_img.location['y']
                    right = captcha_img.location['x'] + captcha_img.size['width'] - 8
                    bottom = captcha_img.location['y'] + captcha_img.size['height']

                    captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                    captcha_code = self.ask_image_captcha(captcha_body, user_name, file_type=".png")

                    # driver.execute_script('document.getElementById("input_captcha").value="{0}";'
                    #                      .format(captcha_code))
                    input_captcha.send_keys(captcha_code)
            except NoSuchElementException:
                pass

            butt_submit = driver.find_element_by_id('login')
            self.element_click_three_times(butt_submit)
            sleep(3)
            try:
                driver.find_element_by_id('login')
                yield from self.error_handle(user_name,
                                             "交通银行---登录失败：(username:%s, password:%s) %s"
                                             % (user_name, item["password"], '账号、密码错误或模拟键盘操作失败,返回登录页面'),
                                             tell_msg="账号、密码错误或模拟键盘操作失败")
                return
            except NoSuchElementException:
                pass

            try:
                # 有可能没有验证手机
                sleep(1)
                btnSendCode = driver.find_element_by_id('authSMSSendBtn')
                self.element_click_three_times(btnSendCode)
                sms_code = self.ask_sms_captcha(user_name)
                sms_code_input = driver.find_element_by_id('mobileCode')
                sms_code_input.send_keys(sms_code)
                sleep(0.5)
                submit = driver.find_element_by_id('btnConf2')
                self.element_click_three_times(submit)
                sleep(1)
            except NoSuchElementException:
                pass

            # 提交设置为常用电脑
            try:
                self.element_click_three_times(driver.find_element_by_xpath('//input[@checked="checked"]'))
                self.element_click_three_times(driver.find_element_by_id('next'))
                sleep(0.5)
            except NoSuchElementException:
                pass

            self.wait_xpath(driver, '//iframe[@id="frameMain"]')
            driver.switch_to.frame('frameMain')
            driver.execute_script('document.getElementById("search").value="账户明细查询";')

            # driver.find_element_by_id('search').send_keys('账户明细查询')
            self.element_click_three_times(driver.find_element_by_class_name('search_btn'))
            self.wait_xpath(driver, '//iframe[@id="tranArea"]')

            frame = driver.find_element_by_id('tranArea')
            # 转到 主工作区 iframe 里面
            driver.switch_to.frame(frame)
            #  搜索框中的交易明细查询 menucode为P002000
            if driver.find_elements_by_xpath('//td[@menucode="P002000"]/a'):
                self.element_click_three_times(driver.find_element_by_xpath('//td[@menucode="P002000"]/a'))
                sleep(1)
                fromday = (date.today() - self.date_delta).strftime("%Y%m%d")
                driver.execute_script('$("#startDate").datepicker("setDate","{0}");'.format(fromday))
                submit_date = driver.find_element_by_id('btnQry2')
                self.element_click_three_times(submit_date)
                sleep(0.5)
                self.wait_xpath(driver, '//tbody[@id="recordtbody"]')
                page_source = driver.page_source
                result = self.__get_page_detail(page_source)
                for i in range(100):
                    try:
                        pageDown_btn = driver.find_element_by_id('pageDown')
                    except NoSuchElementException:
                        break
                    if pageDown_btn.is_displayed():
                        self.element_click_three_times(pageDown_btn)
                        sleep(1)
                        page_source = driver.page_source
                        result.extend(self.__get_page_detail(page_source))
                    else:
                        break

                item['trade_records'] = result
                yield from self.crawling_done(item)
            else:
                yield from self.error_handle(user_name, "交通银行---未搜索到交易明细",
                                             tell_msg="信息获取异常")
        except CaptchaTimeout:
            yield from self.error_handle(user_name, "交通银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(user_name, "交通银行---解析失败", tell_msg="解析失败")
            return
        finally:
            driver.quit()

    def __get_page_detail(self, page_source):
        selector = Selector(text=page_source)
        outcome_income_list = selector.xpath('//tbody[@id="recordtbody"]/tr/td/font/text()').extract()
        history_records_table = selector.xpath('//tbody[@id="recordtbody"]/tr/td/text()').extract()
        outcome_income_split = 2
        history_records_split = 7

        trade_records = []
        titles = ['trade_date', 'trade_type', 'trade_currency', 'trade_location',
                  'trade_outcome', 'trade_income', 'trade_balance', 'trade_amount']
        for remain, outcome_income, record in zip(selector.xpath('//tbody[@id="recordtbody"]'
                                                                 '/tr/td/div/text()').extract(),
                                                  (outcome_income_list[i:i + outcome_income_split] for i in
                                                   range(0, len(outcome_income_list), outcome_income_split)),
                                                  (history_records_table[i:i + history_records_split] for i in
                                                   range(0, len(history_records_table), history_records_split))):
            trade_time_format = record[0].replace('　', '')
            temp_record = [trade_time_format, record[1], record[2], record[4]]
            temp_record.extend(j.replace('-', '').strip() for j in outcome_income)
            temp_record.append(remain)
            temp_record.append(temp_record[5] or ("-" + temp_record[4]))

            trade_records.append(dict(zip(titles, temp_record)))

        return trade_records
