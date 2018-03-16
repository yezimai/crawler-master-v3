# -*- coding: utf-8 -*-

from datetime import date
from time import sleep
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from scrapy.http import Request
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Ie
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC, ui
from xlrd import open_workbook

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes


class SpdbSpider(WebdriverSpider, BankSpider):
    name = "bank_spdb"
    allowed_domains = ["ebank.spdb.com.cn"]
    start_urls = ["https://ebank.spdb.com.cn/nbper/prelogin.do", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prequeryhistory_url = "https://ebank.spdb.com.cn/nbper/PreQueryHistory.do?_viewReferer=default,account/QueryHistory&selectedMenu=menu2_1_10"
        self.queryhistory_url = "https://ebank.spdb.com.cn/nbper/QueryHistory.do"
        self.balance_url = "https://ebank.spdb.com.cn/nbper/PreQueryBalance.do?_viewReferer=default,account/QueryBalance&selectedMenu=menu2_1_9"
        self.download_url = "https://ebank.spdb.com.cn/nbper/DownloadHistory.do"
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Win64; x64; Trident/4.0; .NET CLR 2.0.50727; SLCC2; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E)",
        }
        self.date_delta = relativedelta(years=2)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        driver = Ie(executable_path=self.settings['IE_EXECUTABLE_PATH'])
        pid = driver.iedriver.process.pid
        try:
            # driver = self.getdriver(executable_path=self.settings["CHROME_EXECUTABLE_PATH"], browser_type="CHROME",
            #                         use_proxy=False, change_proxy=False)
            wait_60 = ui.WebDriverWait(driver, 60)
            wait = ui.WebDriverWait(driver, 20)
            driver.maximize_window()
            driver.get(response.url)
            for i in range(10):
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                    sleep(1)
                except Exception:
                    break
            wait_60.until(EC.visibility_of_element_located((By.NAME, 'login-iframe')))

            # 点击密码输入框
            # driver.execute_script("inputPwd();")

            # sleep(3)
            # driver.execute_script("var obj_pwd=document.getElementById('password');"
            #                       "obj_pwd.readOnly=false;"
            #                       "obj_pwd.value='" + item["password"] + "';")
            # driver.execute_script("var obj_pwd2=document.getElementById('Password');"
            #                       "obj_pwd2.value='" + item["password"] + "';")

            # 输入密码
            # pwd_input = wait.until(EC.visibility_of_element_located((By.ID, 'OPassword')))
            # pwd_input.send_keys(item["password"])

            # 停顿2秒 准备模拟键盘输入
            with Ddxoft(pid) as dd_opt:
                # 输入用户名
                driver.execute_script('login_iframe=document.getElementsByName("login-iframe")[0].contentDocument;'
                                      'username_input=login_iframe.getElementById("LoginId");'
                                      'username_input.focus();'
                                      'username_input.value="' + username + '";')

                # 切换到登录的框架
                driver.switch_to.frame("login-iframe")
                dd_opt.dd_tab()
                for i in item['password']:
                    dd_opt.dd_keyboard(i)
                    sleep(0.5)

            # 如果出现验证码
            try:
                # 输入验证码
                validation_img = wait.until(EC.visibility_of_element_located((By.ID, 'tokenImg')))
                left = validation_img.location['x']
                top = validation_img.location['y']
                right = validation_img.location['x'] + validation_img.size['width']
                bottom = validation_img.location['y'] + validation_img.size['height']

                photo_base64 = driver.get_screenshot_as_base64()
                img_bytes = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                captcha_code = self.ask_image_captcha(img_bytes, username, file_type=".png")

                token_input = wait.until(EC.visibility_of_element_located((By.ID, 'verCodeToken')))
                token_input.send_keys(captcha_code)
            except CaptchaTimeout:
                raise
            except Exception:
                pass

            # 点击登录
            login_btn = wait.until(EC.visibility_of_element_located((By.ID, 'LoginButton')))
            # login_btn.click()
            driver.execute_script("Javascript: return doSubmit()")

            # 获取出错信息
            try:
                error_div = wait.until(EC.visibility_of_element_located((By.ID, 'errInfo')))
                msg = error_div.text
                if msg != "":
                    yield from self.error_handle(username, msg, tell_msg=msg)
                    return
            except TimeoutException:
                pass

            # 获取cookie
            cookies = driver.get_cookies()

            # 获取余额所在的页面
            driver.get(self.balance_url)
            balance_div = wait.until(EC.visibility_of_element_located((By.XPATH,
                                                                       '//td[@id="CanUseBalanceShow_0"]/div')))
            item["balance"] = balance_div.text.strip()

            # 进入到明细查询页面
            yield Request(
                url=self.prequeryhistory_url,
                callback=self.parse_prequeryhistory,
                headers=self.headers,
                cookies=cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except CaptchaTimeout:
            yield from self.error_handle(username, "浦发银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "浦发银行---登录数据解析异常")
        finally:
            driver.quit()

    def parse_prequeryhistory(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            # 获取账户明细
            req_data = {
                "AcctKind": response.xpath('//input[@name="AcctKind"]/@value').extract_first(""),
                "CurrencyNo": "01",
                "CurrencyType": response.xpath('//input[@name="CurrencyType"]/@value').extract_first(""),
                "BeginDate": (date.today() - self.date_delta).strftime('%Y%m%d'),
                "EndDate": response.xpath('//input[@name="EndDate"]/@value').extract_first(""),
            }

            for acc in response.xpath('//select[@name="AcctNo"]/option'):
                req_data["AcctNo"] = acc.xpath("@value").extract_first("")
                yield Request(
                    url=self.download_url + "?" + urlencode(req_data),
                    callback=self.parse_queryhistory,
                    headers=self.headers,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "浦发银行---账号信息解析异常")

    def parse_queryhistory(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]

        try:
            with open_workbook(file_contents=response.body) as data:
                # 读取excel
                table = data.sheet_by_index(0)
                nrows = table.nrows
                for i in range(2, nrows):
                    tr = table.row_values(i)
                    trade_income = tr[3]
                    trade_outcome = tr[4]
                    tmp_dict = {
                        "trade_date": tr[1].split(" ", 1)[0],
                        "trade_remark": tr[2],
                        "trade_income": trade_income,
                        "trade_outcome": trade_outcome,
                        "trade_balance": tr[5],
                        "trade_amount": (trade_income or ("-" + trade_outcome)),
                    }
                    trade_records.append(tmp_dict)

            # 抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "浦发银行---账单解析异常")

    """
   def parse_prequeryhistory(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            # 获取账户明细
            req_data = {
                "CurrencyNo": "01",
                "LoanType": "000000",
                "LoanStatus": "2",
                "BeginDate": (date.today() - self.date_delta).strftime('%Y%m%d'),
                "BeginNumber": "0",
                "QueryNumber": "20"
            }
            
            for key in ["_viewReferer", "selectedMenu", "selectedSubMenu", "ClickMenu", "SelectFlag",
                        "AcctNoFlag", "BeginDate1", "EndDate1", "QueryTrsType", "AcctKind", "InputType",
                        "InputType1", "FastSelect", "HuoqiShow", "TouzhiShow", "ZhiyekaShow",
                         "ZhipiaoShow", "CurrencyType", "EndDate"]:
                req_data[key] = response.xpath('//input[@name="' + key + '"]/@value').extract_first("")

            meta["trade_records"] = []
            meta["BeginNumber"] = 0

            headers = self.headers.copy()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            for acc in AcctNo:
                tmp_req_data = req_data.copy()
                tmp_req_data["AcctNo"] = acc.xpath("@value").extract_first("")
                request = FormRequest(
                    url=self.queryhistory_url,
                    callback=self.parse_queryhistory,
                    headers=headers,
                    formdata=tmp_req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
                request.meta["req_data"] = tmp_req_data
        except Exception:
            yield from self.except_handle(item["username"], "浦发银行---账号信息解析异常")

    def parse_queryhistory(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]
        req_data = meta["req_data"]
        begin_number = meta["BeginNumber"]

        try:
            tr_list = response.xpath('//table[@class="table"]/tr')
            for tr in islice(tr_list, 2, None):
                pass_entry_date = tr.xpath('td[2]/text()').extract_first("")
                income = tr.xpath('td[4]/text()').extract_first("").strip()
                outcome = tr.xpath('td[5]/text()').extract_first("").strip()
                tmp_dict = {
                    "trade_date": pass_entry_date.strip().split("\r\n", 1)[0].strip(),
                    "trade_remark": tr.xpath('td[3]/text()').extract_first("").strip(),
                    "trade_income": income,
                    "trade_outcome": outcome,
                    "trade_balance": tr.xpath('td[6]/text()').extract_first("").strip(),
                    "trade_amount": (income or ("-" + outcome)),
                }
                trade_records.append(tmp_dict)

            if not tr_list:
                # 抓取完成
                yield from self.crawling_done(item)
                return

            # 查询下一页
            begin_number += 20
            meta["BeginNumber"] = begin_number
            req_data["BeginNumber"] = str(begin_number)

            yield FormRequest(
                url=self.queryhistory_url,
                callback=self.parse_queryhistory,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )

    except Exception:
        yield from self.except_handle(item["username"], "浦发银行---交易明细数据解析异常")
    """
