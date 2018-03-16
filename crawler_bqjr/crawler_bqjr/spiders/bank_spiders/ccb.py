# -*- coding: utf-8 -*-

from datetime import date
from os import remove as os_remove
from os.path import exists as file_exists
from time import sleep

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import NoSuchElementException
from xlrd import open_workbook

from crawler_bqjr.settings import CHROME_DOWNLOAD_DIR
from crawler_bqjr.spider_class import ChromeWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, \
    find_str_range, get_content_by_requests


#################################################
# 建行爬虫
#################################################
class CCBSpider(ChromeWebdriverSpider, BankSpider):
    name = "bank_ccb"
    allowed_domains = ["ccb.com.cn"]
    start_urls = ["https://ibsbjstar.ccb.com.cn/CCBIS/B2CMainPlat_09"
                  "?SERVLET_NAME=B2CMainPlat_09&CCB_IBSVersion=V6"
                  "&PT_STYLE=1&CUSTYPE=0&TXCODE=CLOGIN&DESKTOP=0"
                  "&EXIT_PAGE=login.jsp&WANGZHANGLOGIN=&FORMEPAY=2", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, load_images=False, **kwargs)
        self.headers = {
            "Referer": self._start_url_,
            "Origin": "https://ibsbjstar.ccb.com.cn",
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,en,*"
        }
        self.date_delta = relativedelta(years=1)

    def _download_trade_records(self, driver, start_date_str, end_date_str, mingxi_values):
        filename = "".join([CHROME_DOWNLOAD_DIR, "交易明细_", mingxi_values.split("|", 1)[0][-4:],
                            "_", start_date_str, "_", end_date_str, ".xls"])
        trade_records = []
        try:
            driver.execute_script('document.getElementById("detailDownload").click();'
                                  '$("div#selectDownLoadDiv input[value=3]").click();')

            for i in range(30):
                sleep(1)
                if file_exists(filename):
                    break
            else:
                raise Exception("等待账单文件超时")

            with open_workbook(filename) as bk:
                infos_sheet = bk.sheet_by_index(0)
                for i in range(6, infos_sheet.nrows):
                    trade = {}
                    row_data = infos_sheet.row_values(i)
                    (trade_date, trade_time, trade["trade_location"], trade_outcome, trade_income,
                     trade["trade_balance"], trade["trade_acceptor_account"], trade["trade_acceptor_name"],
                     trade["trade_currency"], trade["trade_remark"]) = row_data[1:11]

                    trade["trade_date"] = trade_date + trade_time
                    trade["trade_amount"] = str(trade_income) if 0 == trade_outcome else ("-" + str(trade_outcome))
                    trade["trade_outcome"] = str(trade_outcome)
                    trade["trade_income"] = str(trade_income)

                    trade_records.append(trade)
        except Exception:
            raise
        finally:
            try:
                os_remove(filename)
            except Exception:
                pass

        return trade_records

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]

        driver = self.load_page_by_webdriver(response.url, "//input[@id='USERID']")
        try:
            # 因为密码控件有javascript加密调用，所以必须用send_keys
            driver.find_element_by_id("LOGPASS").send_keys(item["password"])
            driver.execute_script('document.getElementById("LOGPASS").blur();'
                                  'user_input=document.getElementById("USERID");'
                                  'user_input.focus();'
                                  'user_input.value="' + username + '";')

            # 验证码
            try:
                driver.find_element_by_id("PT_CONFIRM_PWD")
            except NoSuchElementException:
                pass
            else:
                captcha_url = driver.find_element_by_id("fujiama").get_attribute("src")
                cookiejar = get_cookies_dict_from_webdriver(driver)
                capcha_body = get_content_by_requests(captcha_url, headers=self.headers,
                                                      cookie_jar=cookiejar)
                captcha_code = self.ask_image_captcha(capcha_body, username)
                driver.execute_script('document.getElementById("PT_CONFIRM_PWD").value="'
                                      + captcha_code + '";')

            driver.execute_script('document.getElementById("loginButton").click();')
            # =================================登录结束================================= #

            # 点击明细
            iframe_xpath = "//div[@id='w3']/iframe"
            self.wait_xpath(driver, iframe_xpath)
            driver.switch_to.frame(driver.find_element_by_xpath(iframe_xpath))
            self.wait_xpath(driver, "//span[@data_id='mingxi']")

            html = find_str_range(driver.page_source, '<div class="card_list"', "/ul>")
            bs_obj = BeautifulSoup(html, "lxml")
            mingxi_values = bs_obj.find("span", {"data_id": "mingxi"})["values"]

            driver.execute_script("""$("span[values='%s']")[0].click()""" % mingxi_values)
            driver.switch_to.window(driver.window_handles[1])
            driver.switch_to.frame("sear")

            end_date = date.today()
            start_date_str = (end_date - self.date_delta).strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")
            driver.execute_script('document.getElementById("START_DATE").value="%s";'
                                  'document.getElementById("END_DATE").value="%s";'
                                  'toSqOrQd("1");' % (start_date_str, end_date_str))
            self.wait_xpath(driver, "//iframe[@id='result']")

            item["trade_records"] = self._download_trade_records(driver, start_date_str,
                                                                 end_date_str, mingxi_values)

            yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "建设银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "建设银行----爬取异常:",
                                          tell_msg="爬取建设银行账户流水失败")
        finally:
            driver.quit()
