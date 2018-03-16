# -*- coding: utf-8 -*-

from datetime import date, timedelta
from time import sleep

from scrapy.http import Request
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC, ui

from crawler_bqjr.spider_class import WebBrowserSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes


class BocSpider(WebBrowserSpider, BankSpider):
    name = "bank_boc"
    allowed_domains = ["mbs.boc.cn"]
    start_urls = ["https://ebsnew.boc.cn/boc15/login.html", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PsnGetUserProfile_url = "https://ebsnew.boc.cn/BII/PsnGetUserProfile.do?_locale=zh_CN"
        self.download_url = "https://ebsnew.boc.cn/BII/PsnAccountTransferDetailDownload.do"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3166.0 Safari/537.36",
            "Content-Type": "text/json;",
            "Origin": "https://ebsnew.boc.cn",
            "Referer": "https://ebsnew.boc.cn/boc15/welcome_ele.html?v=20170718030500330&locale=zh&login=card&segment=1",
            "X-Requested-With": "XMLHttpRequest"
        }

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        driver = self.getdriver(executable_path=self.settings["CHROME_EXECUTABLE_PATH"],
                                browser_type="CHROME_HEADLESS")
        try:
            wait = ui.WebDriverWait(driver, 10)
            driver.get(response.url)

            # 输入用户名
            username_input = wait.until(EC.visibility_of_element_located((By.ID, 'txt_username_79443')))
            username_input.send_keys(username)
            username_input.send_keys(Keys.TAB)

            # 输入密码
            try:
                pwd_input = wait.until(EC.visibility_of_element_located((By.ID, 'input_div_password_79445_1')))
            except TimeoutException:
                pwd_input = wait.until(EC.visibility_of_element_located((By.ID, 'input_div_password_79445')))
            pwd_input.send_keys(item["password"])
            self.click_hidemsgbox(wait)

            # 输入验证码
            try:
                try:
                    validation_img = wait.until(EC.visibility_of_element_located((By.ID, 'captcha_debitCard')))
                except TimeoutException:
                    validation_img = wait.until(EC.visibility_of_element_located((By.ID, 'captcha')))
                left = validation_img.location['x']
                top = validation_img.location['y']
                right = validation_img.location['x'] + validation_img.size['width']
                bottom = validation_img.location['y'] + validation_img.size['height']

                photo_base64 = driver.get_screenshot_as_base64()
                img_bytes = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                captcha_code = self.ask_image_captcha(img_bytes, username, file_type=".png")

                self.click_hidemsgbox(wait)
                try:
                    validation_input = wait.until(EC.visibility_of_element_located((By.ID, 'txt_captcha_741012')))
                except TimeoutException:
                    validation_input = wait.until(EC.visibility_of_element_located((By.ID, 'txt_captcha_79449')))
                validation_input.send_keys(captcha_code)
                self.click_hidemsgbox(wait)
            except Exception:
                pass

            # 点击登录
            try:
                submit_input = wait.until(EC.visibility_of_element_located((By.ID, 'btn_49_741014')))
            except TimeoutException:
                submit_input = wait.until(EC.visibility_of_element_located((By.ID, 'btn_login_79676')))
            submit_input.click()
            # 判断是否登录成功
            try:
                error_info = wait.until(EC.visibility_of_element_located((By.ID, 'msgContent')))
                msg = error_info.text
                if msg != "":
                    yield from self.error_handle(username, msg, tell_msg=msg)
                    return
            except TimeoutException:
                pass
            if username.isdigit() and len(username) == 19:
                # 使用webdriver的方式
                # 查询余额
                balance_td = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="cardMain"]/div/div[2]'
                                                                                    '/table/tbody/tr/td[4]')))
                item["balance"] = balance_td.text.strip()
                # 选择查询交易明细
                trade_detail = wait.until(EC.visibility_of_element_located((By.ID, 'div_transaction_details_740993')))
                trade_detail.click()
                # 选择日期
                start_date = wait.until(EC.visibility_of_element_located((By.ID, 'date_start_date_740972')))
                begin_date = (date.today() - timedelta(days=180)).strftime('%Y/%m/%d')
                start_date.clear()
                start_date.send_keys(begin_date)
                # 点击空白
                null_click = wait.until(EC.visibility_of_element_located((By.ID, 'sel_pleaseselectaccount_740896')))
                null_click.click()

                # 点击查询按钮
                query_input = wait.until(EC.visibility_of_element_located((By.ID, 'btn_49_740974')))
                query_input.click()
                trade_records = item["trade_records"]
                # 获取总页码
                page_count_em = driver.find_element_by_xpath('//*[@id="pager"]/ul/li[2]/em[2]')
                page_count = int(page_count_em.text)
                next_count = 0
                while next_count < page_count:
                    # 滚到顶部
                    driver.execute_script("window.scrollTo(0,0)")
                    wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="debitCardTransDetail_table"]'
                                                                           '/table/tbody/tr')))
                    tr_list = driver.find_elements_by_xpath('//*[@id="debitCardTransDetail_table"]/table/tbody/tr')
                    for tr in tr_list:
                        td = tr.find_elements_by_xpath("td")
                        trade_income = td[6].text
                        trade_outcome = td[7].text
                        tmp_dict = {
                            "trade_date": td[0].text,
                            "trade_remark": td[1].text,
                            "trade_acceptor_account": td[2].text,
                            "trade_acceptor_name": td[3].text,
                            "trade_currency": td[4].text,
                            "trade_income": trade_income,
                            "trade_outcome": trade_outcome,
                            "trade_amount": trade_income or ("-" + trade_outcome),
                            "trade_balance": td[8].text,
                            "trade_channel": td[9].text,  # 交易渠道
                        }
                        trade_records.append(tmp_dict)

                    next_count += 1

                    # 滚到页面底部才有下一页按钮
                    driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
                    next_pager = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'next')))
                    next_pager.click()
                    sleep(1)

                driver.execute_script("window.scrollTo(0,0)")
                # 退出网银
                pager_quit = wait.until(EC.visibility_of_element_located((By.ID, 'a_59_1168')))
                pager_quit.click()

                # 抓取完成
                yield from self.crawling_done(item)
            else:
                cookies = driver.get_cookies()
                # 点击银行账户链接
                my_account = wait.until(EC.visibility_of_element_located((By.XPATH, '//a[@key="MyAccount"]')))
                my_account.click()
                my_balance = wait.until(EC.visibility_of_element_located((By.XPATH, '//a[@title="余额"]')))
                # 获取accountid
                accountid = my_balance.get_attribute('accountid')
                my_balance.click()
                # 获取余额
                item["balance"] = wait.until(EC.visibility_of_element_located((By.XPATH, '//td[@lan="num"]'))).text
                begin_date = (date.today() - timedelta(days=180)).strftime('%Y/%m/%d')
                end_date = date.today().strftime('%Y/%m/%d')
                # 下载账单
                download_url = "%s?accountId=%s&currency=%s&cashRemit=&startDate=%s&endDate=%s" \
                               % (self.download_url, accountid, "001", begin_date, end_date)
                yield Request(
                    url=download_url,
                    callback=self.parse_download,
                    headers=self.headers,
                    meta=meta,
                    cookies=cookies,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except CaptchaTimeout:
            yield from self.error_handle(username, "中国银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "中国银行---数据解析异常")
        finally:
            driver.quit()

    def _get_trade_record_data(self, data):
        ret_data = data.strip()
        return ret_data if ret_data != "-" else ""

    def parse_download(self, response):
        meta = response.meta
        item = meta["item"]
        trade_records = item["trade_records"]

        try:
            # TODO 改成csv处理
            _get_trade_record_data = self._get_trade_record_data
            for i, tr in enumerate(response.body.decode("utf-16").split("\n")):
                tr = tr.strip()
                if 0 == i or "" == tr:
                    continue

                tr = tr.replace('"', '').split("\t")
                trade_income = tr[6].strip()
                trade_outcome = tr[7].strip()
                tmp_dict = {
                    "trade_date": tr[0].strip(),
                    "trade_remark": _get_trade_record_data(tr[1]),
                    "trade_acceptor_account": _get_trade_record_data(tr[3]),
                    "trade_acceptor_name": _get_trade_record_data(tr[2]),
                    "trade_currency": _get_trade_record_data(tr[4]),
                    "trade_income": trade_income,
                    "trade_outcome": trade_outcome,
                    "trade_amount": trade_income or ("-" + trade_outcome),
                    "trade_balance": _get_trade_record_data(tr[8]),
                    "trade_channel": _get_trade_record_data(tr[9]),  # 交易渠道
                }
                trade_records.append(tmp_dict)

            # 抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "浦发银行---账单解析异常")

    def click_hidemsgbox(self, wait):
        try:
            confirm_btn = wait.until(EC.visibility_of_element_located((By.ID, 'hideMsgBox')))
            confirm_btn.click()
        except Exception:
            pass
