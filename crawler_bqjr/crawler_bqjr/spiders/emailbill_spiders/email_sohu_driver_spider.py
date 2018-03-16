# -*- coding:utf-8 -*-

from re import compile as re_compile
from time import sleep

from crawler_bqjr.spiders.emailbill_spiders.email_sohu_scrapy_spider import EmailSohuSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import check_email_credit_card_by_address
from crawler_bqjr.utils import driver_screenshot_2_bytes, get_js_time
from global_utils import json_loads


class EmailSohuDriverSpider(EmailSohuSpider):
    start_urls = ['https://mail.sohu.com/fe/#/login', ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.detail_pattern = re_compile(r'"display":"(.*?)","sendDate"')
        self.mail_list_pattern = re_compile(r'<body>(\{.+?\})</')

    def _get_bill_records(self, driver, mail_list):
        detail_pattern = self.detail_pattern
        get_bill_record = self.get_bill_record
        bill_records = []
        for it in mail_list:
            subject = it['subject']
            bankname = check_email_credit_card_by_address(subject, it["from"])
            if bankname:
                driver.get('https://mail.sohu.com/fe/getMail'
                           '?id=%s&t=%s' % (it['id'], get_js_time()))
                sleep(0.2)
                detail = detail_pattern.search(driver.page_source).group(1)
                bill_record = get_bill_record(bankname, subject, detail)
                bill_records.append(bill_record)

        return bill_records

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        username = item["username"]

        driver = self.load_page_by_webdriver(self._start_url_)
        sleep(0.5)
        try:
            try:
                driver.execute_script("""$('input[ng-model="account"]').val('%s');
                $('input[ng-model="account"]').change();""" % username)
                sleep(0.2)
                driver.execute_script("""$('input[ng-model="pwd"]').val('%s');
                $('input[ng-model="pwd"]').change();""" % item["password"])
                sleep(0.2)
                driver.execute_script("document.getElementsByClassName('btn-login fontFamily')[0].click();")
                sleep(2)

                if driver.current_url == self._start_url_:
                    captcha_image = driver.find_element_by_xpath('//div[@ng-show="needCaptcha"]/img')
                    location = captcha_image.location
                    size = captcha_image.size
                    left = location["x"] - 8
                    top = location["y"]
                    right = left + size["width"]
                    bottom = top + size["height"]

                    photo_base64 = driver.get_screenshot_as_base64()
                    captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                    captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".png")
                    driver.execute_script("""$('input[ng-model="captcha"]').val('%s');
                    $('input[ng-model="captcha"]').change();""" % captcha_code)
                    driver.execute_script("document.getElementsByClassName('btn-login fontFamily')[0].click()")
                # 登录成功之后 直接访问json页面, 提取对应数据进行筛选
                # sleep(0.5)
            except TypeError:
                pass
            except AttributeError:
                # 跳转页面会出现异常,这个异常可忽略.
                pass

            driver.get(self.search_url % (0, get_js_time(), self.keyword))
            result_str = self.mail_list_pattern.search(driver.page_source).group(1)
            result = json_loads(result_str)
            if result['msg'] != '登录超时，请重新登录':
                bill_records = item["bill_records"]
                the_data = result['data']
                bill_records.extend(self._get_bill_records(driver, the_data['list']))

                page_step = self.page_step
                page = (the_data['total'] + page_step - 1) // page_step
                for pa in range(1, page):  # 过滤掉第一页
                    driver.get(self.search_url % (pa * page_step, get_js_time(), self.keyword))
                    result_str = self.mail_list_pattern.search(driver.page_source).group(1)
                    bill_records.extend(self._get_bill_records(driver, json_loads(result_str)['data']['list']))

                yield from self.crawling_done(item)
            else:
                yield from self.error_handle(username, "搜狐邮箱---等待验证码超时",
                                             tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "搜狐邮箱---抓取异常",
                                          tell_msg="请刷新页面重试。。")
        finally:
            driver.quit()
