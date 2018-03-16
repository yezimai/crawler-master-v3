# -*- coding: utf-8 -*-

from datetime import date, timedelta
from re import compile as re_compile, S as re_S
from time import sleep

from scrapy.http import Request, FormRequest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Ie
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC, ui
from xlrd import open_workbook

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes


class PsbcSpider(WebdriverSpider, BankSpider):
    name = "bank_psbc"
    allowed_domains = ["pbank.psbc.com"]
    start_urls = ["https://pbank.psbc.com/pweb/prelogin.do?_locale=zh_CN&BankId=9999", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_url = "https://pbank.psbc.com/pweb/ActListQry.do"
        self.acttrsqrypre_url = "https://pbank.psbc.com/pweb/ActTrsQryPre.do"
        self.acttrsinfoqry_url = "https://pbank.psbc.com/pweb/ActTrsInfoQry.do"
        self.acttrsinfodownLoad_url = "https://pbank.psbc.com/pweb/ActTrsInfoDownLoad.do"
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Win64; x64; Trident/4.0; .NET CLR 2.0.50727; SLCC2; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E)",
        }
        self.pattern = re_compile(r"ToSavDes\('(.*?)','(.*?)'\)", re_S)
        self.date_delta = timedelta(days=180)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        driver = Ie(executable_path=self.settings['IE_EXECUTABLE_PATH'])
        pid = driver.iedriver.process.pid
        try:
            driver.maximize_window()
            wait = ui.WebDriverWait(driver, 20)
            driver.get(response.url)

            username = wait.until(EC.visibility_of_element_located((By.ID, 'textfield')))
            username.send_keys(username)
            # 停顿2秒 准备模拟键盘输入
            with Ddxoft(pid) as visual_keyboard:
                visual_keyboard.dd_tab()
                visual_keyboard.dd_tab()
                for i in item['password']:
                    visual_keyboard.dd_keyboard(i)
                    sleep(0.5)

            # 输入验证码
            validation_img = wait.until(EC.visibility_of_element_located((By.ID, '_tokenImg')))
            left = validation_img.location['x']
            top = validation_img.location['y']
            right = validation_img.location['x'] + validation_img.size['width']
            bottom = validation_img.location['y'] + validation_img.size['height']

            photo_base64 = driver.get_screenshot_as_base64()
            img_bytes = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
            captcha_code = self.ask_image_captcha(img_bytes, username, file_type=".png")

            token_input = wait.until(EC.visibility_of_element_located((By.ID, '_vTokenName')))
            token_input.send_keys(captcha_code)

            button = driver.find_element_by_id('button')
            button.click()

            # 判断是否登录成功
            try:
                error_info = wait.until(EC.visibility_of_element_located((By.ID, 'EEE')))
                msg = error_info.text
                if msg != "":
                    yield from self.error_handle(username, msg, tell_msg=msg)
                    return
            except TimeoutException:
                pass

            cookies = driver.get_cookies()

            yield Request(
                url=self.account_url,
                callback=self.parse_act_list,
                headers=self.headers,
                cookies=cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except CaptchaTimeout:
            yield from self.error_handle(username, "邮政银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "邮政银行---登录数据解析异常")
        finally:
            driver.quit()

    def parse_act_list(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            act_list = response.xpath('//table[@id="cardLists"]/tr[@class="trValue"]')
            regex = self.pattern
            for act in act_list:
                act_info = act.xpath('td[8]/a/@onclick').extract_first("")
                card_no, card_type = regex.search(act_info).groups()
                acttrsqrypre_url = (self.acttrsqrypre_url + "?AcNo=" + card_no
                                    + "&AcType=" + card_type + "&PrePage=list")
                item["balance"] = act.xpath('td[7]/div/text()').extract_first("").strip()

                yield Request(
                    url=acttrsqrypre_url,
                    callback=self.parse_acttrsqrypre,
                    headers=self.headers,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "邮政银行---获取邮政银行列表数据解析异常")

    def parse_acttrsqrypre(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            req_data = {
                "BeginDate": (date.today() - self.date_delta).strftime('%Y-%m-%d'),
                "ChannelId": "",
                "queryButton": "交易明细查询",
                "currentIndex": "0",
                "recordNumber": "0"
            }

            for key in ["_viewReferer", "qryType", "AcNo", "BankAcType", "SubAcSeq", "SeqNoKey",
                        "Currency", "CRFlag", "DeptId", "AcType", "PrePage", "Download", "EndDate"]:
                req_data[key] = response.xpath('//input[@id="' + key + '"]/@value').extract_first("")

            meta["req_data"] = req_data

            yield FormRequest(
                url=self.acttrsinfoqry_url,
                callback=self.parse_acttrsinfoqry,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "邮政银行---请求交易明细数据解析异常")

    def parse_acttrsinfoqry(self, response):
        """
        采用下载账单方式
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        req_data = meta["req_data"]

        try:
            req_data["currentIndex"] = response.xpath('//input[@name="currentIndex"]/@value').extract_first("")
            req_data["recordNumber"] = response.xpath('//input[@name="recordNumber"]/@value').extract_first("")
            yield FormRequest(
                url=self.acttrsinfodownLoad_url,
                callback=self.parse_acttrsinfodownLoad,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "邮政银行---解析交易明细数据解析异常")

    def parse_acttrsinfodownLoad(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = []

        try:
            with open_workbook(file_contents=response.body) as data:
                # 读取excel
                table = data.sheet_by_index(0)
                nrows = table.nrows
                for i in range(5, nrows):
                    tr = table.row_values(i)
                    tmp_dict = {
                        "trade_date": tr[1],
                        "trade_remark": tr[2],
                        "trade_amount": tr[3],
                        "trade_balance": tr[4]
                    }
                    trade_records.append(tmp_dict)

            last_balance = 0
            trade_records_temp = []
            for trade in reversed(trade_records):
                # 余额增加，说明是入账,反之则是出账
                this_balance = float(trade["trade_balance"])
                if last_balance < this_balance:
                    trade["trade_income"] = trade["trade_amount"]
                else:
                    trade_amount = trade["trade_amount"]
                    trade["trade_outcome"] = trade_amount
                    trade["trade_amount"] = "-" + trade_amount
                last_balance = this_balance
                trade_records_temp.append(trade)

            trade_records_temp.reverse()
            item["trade_records"] = trade_records_temp[:-1]

            # 抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "邮政银行---下载交易明细账单出错")

    """
    def parse_acttrsinfoqry(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]
        req_data = meta["req_data"]

        try:
            tr_list = response.xpath('//tr[@class="trValue"]')
            for tr in tr_list:
                tmp_dict = {
                    "trade_date": tr.xpath('td[2]/text()').extract_first("").strip(),
                    "trade_remark": tr.xpath('td[3]/text()').extract_first("").strip(),
                    "trade_amount": tr.xpath('td[4]/text()').extract_first("").strip(),
                    "trade_balance": tr.xpath('td[5]/text()').extract_first("").strip()
                }
                trade_records.append(tmp_dict)

            currentIndex = response.xpath('//input[@name="currentIndex"]/@value').extract_first()
            recordNumber = response.xpath('//input[@name="recordNumber"]/@value').extract_first()
            currentIndex = int(currentIndex)
            recordNumber = int(recordNumber)

            if currentIndex * 10 < recordNumber:
                req_data["currentIndex"] = str(currentIndex + 10)
                req_data["recordNumber"] = str(recordNumber)
                yield FormRequest(
                    url=self.acttrsinfoqry_url,
                    callback=self.parse_acttrsinfoqry,
                    headers=self.headers,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                last_balance = 0
                trade_records_temp = []
                for trade in reversed(trade_records):
                    # 余额增加，说明是入账,反之则是出账
                    this_balance = float(trade["trade_balance"])
                    if last_balance < this_balance:
                        trade["trade_income"] = trade["trade_amount"]
                    else:
                        trade_amount = trade["trade_amount"]
                        trade["trade_outcome"] = trade_amount
                        trade["trade_amount"] = "-" + trade_amount
                    last_balance = this_balance
                    trade_records_temp.append(trade)
                    
                trade_records_temp.reverse()
                item["trade_records"] = trade_records_temp[:-1]
                # 抓取完成
                yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "邮政银行---解析交易明细数据解析异常")
    """
