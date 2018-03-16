# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep

from scrapy import Request, FormRequest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import TouchActions
from selenium.webdriver.support import ui

from crawler_bqjr.captcha.tb_slider.slider import TaoBaoLoginSlider
from crawler_bqjr.items.ecommerce_items import TaoBaoItem
from crawler_bqjr.spider_class import ChromeWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.b2c_ecommerce_spiders.alipay import AlipaySpider
from crawler_bqjr.spiders.b2c_ecommerce_spiders.base import EcommerceSpider
from crawler_bqjr.spiders_settings import TAOBAO_DICT
from crawler_bqjr.utils import get_cookies_dict_from_webdriver
from global_utils import json_loads

alipay = AlipaySpider()


class TaobaoSpider(ChromeWebdriverSpider, EcommerceSpider):
    """
    淘宝爬虫
    """

    name = TAOBAO_DICT["淘宝"]
    allowed_domains = ["taobao.com"]
    start_urls = ['https://login.taobao.com/']

    SEX_DICT = {
        "0": "男",
        "1": "女"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=TaoBaoItem, **kwargs)
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch, br",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.04",
        }
        self.order_url = ""

        self.reg_receive_info = re_compile(r'>收货地址：</td>\s*<td>([^<]*)</td>')
        self.reg_transport_style = re_compile(r'>运送方式：</td>\s*<td>([^<]*)<')
        self.reg_logistics_company = re_compile(r'>物流公司：</td>\s*<td>([^<]*)<')
        self.reg_waybill_id = re_compile(r'>运单号：</td>\s*<td>([^<]*)<')
        self.reg_buyer_msg = re_compile(r'id="J_ExistMessage">([^<]*)<')
        self.reg_account_name = re_compile(r'>会员名</span>\s*<span class="[^"]*">([^<]*)<')
        self.reg_email = re_compile(r'>登录邮箱：</span><span class="[^"]*">([^<]*)<')
        self.reg_mobile = re_compile(r'>绑定手机：</span>\s*<span class="[^"]*">([^<]*)<')
        self.reg_id_card = re_compile(r'>18位身份证号：</span>\s*<div class="left">([^<]*)<')

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        request.meta["dont_merge_cookies"] = True
        return request

    def parse(self, response):
        meta = response.meta
        username = meta["item"]["username"]
        # 1:selenium模拟登录,2:扫描二维码登录,3:手机版短信登录,4:从支付宝跳转
        login_type = meta["login_type"]
        try:
            if login_type == self.LOGIN_TYPE.get("account_login"):
                # selenium模拟登录(有时会出现滑块验证)
                yield from self.login(response)
            elif login_type == self.LOGIN_TYPE.get("qrcode_login"):
                # 扫描二维码登录
                yield from self.qrcode_login(response)
            elif login_type == self.LOGIN_TYPE.get("mobile_login"):
                # 手机版短信登录
                yield from self.mobile_login(response)
            elif login_type == self.LOGIN_TYPE.get("jump_login"):
                # 从支付宝跳转
                kwargs = {"tb_response": response, "taobao_instance": self}
                yield from alipay.login(response, target_site="TAOBAO", tb_callback=self._get_account_request, **kwargs)
            else:
                yield from self.crawling_failed(username, "不支持该登录类型")
        except Exception:
            yield from self.except_handle(username, "解析登录页面异常")

    def _get_accounts_info(self, response):
        """
        获取账户信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        cookies = meta["cookies"]
        try:
            birth_year = response.xpath('//select[@id="J_Year"]/option[@selected="selected"]/@value').extract_first()
            birth_mouth = response.xpath('//select[@id="J_Month"]/option[@selected="selected"]/@value').extract_first()
            birth_day = response.xpath('//select[@id="J_Date"]/option[@selected="selected"]/@value').extract_first()
            birth_list = [birth_year, birth_mouth, birth_day]
            accounts = {
                "account": item["username"],
                "type": "淘宝",
                "nick_name": response.xpath('//input[@id="J_uniqueName"]/@value').extract_first(),
                "birthday": "-".join(birth_list) if all(birth_list) else "",
                "gender": self.SEX_DICT.get(response.xpath('//input[@name="_fm.b._0.g"]'
                                                           '[@checked="checked"]/@value').extract_first(), "男"),
            }
            # 获取账户更多信息
            self.logger.info("获取账户更多信息中...")
            more_info = self._get_more_user_info(cookies)
            accounts.update(more_info)
            item["accounts"] = accounts

            self.logger.info("账户信息获取完成，开始获取收货地址信息")

            # 账户信息获取完成，开始获取收货地址信息
            address_url = "https://member1.taobao.com/member/fresh/deliver_address.htm"

            yield Request(
                url=address_url,
                meta=meta,
                callback=self._parse_address_info,
                errback=self.err_callback,
                headers=meta["headers"],
                dont_filter=True
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取账户信息异常")

    def _get_more_user_info(self, cookies):
        """
        获取更多用户信息
        :param cookies:
        :return:
        """
        try:
            sec_url = "https://member1.taobao.com/member/fresh/account_security.htm"
            sec_page = self.http_request(sec_url, cookies=cookies, charset="gb18030")
            if not sec_page:
                self.logger.error("打开更多用户信息页面失败")
                return {}
            sec_page = sec_page.replace("&nbsp;", "")
            sec_info = {
                "taobao_account": self.reg_match(sec_page, self.reg_account_name),
                "mobile": self.reg_match(sec_page, self.reg_mobile),
                "email": self.reg_match(sec_page, self.reg_email)
            }
            # 获取身份认证信息
            certify_url = "https://member1.taobao.com/member/fresh/certify_info.htm"
            certify_page = self.http_request(certify_url, cookies=cookies, charset="gb18030")
            if certify_page:
                sec_info["is_real_name"] = (">已通过实名认证<" in certify_page)
                sec_info["identification_number"] = self.reg_match(certify_page, self.reg_id_card)

            self.logger.info("获取更多用户信息完成")
            return sec_info
        except Exception:
            self.logger.exception("获取更多用户信息出错:")
            return {}

    def _parse_address_info(self, response):
        """
        获取收货地址信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            address_list_info = []
            tr_list = response.xpath('//*[normalize-space(@class)="thead-tbl-address"]')
            if tr_list:
                for tr in tr_list:
                    temp_dic = {
                        "receiver_name": tr.xpath('.//td[1]/text()').extract_first(),
                        "receiver_area": tr.xpath('.//td[2]/text()').extract_first(),
                        "receiver_location_detail": tr.xpath('.//td[3]/text()').extract_first(),
                        "receiver_postcode": tr.xpath('.//td[4]/text()').extract_first(),
                        "receiver_mobile": tr.xpath('.//td[5]/text()').extract_first("").replace("\n", "").replace("\t", "").strip(),
                    }
                    address_list_info.append(temp_dic)
            else:
                self.logger.info("暂无收货地址信息")

            item["receiver_addresses"] = address_list_info
            self.logger.info(address_list_info)
            self.order_url = "https://buyertrade.taobao.com/trade/itemlist/asyncBought.htm?" \
                             "action=itemlist/BoughtQueryAction&event_submit_do_query=1&_input_charset=utf8"
            query_req = self.__generate_order_request(meta)
            if query_req:
                yield query_req
            else:
                yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析收货地址信息异常")

    def __generate_order_request(self, meta, page_num=1, page_size=15):
        """
        生成查询订单请求
        :param meta:
        :param page_num:
        :param page_size:
        :return:
        """
        try:
            post_data = {
                "buyerNick": "",
                "dateBegin": "0",
                "dateEnd": "0",
                "lastStartRow": "",
                "logisticsService": "",
                "options": "0",
                "orderStatus": "",
                "pageNum": str(page_num),
                "pageSize": str(page_size),
                "queryBizType": "",
                "queryOrder": "desc",
                "rateStatus": "",
                "refund": "",
                "sellerNick": "",
                "prePageNo": "1",
            }
            return FormRequest(
                url=self.order_url,
                meta=meta,
                formdata=post_data,
                callback=self._parse_order_info,
                errback=self.err_callback,
                headers=meta["headers"],
                dont_filter=True
            )
        except Exception:
            self.logger.exception("生成查询订单请求异常:")
            return None

    def _parse_order_info(self, response):
        """
        解析订单信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        orders = item.get("orders")
        if not orders:
            orders = []
        try:
            json_page = json_loads(response.text)
            if not json_page.get("error"):
                page = json_page.get("page")
                curr_page = page.get("currentPage")
                total_page = page.get("totalPage")
                # total_num = page.get("totalNumber")
                main_orders = json_page.get("mainOrders", [])
                for one in main_orders:
                    temp_dic = {}
                    order_info = one.get("orderInfo", {})
                    pay_info = one.get("payInfo", {})
                    temp_dic["b2c"] = order_info.get("b2C")
                    temp_dic["order_no"] = order_info.get("id")
                    temp_dic["create_time"] = order_info.get("createTime")
                    temp_dic["order_fee"] = pay_info.get("actualFee")
                    temp_dic["post_type"] = pay_info.get("postType", "")
                    temp_dic["shop_name"] = one.get("seller", {}).get("shopName")
                    temp_dic["status"] = one.get("statusInfo", {}).get("text")
                    # 获取子订单
                    sub_orders = one.get("subOrders", [])
                    sub_order_list = []
                    for sub_order in sub_orders:
                        temp_item = {}
                        # 商品名
                        goods_name = sub_order.get("itemInfo", {}).get("title")
                        temp_item["goods_name"] = goods_name
                        # 数量
                        quantity = sub_order.get("quantity")
                        temp_item["quantity"] = quantity
                        sub_order_list.append(temp_item)

                    temp_dic["sub_orders"] = sub_order_list

                    # 获取商品物流信息
                    detail_url = "https://tradearchive.taobao.com/trade/detail/" \
                                 "trade_item_detail.htm?bizOrderId={id}".format(id=temp_dic.get("order_no"))
                    logistics = self._get_logistics_info(detail_url, cookies=meta["cookies"])
                    temp_dic["logistics"] = logistics

                    orders.append(temp_dic)
                item["orders"] = orders
                if int(curr_page) != int(total_page) + 1:
                    query_req = self.__generate_order_request(meta, page_num=int(curr_page) + 1)
                    if query_req:
                        yield query_req
                    else:
                        yield item
                        yield from self.crawling_failed(item["username"], "生成请求订单信息失败")
                else:
                    self.logger.info("---->所有信息抓取完成")
                    yield from self.crawling_done(item)
            else:
                yield item
                yield from self.crawling_failed(item["username"], "请求订单信息失败")
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析订单信息异常")

    def _get_logistics_info(self, detail_url, cookies):
        """
        获取商品物流信息
        :param detail_url:
        :param cookies:
        :return:
        """
        try:
            logistics_info = {}
            detail_page = self.http_request(detail_url, cookies=cookies, charset="gb18030")
            if not detail_page:
                return {}
            recrive_str = self.reg_match(detail_page, self.reg_receive_info)
            recrive_str = self.reg_blank.sub(' ', recrive_str or '').strip()
            recrive_list = recrive_str.split("，")
            recrive_list_len = len(recrive_list)
            if recrive_list_len == 5:
                recrive_list.pop(2)
            elif recrive_list_len == 4:
                logistics_info["name"] = recrive_list[0].strip()
                logistics_info["phone"] = recrive_list[1].strip()
                logistics_info["address_area"] = recrive_list[2].strip().rsplit(" ", maxsplit=1)[0].replace(" ", "/")
                logistics_info["address_detail"] = recrive_list[2].strip().rsplit(" ", maxsplit=1)[-1]
                logistics_info["postcode"] = recrive_list[3].strip()
            logistics_info["transport_style"] = self.reg_match(detail_page, self.reg_transport_style)
            logistics_info["logistics_company"] = self.reg_match(detail_page, self.reg_logistics_company)
            logistics_info["waybill_id"] = self.reg_match(detail_page, self.reg_waybill_id)
            logistics_info["buyer_msg"] = self.reg_match(detail_page, self.reg_buyer_msg)

            return logistics_info
        except Exception:
            self.logger.exception("获取商品物流信息出错:%s" % detail_url)
            return {}

    def _agreement(self, driver):
        """
        同意淘宝协议
        :param driver:
        :return:
        """
        try:
            self._get_element(driver, "J_AgreementBtn").click()
            return True
        except Exception:
            return False

    def _check_identify(self, driver, username):
        """
        验证身份
        :param driver:
        :return:
        """
        try:
            iframe = self._get_element(driver, '//div[@class="login-check-left"]/iframe', by=self.BY_XPATH)
            driver.switch_to.frame(iframe)

            other_btn_1 = self._get_element(driver, '//a[@class="ui-form-other"]', self.BY_XPATH)
            other_btn_2 = self._get_element(driver, 'otherValidator')
            other_btn = other_btn_1 or other_btn_2
            if not other_btn:
                self.logger.error("获取验证btn失败")
                return False
            other_btn.click()
            check_ele = self._get_element(driver, '//ol[@class="select-strategy"]/li[2]/a', self.BY_XPATH)
            if not check_ele:
                return False
            check_ele.click()
            getcode_btn = self._get_element(driver, "J_GetCode")
            if not getcode_btn:
                return False
            getcode_btn.click()
            sms_code = self.ask_sms_captcha(username)
            self.logger.info("短信验证码：%s" % sms_code)
            self._get_element(driver, "J_Phone_Checkcode").send_keys(sms_code)
            submit_btn = self._get_element(driver, '//input[@class="ui-button ui-button-lorange"]', self.BY_XPATH)
            if not submit_btn:
                return False
            submit_btn.click()
            if self._get_element(driver, "J_GetCode"):
                self.logger.error("短信验证码错误，验证身份失败")
                return False
            driver.get("https://i.taobao.com/my_taobao.htm")  # 打开个人中心
            return True
        except Exception:
            self.logger.exception("淘宝验证身份出错")
            return False

    def qrcode_login(self, response):
        """
        扫描二维码登录(前端轮询)
        :param response:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        try:
            cookies = self.ask_qrcode_cookies(username, account_type="taobao")
            # self.logger.debug("cookies:%s" % str(cookies))
            yield self._get_account_request(response, driver_cookies=cookies)
        except CaptchaTimeout:
            yield from self.error_handle(username, "扫描二维码登录超时")
        except Exception:
            yield from self.except_handle(username, "通过扫描二维码登录出错")

    def mobile_login(self, response):
        """
        淘宝手机版登录
        :param response:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        login_url = "https://login.m.taobao.com/msg_login.htm"
        driver = self.load_page_by_webdriver(login_url, '//span[@id="getCheckcode"]')
        try:
            driver.maximize_window()
            username_input = self._get_element(driver, 'username')
            if not username_input:
                self.logger.error("获取用户名数据框失败")
                yield from self.crawling_failed(username, "打开登录页面失败，登录失败")
                return
            username_input.send_keys(username)
            sleep(1)
            sms_btn = self._get_element(driver, 'getCheckcode')
            if not sms_btn:
                self.logger.error("获取发送短信按钮失败")
                yield from self.crawling_failed(username, "打开登录页面失败，登录失败")
                return
            action = TouchActions(driver)  # 移动端
            action.tap(sms_btn).perform()
            page = driver.page_source
            if "请点击滑块上的圆圈完成验证" in page:
                self.logger.info("需要点击圆圈验证")
                if not self._click_circle_verify(driver, username):
                    self.logger.error("点击圆圈验证失败")
                    yield from self.crawling_failed(username, "点击圆圈验证失败，登录失败")
                    return
            self.logger.info("需要输入手机短信验证码登录淘宝")
            sms_code = self.ask_sms_captcha(username)
            self.logger.info("短信验证码:%s" % sms_code)
            self._get_element(driver, 'msgCheckCode', self.BY_NAME).send_keys(sms_code)
            login_btn = self._get_element(driver, 'btn-submit')
            driver.execute_script('document.getElementById("btn-submit").click();')
            self.logger.info("正在登录中...")
            alert_dialog = self._get_element(driver, '//div[@class="km-dialog-content"]', self.BY_XPATH)
            if alert_dialog:
                msg = "短信登录失败：%s" % alert_dialog.text
                self.logger.error(msg)
                self._get_element(driver, 'km-dialog-btn', self.BY_CLASS).click()
                yield from self.crawling_failed(username, msg)
                return
            ui.WebDriverWait(driver, 10).until(lambda d: d.find_element_by_id("J_myNick").is_displayed())
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')  # 滚动到页面底部
            self._get_element(driver, '电脑版', self.BY_LINK).click()  # 跳转到电脑版
            driver.implicitly_wait(1)

            self.logger.info("通过短信登录淘宝手机端成功")
            driver_cookies = get_cookies_dict_from_webdriver(driver)
            yield self._get_account_request(response, driver_cookies=driver_cookies)
        except TimeoutException:
            yield from self.except_handle(username, "淘宝手机版登录失败")
        except Exception:
            self.logger.exception("淘宝手机版登录出错")
            return False
        finally:
            driver.quit()

    def _click_circle_verify(self, driver, username):
        """
        淘宝手机端登录点击圆圈验证
        :param driver:
        :param username:
        :return:
        """
        try:
            # TODO
            return True
        except Exception:
            self.logger.exception("淘宝手机端登录点击圆圈验证出错")
            return False

    def login(self, response, target_site="TAOBAO", alipay_callback=None, **kwargs):
        """
        淘宝账号密码登录
        :param response:
        :param target_site:
        :param alipay_callback:支付宝登录回调函数
        :param kwargs:回调函数参数
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        password = meta["item"]["username"]
        driver = self.load_page_by_webdriver(self._start_url_, '//div[@id="J_QRCodeLogin"]')
        try:
            driver.implicitly_wait(2)
            driver.maximize_window()
            sta_tab = self._get_element(driver, "J_Quick2Static")
            if not sta_tab:
                self.logger.error("打开登录页面失败，登录失败")
                yield from self.crawling_failed(username, "打开登录页面失败，登录失败")
                return
            sta_tab.click()
            user_input = self._get_element(driver, "TPL_username_1")
            if not user_input:
                self.logger.error("打开登录页面失败，登录失败")
                yield from self.crawling_failed(username, "打开登录页面失败，登录失败")
                return
            driver.execute_script('''document.getElementById("TPL_username_1").value = "%s";''' % username)
            self._get_element(driver, "TPL_password_1").click()
            user_input.click()
            driver.execute_script('''document.getElementById("TPL_password_1").value = "%s";''' % password)
            check_url = "https://login.taobao.com/member/request_nick_check.do?_input_charset=utf-8"
            ua_json = driver.execute_script('return window["_n"];')
            post_data = {"username": username, "ua": ua_json}
            re_json = self.http_request(check_url, method="POST", data=post_data, to_json=True)
            needcode = re_json.get("needcode", False)
            wait = ui.WebDriverWait(driver, 10)
            if needcode:
                self.logger.info("淘宝登录需要滑块验证")
                success_xpath = '//*[@id="nc_1_n1z"][@class="nc_iconfont btn_ok"]'
                pid = driver.service.process.pid
                with TaoBaoLoginSlider(driver=driver, wait=wait, logger=self.logger, pid=pid) as taobao_slider:
                    check_result = taobao_slider.drag_login_slider(success_xpath=success_xpath)
                    if not check_result:
                        self.logger.error("滑块验证失败，登录失败")
                        yield from self.crawling_failed(username, "滑块验证失败，登录失败")
                        return
                # 重新填入密码
                driver.execute_script('''document.getElementById("TPL_password_1").value = "%s";''' % password)
            self._get_element(driver, "J_SubmitStatic").click()
            sleep(1)
            error_element = self._get_element(driver, 'J_Message')
            if error_element:
                err_msg = error_element.text
                err_msg = err_msg.replace("\n", "") if err_msg else "用户名或密码错误"
                msg = "登录失败:%s" % err_msg
                self.logger.info(msg)
                yield from self.crawling_failed(username, msg)
                return
            if self._get_element(driver, '//*[@class="login-agreement"]', self.BY_XPATH):
                # 同意淘宝协议
                self.logger.info("--->需要同意淘宝协议")
                if not self._agreement(driver):
                    yield from self.crawling_failed(username, "同意淘宝协议失败")
                    return
            if self._get_element(driver, '//div[@class="login-check-left"]', self.BY_XPATH):
                # 身份验证
                self.logger.info("--->需要身份验证,采用短信验证")
                if not self._check_identify(driver, username):
                    yield from self.crawling_failed(username, "身份验证失败")
                    return
                self.logger.info("身份验证成功")
            if self._get_element(driver, 'J_MyPrivilegeInfo'):
                # 登录成功，按需跳转
                self.logger.info("淘宝登录成功,正在跳转中...")
                if target_site == "TAOBAO":
                    driver.get("https://member1.taobao.com/member/fresh/deliver_address.htm")
                    driver_cookies = get_cookies_dict_from_webdriver(driver)
                    yield self._get_account_request(response, driver_cookies=driver_cookies)
                elif target_site == "ALIPAY":
                    ali_ele = self._get_element(driver, '//li[@id="J_MyAlipayInfo"]/span/a', self.BY_XPATH)
                    if ali_ele:
                        curr_window = driver.current_window_handle
                        ali_ele.click()  # wait
                        all_windows = driver.window_handles
                        for w in all_windows:
                            if curr_window != w:
                                driver.switch_to_window(w)
                                wait.until(lambda dr: dr.find_element_by_id("J-userInfo-account"
                                                                            "-userEmail").is_displayed())
                                break
                    driver_cookies = get_cookies_dict_from_webdriver(driver)
                    alipay_response = kwargs.get("alipay_response")
                    yield alipay_callback(response=alipay_response, driver_cookies=driver_cookies)
                else:
                    yield from self.crawling_failed(username, "目标网站不正确")
                return
            yield from self.crawling_failed(username, "登录失败")
        except Exception:
            yield from self.except_handle(username, "登录出错")
        finally:
            driver.quit()

    def _get_account_request(self, response, driver_cookies=None):
        """
        生成获取用户信息请求
        :param response:
        :param driver_cookies:从支付宝登录时的cookies
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]

        # 通知授权成功
        self.crawling_login(username)

        self.logger.info("开始获取账户信息中...")
        base_info_url = "https://i.taobao.com/user/baseInfoSet.htm"
        if driver_cookies is None:
            temp_cookies = {}
            for c in response.headers.getlist('Set-Cookie', []):
                temp_cookies.update(dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv))
        else:
            temp_cookies = driver_cookies
        meta["cookies"] = temp_cookies
        cookies_dict = {
            "Cookie": ';'.join(["{0}={1}".format(k, v) for k, v in temp_cookies.items()])
        }
        my_headers = self.headers.copy()
        my_headers["Referer"] = "https://i.taobao.com/my_taobao.htm"
        my_headers.update(cookies_dict)
        meta["headers"] = my_headers

        return Request(
            url=base_info_url,
            meta=meta,
            callback=self._get_accounts_info,
            errback=self.err_callback,
            headers=my_headers,
            dont_filter=True
        )
