# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep, strftime

from scrapy import FormRequest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from xlrd import open_workbook

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import IE233WebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, get_content_by_requests


class CncbSpider(IE233WebdriverSpider, BankSpider):
    name = "bank_cncb"
    allowed_domains = ['ecitic.com']
    start_urls = ["https://i.bank.ecitic.com/perbank6/signIn.do", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Referer": self._start_url_,
            "Origin": "https://i.bank.ecitic.com",
            "User-Agent": "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; .NET4.0C; .NET4.0E; InfoPath.3)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN",
            "Connection": "Keep-Alive"
        }
        self.history_pattern = re_compile(r'<.*?>')
        self.EMP_SID_pattern = re_compile(r'EMP_SID=([A-Za-z\d]*)')
        self.balance_pattern = re_compile(r'￥([\d\.]*)')
        self.name_pattern = re_compile(r'name="(.*?)"')
        self.value_pattern = re_compile(r'value="(.*?)"')
        self.account_balance_url = 'https://i.bank.ecitic.com/perbank6/pb1110_my_debitcard.do?EMP_SID={0}'
        self.currency_info_url = 'https://i.bank.ecitic.com/perbank6/trans_3063s.do?EMP_SID={0}'
        self.account_detail_url = 'https://i.bank.ecitic.com/perbank6/pb1310_account_detail.do?EMP_SID={0}'
        self.export_detail_url = 'https://i.bank.ecitic.com/perbank6/exportExcel.do?EMP_SID={0}'

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item['username']

        driver = self.load_page_by_webdriver(response.url)
        pid = driver.iedriver.process.pid
        try:
            sleep(3)
            with Ddxoft(pid) as dd_opt:
                driver.execute_script('document.getElementsByName("logonNoCert")[0].value="{0}";'
                                      'document.getElementsByName("logonNoCert")[0].focus()'.format(username))
                dd_opt.dd_tab()
                sleep(0.1)
                for i in item['password']:
                    dd_opt.dd_keyboard(i)
                    sleep(0.1)

            if driver.find_element_by_id('verifyId').is_displayed():
                captcha_input = driver.find_element_by_name('verifyCode')
                captcha_url = driver.find_element_by_id('pinImg').get_attribute('src')
                capcha_cookies = get_cookies_dict_from_webdriver(driver)
                capcha_body = get_content_by_requests(captcha_url, headers=self.headers,
                                                      cookie_jar=capcha_cookies)
                captcha_code = self.ask_image_captcha(capcha_body, username)
                captcha_input.send_keys(captcha_code)
                sleep(0.5)
                # 验证码正误弹窗
                try:
                    driver.switch_to.alert.accept()
                except Exception:
                    pass
                if 'stop_button' in driver.find_element_by_id('verifyImg').get_attribute('src'):
                    yield from self.error_handle(username,
                                                 "中信银行---登录失败：(username:%s, password:%s) %s"
                                                 % (username, item["password"], '验证码输入错误'),
                                                 tell_msg='验证码错误')
                    return

            butt_submit = driver.find_element_by_id('logonButton')
            butt_submit_onclick_js = butt_submit.get_attribute('onclick')
            driver.execute_script(butt_submit_onclick_js)
            # butt_submit.click()
            sleep(2)
            try:
                errorReason = driver.find_element_by_class_name('errorReason')
                message = errorReason.text
                yield from self.error_handle(username,
                                             "中信银行---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], message),
                                             tell_msg=message)
                return
            except NoSuchElementException:
                pass

            # if driver.find_element_by_id('firstLogonMdyPwdID').is_displayed():  # 出现这个元素要重置密码
            #     # 只出现了一次 不知道是啥样了。先记在这里
            #     pass

            ''' 跳过修改密码'''
            if driver.find_elements_by_xpath('//a[contains(text(),"跳过")]'):
                jump_js = (driver.find_element_by_xpath('//a[contains(@onclick,"jumpTip")]').get_attribute('onclick')
                           or driver.find_element_by_xpath('//a[contains(text(),"跳过")]').get_attribute('onclick'))
                driver.execute_script(jump_js)
                if driver.find_element_by_id('jumpTipDiv').is_displayed():
                    jump_ok_js = driver.find_element_by_id('jump').get_attribute('onclick')
                    driver.execute_script(jump_ok_js)

            ''' 短信验证  (突然又不出现了暂未测完全)'''
            if driver.find_elements_by_name('mdpBtn'):
                get_sms_code_js = driver.find_element_by_name('mdpBtn').get_attribute('onclick').replace('javascript:', '')
                # check_ok_js = driver.find_element_by_id('checkId').get_attribute('onclick').replace('javascript:', '')
                btn_next_js = driver.find_element_by_id('nextStep').get_attribute('onclick').replace('javascript:', '')
                max_loop_time = 10
                while not driver.find_element_by_id('checkId').is_selected() and max_loop_time > 0:
                    driver.find_element_by_id('checkId').click()
                    max_loop_time -= 1
                driver.execute_script(get_sms_code_js)
                sms_code = self.ask_sms_captcha(username)
                driver.execute_script('document.getElementsByName("mobilDynPwdStr1")[0].value="{0}";'.format(sms_code))
                sleep(1)

                driver.execute_script(btn_next_js)
                if driver.find_elements_by_xpath('//dl/dd/b'):
                    err_message = driver.find_element_by_xpath('//dl/dd/b').text
                    yield from self.error_handle(username, "中信银行---短信验证码出错：%s " % err_message,
                                                 tell_msg=err_message)
                    return

            self.wait_xpath(driver, '//input[@id="searchItemId"]')
            EMP_SID = self.EMP_SID_pattern.search(driver.find_element_by_id('formLogout').get_attribute('action'))
            if EMP_SID:
                EMP_SID = EMP_SID.group(1)
            else:
                driver.execute_script('document.getElementById("searchItemId").value="账户查询";')
                driver.find_element_by_id('searchItemId').send_keys(Keys.ENTER)
                driver.find_element_by_id('searchItemId').send_keys(Keys.ENTER)
                driver.find_element_by_id('searchItemId').send_keys(Keys.ENTER)
                sleep(1)
                mainframe = driver.find_element_by_id('mainframe')
                driver.switch_to.frame(mainframe)
                try:
                    EMP_SID = self.EMP_SID_pattern.search(driver.page_source).group(1)
                except AttributeError:
                    yield from self.error_handle(username, "中信银行---解析失败：EMP_SID 获取失败",
                                                 tell_msg='解析出错！')
                    return
            meta["EMP_SID"] = EMP_SID
            cookies = get_cookies_dict_from_webdriver(driver)
            yield FormRequest(
                url=self.account_balance_url.format(EMP_SID),
                callback=self.parse_balance,
                headers=self.headers,
                cookies=cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except CaptchaTimeout:
            yield from self.error_handle(username, "中信银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, "中信银行---解析失败", tell_msg="解析失败")
        finally:
            driver.quit()

    def parse_balance(self, response):
        meta = response.meta
        item = meta['item']
        username = item["username"]

        card_list = response.xpath('//tr')
        for card in card_list:
            card_rows = card.xpath('//td').extract()
            card_num_info_html = card_rows[0]
            card_balance_info_html = card_rows[3]
            if username in card_num_info_html:
                try:
                    item['balance'] = self.balance_pattern.search(card_balance_info_html).group(1)
                except Exception:
                    pass
        req_data = {
            'accountNo': username,
            'selectSubAccount': 'null'
        }
        yield FormRequest(
            url=self.currency_info_url.format(meta["EMP_SID"]),
            callback=self.parse_currency,
            formdata=req_data,
            meta=meta,
            dont_filter=True,
            errback=self.err_callback
        )

    def parse_currency(self, response):
        meta = response.meta
        username = meta['item']['username']

        detail_from_input = response.xpath('//input').extract()
        req_data = {'equipmentNO': '',
                    'accountNo': username,
                    }

        for the_input in detail_from_input:
            input_name = self.name_pattern.search(the_input).group(1)
            value = self.value_pattern.search(the_input)
            if input_name == 'isubAccInfo.accountNo' and value:
                req_data['stdpriacno'] = value.group(1)

        if not req_data.get('stdpriacno'):
            curr_list = response.xpath('//a/@selectid').extract_first()
            if curr_list:
                req_data['stdpriacno'] = curr_list.split('|')[3]

        today = strftime("%Y%m%d")
        begin_day = str(int(today) - 10000)  # 一年

        req_data['stdessbgdt'] = begin_day
        req_data['stdesseddt'] = today
        req_data['std400dcfg'] = ''
        req_data['opFlag'] = '0'
        req_data['stkessmnam'] = ''
        req_data['largeAmount'] = ''
        req_data['stdudfcyno'] = '001'
        req_data['stdesssbno'] = ''
        req_data['CashFlag'] = ''
        req_data['std400chnn'] = ''
        req_data['std400pgqf'] = 'N'
        req_data['startPageFlag'] = ''
        req_data['pageType'] = '1'
        req_data['recordStart'] = '1'
        req_data['recordNum'] = ''
        req_data['queryDays'] = ''
        req_data['lccOrderFlgQry'] = '1'
        req_data['sheetName'] = '�˻���ϸ��ѯ'  # 账户明细查询
        req_data['headLine'] = '�˺ţ�{0} �����  ��ʼ����:{1} ��ֹ����:{2}(9)'. \
            format(username, begin_day, today)  # 账号： 人民币  起始日期: 截止日期:
        req_data['bizId'] = 'accountDetail'
        req_data['flowId'] = 'pb1310_export_detail'
        req_data['iCollName'] = 'iTransInfo'
        req_data['titles'] = '���׿���,��������,֧�����,������,�˻����,�Է�,�������,ժҪ,״̬'
        # 交易卡号，交易日期，支出金额，收入金额，账户余额，对方，受理机构，摘要，状态
        req_data['fields'] = 'equipmentNO,stdesstrdt,stdessdcfg,stdesstram,' \
                             'stdessacbl,fndoppacno,stdoppbrna,stdes2bref,std400desc'

        yield FormRequest(
            url=self.export_detail_url.format(meta["EMP_SID"]),
            callback=self.parse_export,
            formdata=req_data,
            meta=meta,
            dont_filter=True,
            errback=self.err_callback
        )

    def parse_export(self, response):
        item = response.meta['item']
        try:
            with open_workbook(file_contents=response.body) as bk:
                infos_sheet = bk.sheet_by_index(0)
                trade_records = item["trade_records"]
                for i in range(2, infos_sheet.nrows):
                    row_datas = bk.sheet_by_index(0).row_values(i)
                    trade_outcome = row_datas[2].replace('_', '')
                    trade_income = row_datas[3].replace('_', '')
                    trade_records.append({
                        'trade_date': row_datas[1],
                        'trade_accounting_date': row_datas[1].replace('-', ''),
                        'trade_outcome': trade_outcome,
                        'trade_income': trade_income,
                        'trade_balance': row_datas[4],
                        'trade_acceptor_account': row_datas[5],
                        'trade_location': row_datas[6],
                        'trade_remark': row_datas[7],
                        'trade_amount': trade_income or ("-" + trade_outcome),
                    })

            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "中信银行---交易明细解析失败",
                                          tell_msg="交易明细解析失败")

    # 以下之前采用分页请求，现在没使用

    def parse_curlist(self, response):
        meta = response.meta
        username = meta['item']['username']
        detail_from_input = response.xpath('//input').extract()
        req_data = {}
        for the_input in detail_from_input:
            input_name = self.name_pattern.search(the_input).group(1)
            value = self.value_pattern.search(the_input)
            req_data[input_name] = '' if not value else value.group(1)
        req_data['payAcctxt'] = username
        curr_list = response.xpath('//a/@selectid').extract_first()
        if curr_list:
            req_data['currList'] = curr_list
        else:
            req_data['currList'] = '|'.join([req_data['isubAccInfo.subAccountNo'],
                                             req_data['isubAccInfo.balance'],
                                             req_data['isubAccInfo.currencyType'],  # 001 为人民币
                                             req_data['isubAccInfo.accountNo'],
                                             'null', '人民币'])

        today = strftime("%Y%m%d")
        if 'isubAccInfo.accountNo' in req_data:
            req_data['stdpriacno'] = req_data['isubAccInfo.accountNo']
        else:
            req_data['stdpriacno'] = req_data['currList'].split('|')[3]
        req_data['beginDate'] = '20170702'
        req_data['endDate'] = '20170801'
        req_data['beginAmtText'] = '请输入起始金额'
        req_data['endAmtText'] = '请输入截止金额'
        req_data['accountNo'] = username
        req_data['stdessbgdt'] = str(int(today) - 10000)  # 一年
        req_data['stdesseddt'] = today
        req_data['recordStart'] = '1'
        req_data['recordNum'] = '10'
        req_data['std400pgqf'] = 'N'
        req_data['stdudfcyno'] = '001'  # 001是人民币
        req_data['opFlag'] = '0'
        req_data['queryType'] = 'nearOneYearTab'
        req_data['targetPage'] = '1'
        req_data['recordSize'] = '10'
        req_data['queryDays'] = ''
        req_data['startPageFlag'] = ''
        req_data['pageType'] = ''
        req_data['beforePageMap'] = ''
        req_data['beginAmt'] = ''
        req_data['endAmt'] = ''
        req_data['stkessmnam'] = ''
        req_data['largeAmount'] = ''
        req_data['std400pgtk'] = ''
        req_data['std400pgts'] = ''
        req_data['stdesssbno'] = ''
        req_data['CashFlag'] = ''
        meta['req_data'] = req_data
        yield FormRequest(
            url=self.account_detail_url.format(meta["EMP_SID"]),
            callback=self.parse_detail,
            formdata=req_data,
            meta=meta,
            dont_filter=True,
            errback=self.err_callback
        )
