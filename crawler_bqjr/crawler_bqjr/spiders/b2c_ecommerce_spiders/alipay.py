# -*- coding: utf-8 -*-

from datetime import date
from hashlib import md5
from random import random
from re import compile as re_compile
from time import sleep
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from lxml import html
from requests import Session
from scrapy import Request
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.support import ui

from crawler_bqjr.items.ecommerce_items import ZhiFuBaoItem
from crawler_bqjr.spider_class import CaptchaTimeout, HeadlessChromeWebdriverSpider
from crawler_bqjr.spiders.b2c_ecommerce_spiders.base import EcommerceSpider
from crawler_bqjr.spiders_settings import ALIPAY_DICT
from crawler_bqjr.utils import driver_screenshot_2_bytes, get_js_time, \
    get_cookies_dict_from_webdriver
from global_utils import json_loads, json_dumps


class AlipaySpider(HeadlessChromeWebdriverSpider, EcommerceSpider):
    """
    支付宝爬虫
    """

    name = ALIPAY_DICT["支付宝"]
    allowed_domains = ["alipay.com", "taobao.com"]
    start_urls = ['https://auth.alipay.com/login/index.htm']

    # 账单时间对应表
    BILL_TIME_DICT = {
        "1": "oneMonth",
        "3": "threeMonths",
        "7": "sevenDays",
    }

    STEP_POS_DICT = {
        "step_login": "登录",
        "step_query": "查询账单",
        "step_amount": "查询总额",
        "step_bill": "获取账单",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=ZhiFuBaoItem, **kwargs)

        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.04"
        }

        self.query_bill_time = 3  # 查询3个月内的账单
        self.reg_query_url = re_compile(r'queryUrl: "([^"]*)"')
        self.reg_sec_id = re_compile(r'securityId: "([^"]*)"')
        self.reg_get_json = re_compile(r'(\{[\s\S]+\})')
        self.reg_check_code = re_compile(r'id="J-checkcode-img" src="([^"]+)"')
        self.reg_form_tk = re_compile(r'form_tk = "([^"]*)"')
        self.reg_sec_id_download = re_compile(r'data-request="([^"]*)"')
        self.reg_amount_detail = re_compile(r'已支出(\d+)笔共([\d\.]+)元，待支出(\d+)笔'
                                            r'共([\d\.]+)元 \| 已收入(\d+)笔共([\d\.]+)元，'
                                            r'待收入(\d+)笔共([\d\.]+)元')

    def parse(self, response):
        meta = response.meta
        username = meta["item"]["username"]
        login_type = meta["login_type"]  # 1:账户密码登录,2:扫描二维码登录
        try:
            if login_type == self.LOGIN_TYPE.get("account_login"):
                # 账户密码登录
                yield from self.login(response)
            elif login_type == self.LOGIN_TYPE.get("qrcode_login"):
                # 通过扫描二维码登录
                yield from self.qrcode_login(response)
            else:
                self.logger.debug("--->请确认登录方式")
                yield from self.crawling_failed(username, "支付宝登录失败")
        except Exception:
            yield from self.except_handle(username, "登录异常")

    def _confirm_login(self, response):
        """
        确认是否登录成功
        :param response:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        cookies = meta["cookies"]
        try:
            user_email = response.xpath('//*[@id="J-userInfo-account-userEmail"]')
            if user_email:
                self.logger.info("支付宝登录成功")

                # 登录成功后，先尝试下载交易记录并解析
                item = meta["item"]
                zhifubao_deals = self._get_zhifubao_deals(username, cookies)
                if not zhifubao_deals:
                    self.logger.error("获取支付宝交易记录失败")
                else:
                    self.logger.info("获取支付宝交易记录成功，开始获取收货地址信息")
                item["zhifubao_deals"] = zhifubao_deals or {}

                # 通知授权成功
                self.crawling_login(username)

                yield Request(
                    url="https://memberprod.alipay.com/address/index.htm",
                    meta=response.meta,
                    callback=self._parse_address_info,
                    errback=self.err_callback,
                    headers=self.headers,
                    dont_filter=True
                )
            else:
                yield from self.crawling_failed(username, "支付宝登录失败")
        except Exception:
            yield from self.except_handle(username, "登录异常")

    def _get_zhifubao_deals(self, username, cookies):
        """
        获取支付宝交易记录信息(最近三个月)
        :param username:
        :param cookies:
        :return:
        """
        download_record_flag = False  # 通过下载账单的方式失败,故暂不采用此方法

        record_url = "https://consumeprod.alipay.com/record/advanced.htm"
        my_dcap = self.dcap.copy()
        driver = self.get_driver(dcap=my_dcap)
        try:
            driver.get(record_url)
            driver.delete_all_cookies()
            for k, v in cookies.items():
                cookie = {"name": k, "value": v}
                driver.add_cookie(cookie)  # 添加cookies
            driver.implicitly_wait(1)
            driver.refresh()
            driver.get(record_url)
            driver.implicitly_wait(1)
            driver.maximize_window()
            # 先判断是否需要身份验证
            if self._get_element(driver, "risk_qrcode_cnt"):
                # 需要身份验证
                if not self._get_verify_result(driver, username, step_pos="step_query").get("status"):
                    return
            # 先判断账单页面版本，需要切换到高级版
            standard_btn = self._get_element(driver, '切换到高级版', self.BY_LINK)
            if standard_btn:
                self.logger.info("正在从账单标准版切换到高级版")
                standard_btn.click()
            # 选择查询条件，选择近三个月数据
            date_select_btn = self._get_element(driver, '//a[@seed="JDatetimeSelect-link"]', self.BY_XPATH)
            if not date_select_btn:
                self.logger.error("获取日期选择框失败")
                return
            action = ActionChains(driver)
            action.move_to_element(date_select_btn)
            action.click(date_select_btn)
            option_xpath = '//li[@data-value="%s"]' % self.BILL_TIME_DICT.get(str(self.query_bill_time), "3")
            option_sel = self._get_element(driver, option_xpath, self.BY_XPATH)
            action.move_to_element(option_sel)
            action.click(option_sel)
            action.perform()
            search_btn = self._get_element(driver, 'J-set-query-form')
            if not search_btn:
                self.logger.error("获取页面搜索按钮失败")
                return
            search_btn.click()
            # 选择统计金额
            # 统计金额会进行安全校验，URL中需要添加ctoken字段
            # 先判断是否需要身份验证
            if self._get_element(driver, "risk_qrcode_cnt"):
                # 需要身份验证
                if not self._get_verify_result(driver, username, step_pos="step_amount").get("status"):
                    return
            ctoken = cookies.get("ctoken", '')
            driver.execute_script('''
                var amount_tag = document.getElementsByClassName("amount-links")[0];
                var old_url = amount_tag.href;
                amount_tag.href = old_url + "&_input_charset=utf-8&ctoken={ctoken}"
            '''.format(ctoken=ctoken))
            new_cookie_dic = {
                "name": "ctoken",
                "value": ctoken
            }
            driver.add_cookie(new_cookie_dic)  # 添加ctoken
            self._get_element(driver, '//a[@class="amount-links"]', self.BY_XPATH).click()

            if download_record_flag:
                # 通过selenium下载账单
                record_info = self.__download_record(driver, username)
            else:
                # 用selenium翻页获取账单信息
                record_info = self.__parse_record_page(driver, username)

            return record_info
        except Exception:
            self.logger.exception("获取支付宝交易记录信息出错:")
        finally:
            driver.quit()

    def __parse_record_page(self, driver, username):
        """
        通过selenium翻页获取账单信息
        :param driver:
        :param username:
        :return:
        """
        try:
            record_info = {}
            page = driver.page_source
            element = html.fromstring(page)
            # 获取统计金额
            amount_detail_str = self.xpath_match(element, '//div[@class="amount-detail"]/text()')
            amount_detail_list = self.reg_match(amount_detail_str, self.reg_amount_detail, get_one=False)
            amount_detail_list = amount_detail_list[0] if amount_detail_list else None
            amount_deatil_len = 8
            if amount_detail_list and len(amount_detail_list) == amount_deatil_len:
                (total_pay_num, total_pay_money, unpayed_num, unpayed_money, already_earned_num,
                 already_earned_money, pend_income_num, pend_income_money) = amount_detail_list
                record_info["amount_deatil"] = {
                    "total_pay_num": total_pay_num,
                    "total_pay_money": total_pay_money,
                    "unpayed_num": unpayed_num,
                    "unpayed_money": unpayed_money,
                    "already_earned_num": already_earned_num,
                    "already_earned_money": already_earned_money,
                    "pend_income_num": pend_income_num,
                    "pend_income_money": pend_income_money,
                }
            else:
                # 通过requests获取账单金额数据
                self.logger.info("--->通过requests请求获取账单统计金额数据中...")
                amount_deatil = self._get_amount_deatil(driver=driver)
                record_info["amount_deatil"] = amount_deatil or {}

            # 循环获取所有账单记录
            parse_next_page = True  # 下一页标志
            records = []
            page_num = 1
            ret_set = set()  # 用于数据去重(当身份验证时可能会出现重复数据)
            while parse_next_page:
                self.logger.info("--->解析第[%d]页账单数据中..." % page_num)
                tr_items = self.xpath_match(element, '//table[@id="tradeRecordsIndex"]/tbody/tr', get_one=False)
                if tr_items:
                    for item in tr_items:
                        time_date = self.xpath_match(item, './/td[@class="time"]/p[@class="time-d"]/text()')
                        time_hour = self.xpath_match(item, './/td[@class="time"]/p[@class="time-h ft-gray"]/text()')
                        trade_time = time_date.replace('.', '-') + " " + time_hour + ":00" if \
                            isinstance(time_date, str) and isinstance(time_hour, str) else ''
                        trade_name = self.xpath_match(item, './/p[@class="consume-title"]/a/text()')
                        trade_no = self.xpath_match(item, './/td[@class="tradeNo ft-gray"]/p/text()')
                        trade_other = self.xpath_match(item, './/td[@class="other"]/p[@class="name"]/text()')
                        trade_amount = self.xpath_match(item, './/span[@class="amount-pay"]/text()')
                        trade_status = self.xpath_match(item, './/td[@class="status"]/p[1]/text()')
                        trade_info = {
                            "trade_time": trade_time,
                            "trade_name": trade_name,
                            "trade_no": trade_no,
                            "trade_other": trade_other,
                            "trade_amount": trade_amount,
                            "trade_status": trade_status
                        }

                        # 去重 取订单号的md5值作为判重条件
                        md5_val = self.__get_md5(trade_no)
                        if md5_val in ret_set:
                            self.logger.info("此数据已存在：%s" % str(trade_info))
                        else:
                            ret_set.add(md5_val)
                            records.append(trade_info)
                elif self._get_element(driver, "risk_qrcode_cnt"):
                    # 需要扫描二维码进行身份验证
                    if not self._get_verify_result(driver, username, step_pos="step_bill").get("status"):
                        break
                else:
                    self.logger.info("本页暂无账单数据")
                    break
                next_page_btn = self._get_element(driver, '//a[@seed="pageLink-pageNextT1"]', self.BY_XPATH)
                if next_page_btn:
                    # 方式1：直接点击下一页,下一页按钮被遮住
                    # next_page_btn.click()
                    # 方式2：执行JS,JS执行会出现系统繁忙，会检测请求参数
                    # driver.execute_script('document.getElementsByClassName("page-next page-trigger")[0].click();')
                    # 方式3：先滚动到页面底部，使下一个按钮可见(可行)
                    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                    next_page_btn.click()
                    current_page = driver.page_source
                    element = html.fromstring(current_page)
                    page_num += 1
                    sleep(0.5)  # 抓取过快会出现二维码验证身份
                else:
                    parse_next_page = False
                    self.logger.info("不存在下一页，解析账单记录完成，总页数：%d" % page_num)

            self.logger.info("所有账单记录获取完成，账单记录数为：%d" % len(records))
            record_info["records"] = records

            return record_info
        except Exception:
            self.logger.exception("通过selenium翻页获取账单信息失败:")
            return

    def _get_amount_deatil(self, driver):
        """
        获取账单统计金额
        :param driver:
        :return:
        """
        try:
            cookies = get_cookies_dict_from_webdriver(driver)
            ctoken = cookies.get("ctoken")
            date_range = self.BILL_TIME_DICT.get(str(self.query_bill_time))
            end_date = date.today()
            begin_date_str = (end_date - relativedelta(months=self.query_bill_time)).strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            param_data = {
                "_input_charset": "utf-8",
                "dateRange": date_range,
                "tradeType": "ALL",
                "status": "all",
                "fundFlow": "all",
                "keyword": "bizNo",
                "beginTime": "00:00",
                "endDate": end_date_str,
                "endTime": "24:00",
                "beginDate": begin_date_str,
                "dateType": "createDate",
                "pageNum": 1,
                "ctoken": ctoken
            }
            get_url = "https://consumeprod.alipay.com/record/statisticAdvanced.json?" + urlencode(param_data)
            ret_json = self.http_request(get_url, headers=self.headers, cookies=cookies, to_json=True)
            if ret_json.get("stat") == "ok":
                data = ret_json.get("statisticVO", {})
                amount_detail = {
                    "total_pay_num": data.get("expendCount"),
                    "total_pay_money": data.get("expendAmount"),
                    "unpayed_num": data.get("payableCount"),
                    "unpayed_money": data.get("payableAmount"),
                    "already_earned_num": data.get("incomeCount"),
                    "already_earned_money": data.get("incomeAmount"),
                    "pend_income_num": data.get("receivableCount"),
                    "pend_income_money": data.get("receivableAmount"),
                }
                self.logger.info("--->通过requests获取统计金额成功")
                return amount_detail
        except Exception:
            self.logger.exception("获取账单统计金额出错")

        return None

    def _scan_qrcode_verify(self, driver, username):
        """
        扫描二维码进行身份验证(获取账单信息和异地登录时可能会出现)
        :param driver:
        :param username:
        :return:
        """
        try:
            # 先设置样式
            style_js = '''
                var img = document.getElementById("risk_qrcode_cnt");
                img.setAttribute("style", "margin-right: 120px;")
            '''
            driver.execute_script(style_js)
            # 开始截取二维码图片
            qrcode_image = self._get_element(driver, '//div[@id="risk_qrcode_cnt"]/canvas', self.BY_XPATH)
            if not qrcode_image:
                self.logger.error("获取二维码图片失败")
                return False

            location = qrcode_image.location
            size = qrcode_image.size
            left = location["x"]
            top = location["y"]
            right = left + size["width"]
            bottom = top + size["height"]

            photo_base64 = driver.get_screenshot_as_base64()
            qrcode_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
            status = self.ask_scan_qrcode(qrcode_body, username)
            if status != self.SCAN_QRCODE_SUCC:
                self.logger.error("扫描二维码验证失败")
                return False
            ui.WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("J-set-query-form").is_displayed())
            return True
        except TimeoutException:
            self.logger.exception("等待扫描二维码验证超时")
            # 页面未跳转(可能验证成功或验证失败)
            driver.refresh()
            commit_btn = self._get_element(driver, '//input[@seed="checkSubmit-btn"]', self.BY_XPATH)
            if commit_btn and commit_btn.is_displayed():
                commit_btn.click()
                return True
            else:
                self.logger.error("--->请先扫描二维码进行身份验证")
                return
        except Exception:
            self.logger.exception("扫描二维码验证出错")
            return False

    def __get_md5(self, text):
        """
        获取字符串MD5值，用于数据去重
        :param text:
        :return:
        """
        try:
            if not isinstance(text, str):
                text = str(text)
            if isinstance(text, str):
                text = text.encode()
            hex_str = md5(text).hexdigest()
            return hex_str
        except Exception:
            self.logger.exception("转换MD5失败：%s" % text)
            return text

    def __download_record(self, driver, username):
        """
        通过selenium下载文件并解析获取账单信息(未测试通过，安全验证)
        :param driver:
        :param username:
        :return:
        """
        try:
            # 通过下载excel获得账单信息
            self._get_element(driver, '//a[@seed="actionOther-JDownloadTipT1"]', self.BY_XPATH).click()
            # driver.get_screenshot_as_file('excel.jpg')
            # 获取弹出框位置
            xbox_ele = self._get_element(driver, '//div[@class="alipay-xbox-content"]/iframe', self.BY_XPATH)
            if not xbox_ele:
                self.logger.error("获取二维码区域失败")
                return None

            xbox_location = xbox_ele.location
            x_left = xbox_location["x"]
            x_top = xbox_location["y"]

            driver.switch_to_frame(xbox_ele)  # 切换到下载界面，可能会验证身份或重新登录
            auth_ele = self._get_element(driver, '//a[@seed="authcenter-qrshow"]', self.BY_XPATH)
            if auth_ele:
                self.logger.info("会话超时，请重新登录")
                return None

            qrcode_ele = self._get_element(driver, '//a[@seed="qrcodeInfo-link"]', self.BY_XPATH)
            if qrcode_ele:
                self.logger.info("需要扫描二维码验证身份")
                # 开始截取二维码图片
                qrcode_image = self._get_element(driver, '//div[@id="risk_qrcode_cnt"]/canvas', self.BY_XPATH)
                if not qrcode_image:
                    self.logger.error("获取二维码图片位置失败")
                    return None

                location = qrcode_image.location
                size = qrcode_image.size
                left = location["x"] + x_left
                top = location["y"] + x_top
                right = left + size["width"]
                bottom = top + size["height"]

                photo_base64 = driver.get_screenshot_as_base64()
                qrcode_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                status = self.ask_scan_qrcode(qrcode_body, username)
                if status != self.SCAN_QRCODE_SUCC:
                    self.logger.error("扫描二维码验证失败")
                    return None

                # 关闭验证框(有时会出现系统繁忙或页面无响应)，重新点击
                driver.switch_to_default_content()
                self._get_element(driver, '//a[@class="alipay-xbox-close"]', self.BY_XPATH).click()
                # 回到主页面，重新点击下载excel账单
                self._get_element(driver, '//a[@seed="actionOther-JDownloadTipT1"]', self.BY_XPATH).click()
                xbox_new_ele = self._get_element(driver, '//div[@class="alipay-xbox-content"]/iframe', self.BY_XPATH)
                if not xbox_new_ele:
                    self.logger.error("获取二维码区域失败:xbox_new_ele")
                    return None

                driver.switch_to_frame(xbox_new_ele)
                # 等待安全验证成功
                check_ele = '//div[@class="ui-form-item ui-form-item-success"]'
                ui.WebDriverWait(driver, 10).until(lambda d: d.find_element_by_xpath(check_ele).is_displayed())

            # 验证成功后，开始下载账单(账单命名不能区分)
            download_btn = self._get_element(driver, '//input[@seed="downloadSubmit-btn"]', self.BY_XPATH)
            if not download_btn:
                self.logger.error("安全检测失败，身份验证失败")
                return None

            download_btn.click()
            sleep(2)  # 等待下载完成，完成后关闭弹出框

            # 采用模拟请求下载账单(会检测是否是机器人-->rdsUa，模拟请求失败)
            page = driver.page_source
            securityId = self.reg_match(page, self.reg_sec_id_download)
            rdsToken = self.reg_match(page, self.reg_form_tk)
            json_ua = driver.execute_script('return json_ua;')
            post_data = {
                "securityId": securityId,
                "_xbox": "true",
                "rdsToken": rdsToken,
                "rdsUa": json_ua
            }
            download_url = 'https://consumeprod.alipay.com/record/download.resource'
            file_content = self.http_request(download_url, method="POST", data=post_data,
                                             headers=self.headers, get_str=False)
            with open('my_record.zip', 'wb') as f:
                f.write(file_content)

            driver.switch_to_default_content()
            self._get_element(driver, '//a[@class="alipay-xbox-close"]', self.BY_XPATH).click()
            self.logger.info("下载交易记录成功，正在解析账单中...")
            # 解析账单信息
            # TODO
            return None
        except TimeoutException:
            self.logger.exception("等待安全验证超时")
            return None
        except Exception:
            self.logger.exception("通过selenium下载文件并解析获取账单信息出错:")
            return None

    def _parse_address_info(self, response):
        """
        解析收货地址
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            address_list_info = []
            add_list = response.xpath('//div[@class="address-add-list-det"]')
            if add_list:
                for add in add_list:
                    privince = add.xpath('.//span[@class="province fn-hide"]/@data-province').extract_first("")
                    city = add.xpath('.//span[@class="city fn-hide"]/@data-city').extract_first("")
                    area = add.xpath('.//span[@class="area fn-hide"]/@data-area').extract_first("")
                    temp_dic = {
                        "receiver_name": add.xpath('.//span[@class="name"]/text()').extract_first("").strip(),
                        "receiver_area": "%s-%s-%s" % (privince, city, area),
                        "receiver_location_detail": add.xpath('.//span[@class="street"]/text()').extract_first(),
                        "receiver_postcode": add.xpath('.//span[@class="code"]/text()').extract_first(),
                        "receiver_mobile": add.xpath('.//span[@class="mobile"]/text()').extract_first("").replace("(", "").replace(")", "").strip(),
                    }
                    address_list_info.append(temp_dic)
            else:
                self.logger.info("暂无收货地址信息")

            item["receiver_addresses"] = address_list_info
            self.logger.info("收货地址获取完成，开始抓取用户信息...")
            yield Request(
                url="https://custweb.alipay.com/account/index.htm",
                meta=meta,
                callback=self._parse_user_info,
                errback=self.err_callback,
                headers=self.headers,
                dont_filter=True
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析收货地址信息异常")

    def _parse_user_info(self, response):
        """
        解析用户信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            nick_name = response.xpath('//*[@id="username"]/text()').extract_first()
            identification_number = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                                   '/tr[1]/td[1]/span[3]/text()').extract_first()
            audit_text = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                        '/tr[1]/td[1]/span[4]/text()').extract_first("")
            email_text = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                        '/tr[2]/td[1]/span/text()').extract_first("")
            mobile = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                    '/tr[3]/td[1]/span/text()').extract_first()
            taobao_username = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                             '/tr[4]/td[1]/text()').extract_first()
            registration_time = response.xpath('//*[@id="account-main"]/div/table/tbody'
                                               '/tr[7]/td[1]/text()').extract_first()

            item["nick_name"] = nick_name
            item["identification_number"] = identification_number
            item["is_real_name"] = ("已认证" in audit_text)
            item["email"] = email_text if "@" in email_text else ""
            item["mobile"] = mobile
            item["taobao_username"] = taobao_username
            item["registration_time"] = registration_time
            self.logger.info("用户信息获取完成，开始抓取银行卡信息...")

            query_url = "https://zht.alipay.com/asset/bindQuery.json?_input_charset=utf-8" \
                        "&providerType=BANK&t={0}".format(get_js_time())
            yield Request(
                url=query_url,
                meta=meta,
                callback=self._parse_bank_list,
                errback=self.err_callback,
                headers=self.headers,
                dont_filter=True
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析用户信息异常")

    def _parse_bank_list(self, response):
        """
        解析银行卡信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            bank_card_list = []
            json_page = json_loads(response.text)
            if json_page.get("stat") == "ok":
                for card in json_page.get("results", []):
                    temp_dic = {
                        "card_name": card.get("providerName", ""),
                        "card_num_last_4": card.get("providerUserName", ""),
                        "card_type": card.get("cardTypeName", "储蓄卡"),
                    }
                    bank_card_list.append(temp_dic)
            else:
                self.logger.error("获取银行卡信息失败")

            item["bank_card"] = bank_card_list
            self.logger.info("银行卡信息获取完成，--->爬虫抓取完成")

            yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析银行卡信息异常")

    def qrcode_login(self, response):
        """
        扫描二维码登录
        :param response:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        try:
            judge_status_by_selenium = True  # 采用selenium判断是否登录成功

            qrcode_info = self._get_qrcode_info()
            if not qrcode_info:
                self.logger.error("获取二维码信息失败")
                yield from self.crawling_failed(username, "获取二维码信息失败")
                return
            self.logger.info("--->需要扫描二维码")
            status = self.ask_scan_qrcode(qrcode_info.get("content"), username)
            if status != self.SCAN_QRCODE_SUCC:
                self.logger.error("扫描二维码失败")
                yield from self.crawling_failed(username, "扫描二维码失败")
                return
            if judge_status_by_selenium:
                # 采用selenium判断是否登录成功
                driver = qrcode_info.get("driver")
                if driver:
                    try:
                        driver.implicitly_wait(2)
                        ui.WebDriverWait(driver, 10).until(
                            lambda d: d.find_element_by_id("J-portal-message").is_displayed())
                        self.logger.info("通过二维码登录成功")
                        driver_cookies = get_cookies_dict_from_webdriver(driver)
                        yield self._get_confirm_request(response=response, driver_cookies=driver_cookies)
                    except TimeoutException:
                        yield from self.error_handle(username, "登录失败，等待跳转超时")
                    except Exception:
                        yield from self.except_handle(username, "扫描二维码登录出错,登录失败")
                    finally:
                        driver.quit()
            else:
                yield from self.__judge_login_status_by_request(response, qrcode_info)
        except CaptchaTimeout:
            yield from self.error_handle(username, "扫描二维码登录超时")
        except Exception:
            yield from self.except_handle(username, "扫描二维码登录出错")

    def __judge_login_status_by_request(self, response, qrcode_info):
        """
        通过模拟请求判断二维码扫描登录是否成功(暂未测试通过,cookies原因)
        :param response:
        :param qrcode_info:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        try:
            # 模拟判断是否登录成功
            check_url = qrcode_info.get("check_url")
            qrcode_headers = self.headers.copy()
            qrcode_headers["Host"] = "securitycore.alipay.com"
            cookies = qrcode_info.get("cookies")
            res_info = self.http_request(check_url, headers=qrcode_headers, cookies=cookies, get_cookies=True)
            page = res_info.get("result")
            json_page = json_loads(self.reg_match(page, self.reg_get_json))
            stat = json_page.get("stat")
            if stat == "ok":
                barcodeStatus = json_page.get("barcodeStatus")
                if barcodeStatus == "waiting":
                    self.logger.info("等待扫描中...")
                elif barcodeStatus == "scanned":
                    self.logger.info("扫描完成，等待确认中...")
                elif barcodeStatus == "confirmed":
                    self.logger.info("确认完成，等待跳转中...")
                    post_data = self.__get_post_info(qrcode_info.get("page"))
                    if not post_data:
                        self.logger.error("获取二维码POST参数失败")
                        yield from self.crawling_failed(username, "获取二维码POST参数失败")
                        return

                    with Session() as session:
                        # spanner_cookie = res_info.get("cookies")
                        ori_cookies = qrcode_info.get("cookies")
                        # ori_cookies.update(spanner_cookie)
                        qrcode_headers["Host"] = "authet15.alipay.com"
                        post_data["ua"] = qrcode_info.get("json_ua")
                        resp = session.post("https://authet15.alipay.com/login/index.htm",
                                            data=post_data, headers=qrcode_headers,
                                            cookies=ori_cookies, verify=False)
                        if resp.status_code == 200:
                            yield self._get_confirm_request(response=response)
                            return

            yield from self.crawling_failed(username, "二维码登录失败")
        except Exception:
            yield from self.except_handle(username, "通过模拟请求二维码登录失败")

    def _get_qrcode_info(self):
        """
        获取二维码相关信息
        :return:
        """
        try:
            driver = self.load_page_by_webdriver(self._start_url_, '//div[@id="J-barcode-container"]')
            driver.implicitly_wait(2)
            driver.maximize_window()
            qrcode_tab = self._get_element(driver, '//li[@data-status="show_qr"]', self.BY_XPATH)
            if not qrcode_tab:
                self.logger.error("页面打开失败")
                return
            qrcode_tab.click()
            # 开始截取二维码图片
            qrcode_image = self._get_element(driver, "J-barcode-container")
            if not qrcode_image:
                self.logger.error("获取二维码图片位置失败")
                return

            location = qrcode_image.location
            size = qrcode_image.size
            left = location["x"]
            top = location["y"]
            right = left + size["width"]
            bottom = top + size["height"]

            photo_base64 = driver.get_screenshot_as_base64()
            qrcode_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))

            page = driver.page_source
            cookies = {cookie.get("name"): cookie.get("value") for cookie in driver.get_cookies()}
            query_url = self.reg_match(page, self.reg_query_url)
            sec_id = self.reg_match(page, self.reg_sec_id)
            check_url = "{query_url}?securityId={sec_id}&_callback=".format(query_url=query_url, sec_id=sec_id)
            json_ua = driver.execute_script('return json_ua;')  # 获取页面UA参数
            check_code_url = self.reg_match(page, self.reg_check_code)
            code_cookies = self.http_request(check_code_url, cookies=cookies,
                                             get_cookies=True, get_str=False).get("cookies")
            cookies.update(code_cookies)
            del cookies["_uab_collina"]
            del cookies["_umdata"]
            re_data = {
                "check_url": check_url,
                "content": qrcode_body,
                "cookies": cookies,
                "json_ua": json_ua,
                "page": page,
                "driver": driver,
            }
            return re_data
        except Exception:
            self.logger.exception("获取二维码相关信息出错:")
            return
        finally:
            # driver.quit()
            pass

    def __get_post_info(self, page):
        """
        获取二维码登录POST数据
        :param page:
        :return:
        """
        try:
            element = html.fromstring(page)
            post_data = {
                "support": self.__get_input_value_by_name(element, "support"),
                "needTransfer": self.__get_input_value_by_name(element, "needTransfer"),
                "CtrlVersion": self.__get_input_value_by_name(element, "CtrlVersion"),
                "loginScene": self.__get_input_value_by_name(element, "loginScene"),
                "redirectType": self.__get_input_value_by_name(element, "redirectType"),
                "personalLoginError": self.__get_input_value_by_name(element, "personalLoginError"),
                "goto": self.__get_input_value_by_name(element, "goto"),
                "errorVM": self.__get_input_value_by_name(element, "errorVM"),
                "sso_hid": self.__get_input_value_by_name(element, "sso_hid"),
                "site": self.__get_input_value_by_name(element, "site"),
                "errorGoto": self.__get_input_value_by_name(element, "errorGoto"),
                "rds_form_token": self.__get_input_value_by_name(element, "rds_form_token"),
                "json_tk": self.__get_input_value_by_name(element, "json_tk"),
                "method": self.__get_input_value_by_name(element, "method"),
                "logonId": self.__get_input_value_by_name(element, "logonId"),
                "superSwitch": self.__get_input_value_by_name(element, "superSwitch"),
                "noActiveX": self.__get_input_value_by_name(element, "noActiveX"),
                "passwordSecurityId": self.__get_input_value_by_name(element, "passwordSecurityId"),
                "qrCodeSecurityId": self.__get_input_value_by_name(element, "qrCodeSecurityId"),
                "password_input": self.__get_input_value_by_name(element, "password_input"),
                "password_rsainput": self.__get_input_value_by_name(element, "password_rsainput"),
                "J_aliedit_using": self.__get_input_value_by_name(element, "J_aliedit_using"),
                "password": self.__get_input_value_by_name(element, "password"),
                "J_aliedit_key_hidn": self.__get_input_value_by_name(element, "J_aliedit_key_hidn"),
                "J_aliedit_uid_hidn": self.__get_input_value_by_name(element, "J_aliedit_uid_hidn"),
                "alieditUid": self.__get_input_value_by_name(element, "alieditUid"),
                "REMOTE_PCID_NAME": self.__get_input_value_by_name(element, "REMOTE_PCID_NAME"),
                "_seaside_gogo_pcid": self.__get_input_value_by_name(element, "_seaside_gogo_pcid"),
                "_seaside_gogo_": self.__get_input_value_by_name(element, "_seaside_gogo_"),
                "_seaside_gogo_p": self.__get_input_value_by_name(element, "_seaside_gogo_p"),
                "J_aliedit_prod_type": self.__get_input_value_by_name(element, "J_aliedit_prod_type"),
                "security_activeX_enabled": self.__get_input_value_by_name(element, "security_activeX_enabled"),
                "J_aliedit_net_info": self.__get_input_value_by_name(element, "J_aliedit_net_info"),
                "checkCode": "",  # 验证码
                "idPrefix": self.__get_input_value_by_name(element, "idPrefix"),
                "preCheckTimes": self.__get_input_value_by_name(element, "preCheckTimes"),
            }
            return post_data
        except Exception:
            self.logger.exception("获取二维码登录post数据出错:")
            return

    def __get_input_value_by_name(self, element, name):
        """
        通过标签名获取值
        :param element:
        :param name:
        :return:
        """
        try:
            if isinstance(element, str):
                element = html.fromstring(element)
            xpath_pattern = '//input[@name="%s"]/@value' % name
            node = element.xpath(xpath_pattern)
            return node[0] if node else None
        except Exception:
            self.logger.exception("通过标签名获取值失败:%s" % name)

    def login(self, response, target_site="ALIPAY", tb_callback=None, **kwargs):
        """
        支付宝账户密码登录
        :param response:
        :param target_site:
        :param tb_callback:用于淘宝登录成功回调函数
        :param kwargs:回调函数参数
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        password = meta["item"]["password"]
        taobao_instance = None
        if target_site == "TAOBAO":
            taobao_instance = kwargs.get("taobao_instance")
            self = taobao_instance

        def set_crawler_status(msg, level="fail"):
            """
            用于设置爬取状态，淘宝登录时，运行实例应为taobao_instance
            :param msg:
            :param level:
            :return:
            """
            instance = taobao_instance if target_site == "TAOBAO" else self

            if level == "fail":
                yield from instance.error_handle(username, msg)
            elif level == "except":
                yield from instance.except_handle(username, msg)

        driver = self.load_page_by_webdriver(self._start_url_, '//div[@id="J-barcode-container"]')
        try:
            driver.maximize_window()
            driver.refresh()
            # 点击密码登录
            login_tab = self._get_element(driver, '//li[@data-status="show_login"]', self.BY_XPATH)
            if not login_tab:
                self.logger.error("获取密码登录框失败")
                yield from set_crawler_status(msg="打开页面失败，登录失败")
            login_tab.click()
            sleep(3)  # 等待页面密码框完全加载完成
            # 采用send_keys的方式会被识别为机器
            action = ActionChains(driver)

            username_input = self._get_element(driver, 'J-input-user')
            action.move_to_element(username_input).click(username_input).perform()
            driver.execute_script('document.getElementById("J-input-user").value="{0}"'.format(username))

            safe_btn = self._get_element(driver, 'safeSignCheck', wait_time=6)
            action.move_to_element(safe_btn).perform()
            driver.execute_script('document.getElementById("safeSignCheck").click();')

            password_input = self._get_element(driver, '//input[@type="password"]', self.BY_XPATH, wait_time=6)
            action.move_to_element(password_input).click(password_input).perform()
            driver.execute_script('document.getElementsByClassName("ui-input i-text")[0].value="{0}"'.format(password))

            # 判断是否需要输入验证码
            check_code_div = self._get_element(driver, '//div[@id="J-checkcode"][@class="ui-form-item"]', self.BY_XPATH)
            if check_code_div:
                self.logger.info("需要输入验证码")
                captcha_image = self._get_element(driver, 'J-checkcode-img')
                location = captcha_image.location
                size = captcha_image.size
                left = location["x"] - 8
                top = location["y"]
                right = left + size["width"]
                bottom = top + size["height"]

                photo_base64 = driver.get_screenshot_as_base64()
                captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                check_code = self.ask_image_captcha(captcha_body, username, file_type=".png")

                self.logger.info("验证码：%s" % check_code)
                ctoken = get_cookies_dict_from_webdriver(driver).get("ctoken", "")
                if not self._verify_captcha_code(username, check_code, ctoken):
                    yield from set_crawler_status(msg="图片验证码错误", level="except")
                    return
                driver.execute_script('document.getElementById("J-input-checkcode").value="{0}"'.format(check_code))
            driver.execute_script('document.getElementById("J-login-btn").click();')

            # 可能存在扫描二维码验证身份或滑动验证
            try:
                ui.WebDriverWait(driver, 5).until(lambda d: d.find_element_by_id("J-userInfo-account-"
                                                                                 "userEmail").is_displayed())
            except TimeoutException:
                # 先判断是否需要验证身份(异地登录)
                if self._get_element(driver, "risk_qrcode_cnt"):
                    verify_ret = self._get_verify_result(driver, username, step_pos="step_login")
                    if not verify_ret.get("status"):
                        yield from set_crawler_status(msg=verify_ret.get("msg", ""))
                        return
                elif self._get_element(driver, "riskackcode"):
                    self.logger.info("--->需要短信验证")
                    security_id = self._get_element(driver, '//input[@name="securityId"]',
                                                    self.BY_XPATH).getAttribute("value")
                    send_url = "https://securitycore.alipay.com/securityAjaxAckCodeSend.json?type=sms&" \
                               "securityId={security_id}&rnd={rnd}&validateProductName=" \
                               "risk_mobile_account&_callback=".format(security_id=security_id, rnd=random())
                    # 将短信验证相关信息保存至ssdb，供Django端使用
                    headers_str = json_dumps({"url": send_url, "security_id": security_id})
                    self.set_sms_captcha_headers_to_ssdb(headers_str, username)
                    sms_code = self.ask_sms_captcha(username)
                    self.logger.info("sms_code:%s" % sms_code)
                    self._get_element(driver, "riskackcode").send_keys(sms_code)
                    self._get_element(driver, '//input[@seed="JSubmit-btn"]', self.BY_XPATH).click()
                    try:
                        # 等待页面跳转
                        ui.WebDriverWait(driver, 5).until(lambda d: d.find_element_by_id("J-userInfo-account-"
                                                                                         "userEmail").is_displayed())
                        self.logger.info("短信验证成功")
                    except TimeoutException:
                        msg = '登录失败:%s' % "短信验证失败"
                        yield from set_crawler_status(msg=msg)
                        return
                else:
                    err_span = self._get_element(driver, '//span[@class="sl-error-text"]', self.BY_XPATH)
                    err_msg = err_span.text if err_span else '未知错误!'
                    msg = '登录失败:%s' % err_msg
                    yield from set_crawler_status(msg=msg)
                    return

            if target_site == "ALIPAY":
                self.logger.info("支付宝账户密码登录成功")
                driver_cookies = get_cookies_dict_from_webdriver(driver)
                yield self._get_confirm_request(response=response, driver_cookies=driver_cookies)
            elif target_site == "TAOBAO":
                # 跳转到淘宝(先点击账户设置，再点击查看我的淘宝)
                self._get_element(driver, '账户设置', self.BY_LINK).click()
                curr_window = driver.current_window_handle
                self._get_element(driver, '查看我的淘宝', self.BY_LINK).click()
                all_windows = driver.window_handles
                for w in all_windows:
                    if curr_window != w:
                        driver.switch_to_window(w)
                        ui.WebDriverWait(driver, 5).until(
                            lambda dr: dr.find_element_by_id("newAccountSecurity").is_displayed())
                        break
                self.logger.info("通过支付宝登录跳转到淘宝成功")
                driver_cookies = get_cookies_dict_from_webdriver(driver)
                taobao_response = kwargs.get("tb_response")
                yield tb_callback(taobao_response, driver_cookies=driver_cookies)
            else:
                yield from self.crawling_failed(username, "登录失败，目标网站不正确")
        except Exception:
            yield from set_crawler_status(msg="登录出错", level="except")
        finally:
            driver.quit()

    def _verify_captcha_code(self, username, captcha_code, ctoken):
        """
        验证图片验证码是否正确
        :param username:
        :param captcha_code:
        :param ctoken:
        :return:
        """
        try:
            verify_url = "https://auth.alipay.com/login/verifyCheckCode.json"
            post_data = {
                "checkCode": captcha_code,
                "idPrefix": "",
                "timestamp": get_js_time(),
                "_input_charset": "utf-8",
                "ctoken": ctoken
            }

            ret_json = self.http_request(verify_url, method="POST", data=post_data, to_json=True)
            self.logger.debug("图片验证码验证结果：%s" % str(ret_json))
            return ret_json.get("checkResult", False)
        except Exception:
            self.logger.exception("验证图片验证码出错")
            return False

    def _get_verify_result(self, driver, username, step_pos="step_login"):
        """
        获取扫描二维码验证结果
        :param driver:
        :param username:
        :param step_pos:出现二维码验证的位置，不同的位置对应不同的操作
        出现位置：登录-step_login,查询账单-step_query,获取账单-step_bill,统计金额-step_amount
        :return:
        """
        msg = "--->{username}:{step}|{result}"
        step = self.STEP_POS_DICT.get(step_pos)
        result = ""
        status = False
        log_msg = msg.format(**{
            "username": username,
            "step": step,
            "result": "需要扫描二维码进行身份验证"
        })
        self.logger.info("%s..." % log_msg)
        try:
            verify_ret = self._scan_qrcode_verify(driver, username)
            if verify_ret:
                # 验证成功
                result = "扫描二维码验证身份成功!"
                status = True
            elif verify_ret is None:
                # 未扫描二维码
                result = "未扫描二维码!"
            else:
                # 验证失败
                result = "扫描二维码验证身份失败!"
        except Exception:
            result = "扫描二维码验证结果出错"
            self.logger.exception(result)
        finally:
            msg_params = {
                "username": username,
                "step": step,
                "result": result
            }
            msg = msg.format(**msg_params)
            self.logger.info(msg)
            ret_data = {
                "status": status,
                "msg": msg
            }
            return ret_data

    def _get_confirm_request(self, response, driver_cookies=None):
        """
        生成确认登录请求
        :param response:
        :param driver_cookies:dirver登录cookies
        :return:
        """
        meta = response.meta
        # username = meta["item"]["username"]
        # self.crawling_login(username)  # 通知授权成功  支付宝抓取过程中可能会存在交互

        if driver_cookies is None:
            temp_cookies = {}
            for c in response.headers.getlist('Set-Cookie', []):
                temp_cookies.update(dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv))
        else:
            temp_cookies = driver_cookies

        meta["cookies"] = temp_cookies
        return Request(
            url="https://my.alipay.com/portal/i.htm",
            meta=meta,
            cookies=temp_cookies,
            callback=self._confirm_login,
            errback=self.err_callback,
            headers=self.headers,
            dont_filter=True
        )

    def _verify_sms_code(self, driver, sms_code, sec_id):
        """
        短信验证
        :param driver:
        :param sms_code:
        :param sec_id:
        :return:
        """
        try:
            data_content = {"risk_mobile_account": {"mobileAckCode": sms_code}}
            format_args = {
                "stime": get_js_time(),
                "data_content": data_content,
                "sec_id": sec_id
            }
            verify_url = "https://securitycore.alipay.com/securityAjaxValidate.json?" \
                         "sendCount=3&dataId={stime}&dataSize=1&dataIndex=0&dataContent" \
                         "={data_content}&_callback=&securityId={sec_id}&orderId=null".format(**format_args)
            page = self.http_request(verify_url, headers=self.headers)
            res_json = json_loads(page[1:-1])
            if res_json.get("stat") == "ok" and res_json.get("info", {}).get("product", [{}])[0].get("validated"):
                self.logger.info("--->短信验证成功")
                return True
            else:
                error_msg = res_json.get("info", {}).get("product", [])[0].get("message")
                self.logger.error(error_msg)
                return False
        except Exception:
            self.logger.exception("短信验证失败")
            return False
