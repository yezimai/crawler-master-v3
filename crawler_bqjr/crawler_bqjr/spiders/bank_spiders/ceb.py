# -*- coding: utf-8 -*-

from time import sleep

from scrapy.http import Request, FormRequest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Ie
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC, ui
from xlrd import open_workbook

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import WebdriverSpider
from crawler_bqjr.spiders.bank_spiders.base import BankSpider


class CebSpider(WebdriverSpider, BankSpider):
    name = "bank_ceb"
    allowed_domains = ["www.cebbank.com"]
    start_urls = ["https://www.cebbank.com/per/prePerlogin.do?_locale=zh_CN", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.account_url = "https://www.cebbank.com/per/FP020216.do?enterPath=1"
        self.trade_url = "https://www.cebbank.com/per/FP020217.do"
        self.balance_url = "https://www.cebbank.com/per/FP020201.do?enterPath=2"
        self.download_url = "https://www.cebbank.com/per/FP020206.do"
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Win64; x64; Trident/4.0; .NET CLR 2.0.50727; SLCC2; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.3; .NET4.0C; .NET4.0E)",
        }

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        driver = Ie(executable_path=self.settings['IE_EXECUTABLE_PATH'])
        pid = driver.iedriver.process.pid
        try:
            wait = ui.WebDriverWait(driver, 20)
            driver.maximize_window()
            driver.get(response.url)

            wait.until(EC.visibility_of_element_located((By.ID, 'skey')))

            # 输入密码，准备模拟键盘输入
            with Ddxoft(pid) as visual_keyboard:
                # 输入用户名
                driver.execute_script('username_input=document.getElementById("skey");'
                                      'username_input.value="%s";'
                                      'username_input.focus();' % username)
                visual_keyboard.dd_tab()
                for i in item['password']:
                    visual_keyboard.dd_keyboard(i)
                    sleep(0.5)
            # 登录
            driver.execute_script('doLogin();')

            # 获取出错信息
            try:
                error_div = wait.until(EC.visibility_of_element_located((By.ID, 'exceptionDiv')))
                msg = error_div.text
                if msg != "":
                    yield from self.error_handle(username, msg, tell_msg=msg)
                    return
            except TimeoutException:
                pass

            # 获取cookie
            cookies = driver.get_cookies()

            # 获取余额信息
            driver.get(self.balance_url)
            query_balance_btn = wait.until(EC.visibility_of_element_located((By.ID, '0key2')))
            balance_script = query_balance_btn.get_attribute("onclick")
            driver.execute_script(balance_script)
            wait.until(EC.visibility_of_element_located((By.XPATH, '//tr[@class="td2"][2]')))
            tr_list = driver.find_elements_by_xpath('//tr[@class="td2"]')
            for tr in tr_list:
                balance_type = tr.find_elements_by_xpath("td[2]")[0].text
                if balance_type == "人民币":
                    item["balance"] = tr.find_elements_by_xpath("td[7]/table/tbody/tr/td/div")[0].text
                    break

            # 进入到明细查询页面
            yield Request(
                url=self.account_url,
                callback=self.parse_account_step1,
                headers=self.headers,
                cookies=cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )

        except Exception:
            yield from self.except_handle(username, "光大银行---登录数据解析异常")
        finally:
            driver.quit()

    def parse_account_step1(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            req_data = {
                "QISHBS": "1",
                "Download": "",  # 下载账单的时候需要这个参数
                "CurrencyTmp": "01",
            }

            for key in ["helpID", "yanID", "CHFlag", "queryflag", "Currency", "AcCur", "AcType",
                        "savekind", "CifName", "BeginDate", "EndDate", "savekind1", "AcNo1", "AcType1",
                        "Currency1", "CHFlag1", "BeginDate1", "EndDate1", "SavingKind1", "CurrencyTmp1",
                        "flag", "_viewReferer", "AcNo3", "SavingKind", "counter", "Bdate1", "Edate1"]:
                req_data[key] = response.xpath('//input[@id="' + key + '"]/@value').extract_first("")

            meta["QISHBS"] = 1
            for acc in response.xpath('//select[@name="AcNo"]/option'):
                tmp_req_data = req_data.copy()
                tmp_req_data["AcNo"] = acc.xpath("@value").extract_first("")

                request = FormRequest(
                    url=self.download_url,
                    callback=self.parse_trade,
                    headers=self.headers,
                    formdata=tmp_req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
                request.meta["req_data"] = tmp_req_data
                yield request
        except Exception:
            yield from self.except_handle(item["username"], "光大银行---账号列表数据解析异常")

    def parse_trade(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]

        try:
            with open_workbook(file_contents=response.body) as data:
                # 读取excel
                table = data.sheet_by_index(0)
                nrows = table.nrows
                for i in range(10, nrows):
                    tr = table.row_values(i)
                    trade_outcome = tr[1]
                    trade_income = tr[2]
                    tmp_dict = {
                        "trade_date": tr[0],
                        "trade_outcome": trade_outcome,
                        "trade_income": trade_income,
                        "trade_balance": tr[3],
                        "trade_channel": tr[4],
                        "trade_acceptor_account": tr[5],
                        "trade_acceptor_name": tr[6],
                        "trade_remark": tr[7],
                        "trade_amount": trade_income or ("-" + trade_outcome),
                    }
                    trade_records.append(tmp_dict)

            # 抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "光大银行---账单数据解析异常")

    """
    分页方式抓取数据
    def parse_trade(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]
        QISHBS = meta["QISHBS"]
        req_data = meta["req_data"]

        try:
            tr_list = response.xpath('//tr[@class="td2"]')
            for tr in tr_list:
                trade_outcome = tr.xpath('td[2]/text()').extract_first("").strip()
                trade_income = tr.xpath('td[3]/text()').extract_first("").strip()
                trade_outcome = trade_outcome if trade_outcome != "--" else ""
                trade_income = trade_income if trade_income != "--" else ""

                tmp_dict = {
                    "trade_date": tr.xpath('td[1]/text()').extract_first("").strip(),
                    "trade_outcome": trade_outcome,
                    "trade_income": trade_income,
                    "trade_balance": tr.xpath('td[4]/text()').extract_first("").strip(),
                    "trade_channel": tr.xpath('td[5]/text()').extract_first("").strip(),
                    "trade_acceptor_account": tr.xpath('td[6]/text()').extract_first("").strip(),
                    "trade_acceptor_name": tr.xpath('td[7]/text()').extract_first("").strip(),
                    "trade_remark": tr.xpath('td[8]/text()').extract_first("").strip(),
                    "trade_amount": trade_income or ("-" + trade_outcome),
                }
                trade_records.append(tmp_dict)

            if not tr_list:
                # 抓取完成
                yield from self.crawling_done(item)
                return

            # 查询下一页
            QISHBS += 10
            meta["QISHBS"] = QISHBS
            req_data["QISHBS"] = str(QISHBS)

            yield FormRequest(
                url=self.trade_url,
                callback=self.parse_trade,
                headers=self.headers,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "光大银行---账号数据解析异常")
    """
