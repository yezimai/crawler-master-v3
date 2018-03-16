# -*- coding: utf-8 -*-

from itertools import islice
from re import compile as re_compile
from time import sleep, strftime

from scrapy import FormRequest
from selenium.common.exceptions import NoSuchElementException, WebDriverException

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import IE233WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, get_content_by_requests


class CmbSpider(IE233WebdriverSpider, BankSpider):
    name = "bank_cmb"
    allowed_domains = ["cmbchina.com"]
    start_urls = ["https://pbsz.ebank.cmbchina.com/CmbBank_GenShell/UI/GenShellPC/Login/Login.aspx", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_token_url = 'https://pbsz.ebank.cmbchina.com/CmbBank_GenShell/UI/GenShellPC/Login/ApplyToken.aspx'
        self.debitcard_login_url = 'https://pbsz.ebank.cmbchina.com/CmbBank_DebitCard_AccountManager/UI/DebitCard/Login/Login.aspx'
        self.account_url = 'https://pbsz.ebank.cmbchina.com/CmbBank_DebitCard_AccountManager/UI/DebitCard/AccountQuery/am_QuerySubAccount.aspx'
        self.detail_url = 'https://pbsz.ebank.cmbchina.com/CmbBank_DebitCard_AccountManager/UI/DebitCard/AccountQuery/am_QueryHistoryTrans.aspx'

        self.headers = {
            "Referer": 'https://pbsz.ebank.cmbchina.com/CmbBank_GenShell/UI/GenShellPC/Login/GenIndex.aspx',
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; InfoPath.3)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN",
            "Connection": "Keep-Alive"
        }
        self.auth_pattern = re_compile(r'<AuthResponseBody>(.*)</AuthResponseBody>')
        self.client_no_pattern = re_compile(r'<ClientNo>(.*)</ClientNo>')

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item['username']

        driver = self.load_page_by_webdriver(response.url)
        pid = driver.iedriver.process.pid
        try:
            # 停顿2秒 准备模拟键盘输入
            sleep(2)
            with Ddxoft(pid) as dd_opt:
                for i in username:
                    dd_opt.dd_keyboard(i)
                sleep(0.5)
                dd_opt.dd_tab()
                sleep(0.5)
                for i in item['password']:
                    dd_opt.dd_keyboard(i)

            butt_submit = driver.find_element_by_id('LoginBtn')
            # butt_submit.click()
            butt_submit_onclick_js = butt_submit.get_attribute('onclick').replace('javascript:', '')
            driver.execute_script(butt_submit_onclick_js)
            sleep(1)

            # 有可能有附加码（附加码在点击登录后生成 所以填完还得登一下）
            try:
                have_extra = driver.find_element_by_id('ImgExtraPwd').is_displayed()
            except WebDriverException:
                have_extra = False

            if have_extra:
                captcha_input = driver.find_element_by_id('ExtraPwd')
                captcha_url = driver.find_element_by_id('ImgExtraPwd').get_attribute('src')
                capcha_cookies = get_cookies_dict_from_webdriver(driver)
                capcha_body = get_content_by_requests(captcha_url, headers=self.headers,
                                                      cookie_jar=capcha_cookies)
                captcha_code = self.ask_image_captcha(capcha_body, username)
                captcha_input.send_keys(captcha_code)
                sleep(0.5)
                driver.execute_script(butt_submit_onclick_js)

            # 可能已经登录进去了 这个element不在了
            try:
                if driver.find_element_by_class_name('page-form-item-controls').is_displayed():
                    err_message = driver.find_element_by_xpath('//label[@class="control-text error-msg"]').text
                    yield from self.error_handle(username,
                                                 "招商银行---登录失败：%s"
                                                 % (err_message),
                                                 tell_msg=err_message)
                    return
            except WebDriverException:
                pass
            sleep(1)

            try:
                # 有可能没有验证手机，之前试过多次发短信验证码，第二天神奇的不用验证短信了。。
                # self.wait_xpath(driver, '//input[@id="btnSendCode"]')
                sleep(1)
                btnSendCode = driver.find_element_by_id('btnSendCode')
                self.element_click_three_times(btnSendCode)
                sms_code = self.ask_sms_captcha(username)
                sms_code_input = driver.find_element_by_name('txtSendCode')
                sms_code_input.send_keys(sms_code)
                sleep(1)
                submit = driver.find_element_by_id('btnVerifyCode')
                self.element_click_three_times(submit)
                sleep(2)
                try:
                    have_error = driver.find_element_by_class_name('control-explain').is_displayed()
                except WebDriverException:
                    have_error = False

                if have_error:
                    err_message = driver.find_element_by_xpath('//p[@class="control-explain"]').text
                    yield from self.error_handle(username,
                                                 "招商银行---登录失败：%s"
                                                 % (err_message),
                                                 tell_msg=err_message)
                    return
            except NoSuchElementException:
                pass

            # 站点地图点击 (以下未使用执行js 执行js会直接close)
            cookies = get_cookies_dict_from_webdriver(driver)
            client_no = driver.find_element_by_name('ClientNo').get_attribute('value')
            data = {'ClientNo': client_no, 'AuthName': '<AuthName>CBANK_DEBITCARD_ACCOUNTMANAGER</AuthName>'}
            meta['client_no'] = client_no
            meta["cookies"] = cookies
            yield FormRequest(
                url=self.apply_token_url,
                callback=self.parse_token,
                headers=self.headers,
                formdata=data,
                cookies=cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
            # 以下为之前的webdriver点击方式
            # if 0 != 0:
            #     self.element_click_three_times(driver.find_element_by_xpath('//a[3]'))
            #     # func_map_onclick_js = driver.find_element_by_xpath('//a[3]').get_attribute('onclick')
            #     # driver.execute_script(func_map_onclick_js)
            #     frame = driver.find_element_by_id('mainWorkArea')
            #     # 转到 主工作区 iframe 里面
            #     driver.switch_to.frame(frame)
            #     # 站点地图 获取余额
            #     btn_account_summary = driver.find_element_by_xpath('//div[contains(text(),"账户总览")]|'
            #                                                     '//DIV[contains(text(),"账户总览")]')
            #     self.element_click_three_times(btn_account_summary)
            #     # self.wait_xpath(driver,'//span[@id="lblSumOfMoney"]')
            #     balance = driver.find_element_by_id('lblSumOfMoney').text
            #     if balance:
            #         item['balance'] = balance
            #     # 返回
            #     driver.switch_to.default_content()
            #     # 站点地图再次点击
            #     self.element_click_three_times(driver.find_element_by_xpath('//a[3]'))
            #     frame = driver.find_element_by_id('mainWorkArea')
            #     # 又转到 主工作区 iframe 里面
            #     driver.switch_to.frame(frame)
            #     # 站点地图 历史交易
            #     btn_history_tran = driver.find_element_by_xpath('//div[contains(text(),"历史交易查询")]|'
            #                                                     '//DIV[contains(text(),"历史交易查询")]')
            #     self.element_click_three_times(btn_history_tran)
            #     # btn_history_tran_onclick_js = btn_history_tran.get_attribute('onclick')
            #     # driver.execute_script(btn_history_tran_onclick_js)
            #     self.wait_xpath(driver, '//input[@id="EndDate"]')
            #
            #     # 结束日期如:20170621   开始日期201606021
            #     end_date = int(driver.find_element_by_name('EndDate').get_attribute('value'))
            #     start_date = end_date - 10000
            #     start_date_input = driver.find_element_by_name('BeginDate')
            #     start_date_input.clear()
            #     start_date_input.send_keys(start_date)
            #     btnOK = driver.find_element_by_name('BtnOK')
            #     sleep(0.5)
            #     # btnOK_onclick_js = btnOK.get_attribute('onclick')
            #     # driver.execute_script(btnOK_onclick_js)
            #     self.element_click_three_times(btnOK)
            #     # OutCount 是支出交易笔数， 这个出来了table也出来了
            #     self.wait_xpath(driver, '//span[@id="OutCount"]')
            #
            #     history_records_table = Selector(text=driver.page_source).xpath('//td[@align="left"]/text()|'
            #                                                                     '//td[@align="middle"]/text()|'
            #                                                                     '//td[@align="right"]/text()').extract()
            #     # 每七个为一条记录
            #     group_list_split = 7
            #     trade_records = item["trade_records"]
            #     titles = ['trade_accounting_date', 'trade_date', 'trade_outcome', 'trade_income',
            #               'trade_balance', 'trade_type', 'trade_remark', 'trade_amount']
            #     for record in (history_records_table[i:i + group_list_split] for i in
            #                    range(0, len(history_records_table), group_list_split)):
            #         record[0] = record[0].strip()
            #         record[1] = record[0] + record[1].strip()
            #         record[2] = record[2].replace('-', '').strip()
            #         record[3] = record[3].replace('-', '').strip()
            #         record[4] = record[4].strip()
            #         record.append(record[3] or ("-" + record[2]))
            #         trade_records.append(dict(zip(titles, record)))
            #
            #     if 'balance' not in item and trade_records:
            #         item['balance'] = trade_records[-1].get('trade_balance', 0)
            #
            #     yield from self.crawling_done(item)
        except CaptchaTimeout:
            yield from self.error_handle(username, "招商银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "招商银行---解析失败",
                                          tell_msg="解析失败")
        finally:
            driver.quit()

    def parse_token(self, response):
        meta = response.meta
        try:
            AuthResponseBody = self.auth_pattern.search(response.text)
            if AuthResponseBody:
                data = {'ClientNo': meta['client_no'],
                        'AuthToken': AuthResponseBody.group(1)
                        }
                yield FormRequest(
                    url=self.debitcard_login_url,
                    callback=self.parse_debit_card_login,
                    headers=self.headers,
                    formdata=data,
                    cookies=meta["cookies"],
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(meta['item']["username"], "招商银行---token解析失败",
                                          tell_msg="token解析失败")

    def parse_debit_card_login(self, response):
        meta = response.meta
        try:
            client_no = self.client_no_pattern.search(response.text)
            if client_no:
                client_no = client_no.group(1)
                meta['client_no'] = client_no
                yield FormRequest(
                    url=self.account_url,
                    callback=self.parse_account,
                    formdata={'ClientNo': client_no},
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(meta['item']["username"], "招商银行---银行卡登录解析失败",
                                          tell_msg="银行卡登录解析失败")

    def parse_account(self, response):
        meta = response.meta
        try:
            client_no = meta['client_no']
            balance = response.xpath('//table[@class="dgMain"]/tr/td/text()').extract()
            # 前10个是title  余额位于第15个第11个text为空
            meta['item']['balance'] = balance[13] if len(balance) > 14 else 0

            yield FormRequest(
                url=self.detail_url,
                callback=self.parse_detail_query,
                formdata={'ClientNo': client_no},
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(meta['item']["username"], "招商银行---银行卡信息解析失败",
                                          tell_msg="银行卡信息解析失败")

    def parse_detail_query(self, response):
        try:
            __EVENTTARGET = response.xpath('//input[@id="__EVENTTARGET"]/@value').extract_first("")
            __EVENTARGUMENT = response.xpath('//input[@id="__EVENTARGUMENT"]/@value').extract_first("")
            __LASTFOCUS = response.xpath('//input[@id="__LASTFOCUS"]/@value').extract_first("")
            __VIEWSTATE = response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first("")
            __VIEWSTATEGENERATOR = response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').extract_first("")
            __EVENTVALIDATION = response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first("")
            uc_AdvAdvLocID = response.xpath('//input[@id="uc_Adv$AdvLocID"]/@value').extract_first("")
            ClientNo = response.meta['client_no']
            PanelControl = response.xpath('//input[@id="PanelControl"]/@value').extract_first("")
            ddlDebitCardList = response.xpath('//select[@name="ddlDebitCardList"]'
                                              '/option[@selected="selected"]/@value').extract_first("")
            ddlSubAccountList = response.xpath('//select[@name="ddlSubAccountList"]'
                                               '/option[@selected="selected"]/@value').extract_first("")
            ddlTransTypeList = response.xpath('//select[@name="ddlTransTypeList"]/option/@value').extract_first("")

            today = strftime("%Y%m%d")
            data = {
                '__EVENTTARGET': __EVENTTARGET,
                '__EVENTARGUMENT': __EVENTARGUMENT,
                '__LASTFOCUS': __LASTFOCUS,
                '__VIEWSTATE': __VIEWSTATE,
                '__VIEWSTATEGENERATOR': __VIEWSTATEGENERATOR,
                '__EVENTVALIDATION': __EVENTVALIDATION,
                'uc_Adv$AdvLocID': uc_AdvAdvLocID,
                'ClientNo': ClientNo,
                'PanelControl': PanelControl,
                'ddlDebitCardList': ddlDebitCardList,
                'ddlSubAccountList': ddlSubAccountList,
                'ddlTransTypeList': ddlTransTypeList,
                'BeginDate': str(int(today) - 10000),  # 一年
                'EndDate': today,
                'BtnOK': '查询'
            }
            yield FormRequest(
                url=self.detail_url,
                callback=self.parse_detail,
                formdata=data,
                meta=response.meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(response.meta['item']["username"], "招商银行---交易明细查询解析失败",
                                          tell_msg="交易明细查询解析失败")

    def parse_detail(self, response):
        try:
            item = response.meta['item']
            history_records_table = response.xpath('//table[@class="dgMain"]/tr/td/text()').extract()

            trade_records = item["trade_records"]
            titles = ['trade_accounting_date', 'trade_date', 'trade_outcome', 'trade_income',
                      'trade_balance', 'trade_type', 'trade_remark', 'trade_amount']
            for record in islice((history_records_table[i:i + 7] for i in
                                  range(0, len(history_records_table), 7)), 1, None):
                record[0] = record[0].strip()
                record[1] = record[0] + record[1].strip()
                record[2] = record[2].replace(' ', '').strip()
                record[3] = record[3].replace(' ', '').strip()
                record[4] = record[4].strip()
                record.append(record[3] or ("-" + record[2]))
                trade_records.append(dict(zip(titles, record)))

            if 'balance' not in item and trade_records:
                item['balance'] = trade_records[-1].get('trade_balance', 0)

            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(response.meta['item']["username"], "招商银行---交易明细解析失败",
                                          tell_msg="交易明细解析失败")
