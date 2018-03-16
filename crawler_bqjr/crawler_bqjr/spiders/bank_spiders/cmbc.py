# -*- coding: utf-8 -*-

from datetime import date
from random import random
from re import compile as re_compile
from time import sleep

from dateutil.relativedelta import relativedelta
from selenium.webdriver.support import ui

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import WebBrowserSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, get_content_by_requests


###################################################
# 民生银行爬虫
###################################################
class CMBCSpider(WebBrowserSpider, BankSpider):
    name = "bank_cmbc"
    allowed_domains = ["cmbc.com.cn"]
    start_urls = ["https://nper.cmbc.com.cn/pweb/static/login.html"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Accept": "*/*",
            "Referer": self._start_url_,
            "Host": "nper.cmbc.com.cn",
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729)",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-Hans-CN,zh-Hans;q=0.8,en-US;q=0.5,en;q=0.3"
        }
        self.not_num_pattern = re_compile(r"[^.\d]+")
        self.num_pattern = re_compile(r"[.\d]+")

    def get_theday_3_month_ago(self, now=None):
        return (now or date.today()) - relativedelta(months=+3)

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]

        driver = self.getdriver(executable_path=self.settings["IE_EXECUTABLE_233_PATH"], browser_type="IE")
        pid = driver.iedriver.process.pid
        try:
            wait = ui.WebDriverWait(driver, 20)
            driver.get(response.url)
            wait.until(lambda dr: dr.find_element_by_id("loginButton"))
            driver.maximize_window()

            with Ddxoft(pid) as visual_keyboard:
                driver.execute_script("username_input=document.getElementById('writeUserId');"
                                      "username_input.value='%s';"
                                      "username_input.focus();" % username)
                visual_keyboard.dd_tab()
                sleep(0.1)
                for key in item["password"]:
                    visual_keyboard.dd_keyboard(key)
                    sleep(0.1)

            # 检查是否需要输入验证码
            captcha_input = driver.find_element_by_id("_vTokenName")
            if captcha_input and captcha_input.is_displayed():
                # 验证码
                captcha_url = "https://nper.cmbc.com.cn/pweb/GenTokenImg.do?random=" + str(random())
                capcha_cookies = get_cookies_dict_from_webdriver(driver)
                capcha_body = get_content_by_requests(captcha_url, headers=self.headers,
                                                      cookie_jar=capcha_cookies)
                captcha_code = self.ask_image_captcha(capcha_body, username)
                driver.execute_script("document.getElementById('_vTokenName').value='"
                                      + captcha_code + "';")

            driver.execute_script("document.getElementById('loginButton').click();")
            sleep(2)
            curr_url = driver.current_url
            if 'main.html' not in curr_url:  # 验证是否登录成功
                error = driver.find_element_by_id('jsonError').text
                yield from self.error_handle(username,
                                             msg="民生银行---登录失败：(username:%s, password:%s) %s"
                                                 % (username, item['password'], '账号密码错误'),
                                             tell_msg=error)
                return
            # wait.until(lambda dr: dr.find_element_by_id('welcomeMainContent'))
            wait.until(lambda dr: dr.find_elements_by_xpath("//form[@id='welcomeMainContent']"
                                                            "//a[text()='查询明细']"))
            # balance = driver.find_element_by_xpath('//div[@class="sy_m1_x v-scope"]/div/span').text
            item['balance'] = driver.find_element_by_xpath('//div[@class="sy_m1_x v-scope"]'
                                                           '/div/span[@class="v-binding"]').text
            # 跳转到银行流水界面
            driver.execute_script('document.getElementById("welcomeMainContent")'
                                  '.getElementsByClassName("yuanbj")[2].click()')
            wait.until(lambda dr: dr.find_element_by_id("QuickTitle").is_displayed())
            end_date = date.today()
            trade_records = item["trade_records"]
            for i in range(4):  # 只能在3个月的跨度里查询
                start_date = self.get_theday_3_month_ago(end_date)
                try:
                    wait.until(lambda dr: dr.find_elements_by_xpath("//input[@v-model='BeginDate']"))

                    # 选择开始日期
                    driver.execute_script('$("input[v-model=BeginDate]").focus();')
                    sleep(0.1)
                    driver.execute_script('$("select[data-handler=selectYear]").val("%s");'
                                          '$("select[data-handler=selectYear]").change();'
                                          % start_date.year)
                    sleep(0.1)
                    driver.execute_script('$("select[data-handler=selectMonth]").val("%s");'
                                          '$("select[data-handler=selectMonth]").change();'
                                          % (start_date.month - 1))
                    sleep(0.1)
                    day = start_date.day
                    driver.execute_script('''
                    $("table.ui-datepicker-calendar").find("a:contains(%s)").each(function(){
                        if ($(this).text() == "%s" 
                            && $(this).attr("class").indexOf("ui-priority-secondary") == -1) {
                            this.click();
                        }
                    });''' % (day, day))

                    sleep(1)
                    if 'display: none' in driver.find_element_by_id("jsonErrorShow").get_attribute("style"):
                        wait.until(lambda dr: dr.find_element_by_id("DataTable").is_displayed())
                        # json_data = {"AcNo":"6226220681208897","BankAcType":"03","BeginDate":start_date.strftime("%Y-%m-%d"),"EndDate":end_date.strftime("%Y-%m-%d"),"AcName":u"文学","Remark":"-","Fee":"0.00","FeeRemark":"-","Ten":"Ten","SubAcSeq":"0001","currentIndex":0,"uri":"/pweb/ActTrsQry.do"}
                        # _cookies = get_cookies_dict_from_webdriver(driver)
                        # response = requests.post("https://nper.cmbc.com.cn/pweb/ActTrsQry.do", headers=self.headers,
                        #                          json=json_data, cookies=_cookies, verify=False)
                        # response_text = response.text
                        trade_records.extend(self.parse_item_from_webpage(driver, wait))
                except Exception:
                    self.logger.exception("民生银行---时间筛选")
                end_date = start_date

            yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "民生银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, msg="民生银行---错误信息：",
                                          tell_msg="银行流水数据爬取失败，请刷新页面重试！")
        finally:
            driver.quit()

    #######################################################
    # 从银行流水页面解析出item
    #######################################################
    def parse_item_from_webpage(self, driver, wait):
        trade_detail = []
        data_list = driver.find_elements_by_xpath("//table[@id='DataTable']/tbody/tr")
        if data_list:
            not_num_pattern = self.not_num_pattern
            num_pattern = self.num_pattern
            for data_item in data_list:
                temp_item = {}
                data_block_1 = data_item.find_element_by_xpath("td[1]").text.split()
                temp_item["trade_date"] = data_block_1[0]  # 交易日期
                temp_item["trade_name"] = data_block_1[1]  # 交易名称
                data_block_2 = data_item.find_element_by_xpath("td[3]").text
                if data_block_2:
                    trade_type = not_num_pattern.search(data_block_2).group(0)  # 交易类型
                    temp_item["trade_type"] = trade_type.strip()
                    trade_amount = num_pattern.search(data_block_2).group(0)  # 交易金额
                    trade_income = trade_amount if "转入" in trade_type else 0
                    temp_item["trade_income"] = trade_income  # 收入
                    temp_item["trade_amount"] = trade_amount
                data_block_3 = data_item.find_element_by_xpath("td[4]").text
                if data_block_3:
                    trade_type = not_num_pattern.search(data_block_3).group(0)  # 交易类型
                    temp_item["trade_type"] = trade_type.strip()
                    trade_amount = num_pattern.search(data_block_3).group(0)  # 交易金额
                    trade_outcome = trade_amount if "转出" in trade_type else 0
                    temp_item["trade_outcome"] = trade_outcome  # 支出
                    temp_item["trade_amount"] = "-" + trade_amount
                trade_balance = data_item.find_element_by_xpath("td[5]").text  # 余额
                temp_item["trade_balance"] = trade_balance
                trade_channel = data_item.find_element_by_xpath("td[6]").text  # 交易渠道
                temp_item["trade_channel"] = trade_channel
                trade_acceptor_name = data_item.find_element_by_xpath("td[7]").text  # 对方信息
                temp_item["trade_acceptor_name"] = trade_acceptor_name
                trade_detail.append(temp_item)

        return trade_detail
