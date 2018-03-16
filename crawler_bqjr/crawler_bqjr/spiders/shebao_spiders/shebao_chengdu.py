# -*- coding: utf-8 -*-

from time import sleep

from bs4 import BeautifulSoup
from requests import get as http_get
from scrapy import FormRequest, Request
from scrapy.spidermiddlewares.httperror import HttpError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import ui

from crawler_bqjr.captcha.recognize_captcha import recognize_captcha_auto
from crawler_bqjr.spider_class import ProxyPhantomjsSpider
from crawler_bqjr.spiders.shebao_spiders.base import ShebaoSpider
from crawler_bqjr.spiders.shebao_spiders.exceptions import CaptcherInvalidException, \
    InvalidWebpageException, LoginException, HttpStatusException
from crawler_bqjr.spiders_settings import SHEBAO_CITY_DICT
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, driver_screenshot_2_bytes


class ShebaoChengduSpider(ShebaoSpider, ProxyPhantomjsSpider):
    name = SHEBAO_CITY_DICT["成都"]
    allowed_domains = ["cdhrss.gov.cn"]
    start_urls = ["http://jypt.cdhrss.gov.cn:8048/portal.php?id=1"]

    custom_settings = {
        'REDIRECT_MAX_TIMES': 1,  # 最多重定向一次，单点登录需求
        'HTTPERROR_ALLOWED_CODES ': [301, 302]  # 对哪些异常返回进行处理
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Referer": "http://jypt.cdhrss.gov.cn:8048/mlogin_action.php?id=1",
        }
        self.base_domain = "http://insurance.cdhrss.gov.cn"
        self.try_times = 11

    def _get_retry_request(self, response):
        meta = response.meta
        meta['try_count'] -= 1
        if meta['try_count'] > 0:
            sleep(3)
            if isinstance(response, Request):
                return response.copy()
            else:
                return response.request.copy()
        else:
            for request in self.error_handle(meta["item"]["username"],
                                             "成都社保---尝试取%s次后仍然无法得到完整数据" % self.try_times,
                                             tell_msg="尝试多次也无法获取数据"):
                return request

    def err_callback(self, failure):
        try:
            if failure.check(HttpError):
                response = failure.value.response
            else:
                self.logger.error(repr(failure))
                response = failure.request
            return self._get_retry_request(response)
        except Exception:
            self.logger.exception("err_callback except")
            return self.get_next_request()

    ##########################################
    # 登录系统
    ##########################################
    def login(self, driver, wait, response):
        meta = response.meta
        try:
            main_div_xpath = "//form[@id='login_form2']"
            driver.get(response.url)

            # 识别验证码
            wait.until(
                lambda dr: dr.find_element_by_xpath(main_div_xpath
                                                    + "//div[@class='qrcode']/img").is_displayed())
            captcha_ele = driver.find_element_by_xpath(main_div_xpath
                                                       + "//div[@class='qrcode']/img")
            location = captcha_ele.location
            size = captcha_ele.size  # 获取验证码的长宽
            left, top = location['x'], location['y']
            photo_base64 = driver.get_screenshot_as_base64()
            temp = driver_screenshot_2_bytes(photo_base64,
                                             (left, top, left + size['width'], top + size['height']))
            captcha_code = recognize_captcha_auto(temp, digits_only=True, del_noise=True)

            if len(captcha_code) != 3:
                raise CaptcherInvalidException()

            _cookies = get_cookies_dict_from_webdriver(driver)

            # 填写input
            input_capimg = driver.find_element_by_xpath(main_div_xpath + "//input[@type='hidden'][1]")
            input_cookiename = driver.find_element_by_xpath(main_div_xpath + "//input[@type='hidden'][2]")
            input_username = driver.find_element_by_xpath(main_div_xpath + "//input[@type='text'][1]")
            input_password = driver.find_element_by_xpath(main_div_xpath + "//input[@type='password'][1]")
            input_qrcode = driver.find_element_by_xpath(main_div_xpath + "//div[@class='qrcode']/input")

            item = meta["item"]
            formdata = {
                input_capimg.get_attribute("name"): input_capimg.get_attribute("value"),
                input_cookiename.get_attribute("name"): input_cookiename.get_attribute("value"),
                input_username.get_attribute("name"): item["username"],
                input_password.get_attribute("name"): item["password"],
                input_qrcode.get_attribute("name"): captcha_code
            }

            return FormRequest("http://jypt.cdhrss.gov.cn:8048/mlogin_action.php?id=1",
                               meta=meta, cookies=_cookies, formdata=formdata, dont_filter=True,
                               callback=self.login_step2, errback=self.err_callback)
        except CaptcherInvalidException:
            raise
        except Exception:
            raise LoginException(response.url)

    ####################################################
    # 单点登录：系统安全措施
    ####################################################
    def login_step2(self, response):
        meta = response.meta
        try:
            if response.status == 200:
                soup = BeautifulSoup(response.body, "lxml")
                username = soup.select_one("input[name='username']")["value"]
                password = soup.select_one("input[name='password']")["value"]
                checkCode = soup.select_one("input[name='checkCode']")["value"]
                redirectUrl = soup.select_one("input[name='redirect_uri']")["value"]
                clientId = soup.select_one("input[name='client_id']")["value"]
                responseType = soup.select_one("input[name='response_type']")["value"]
                password1 = soup.select_one("input[name='password1']")["value"]
                state = soup.select_one("input[name='state']")["value"]
                e = soup.select_one("input[name='e']")["value"]
                m = soup.select_one("input[name='m']")["value"]
                sfz = soup.select_one("input[name='sfz']")["value"]

                submit_url = soup.select_one("#submit_form")["action"]
                formdata = {
                    "username": username,
                    "password": password,
                    "checkCode": checkCode,
                    "redirect_uri": redirectUrl,
                    "client_id": clientId,
                    "response_type": responseType,
                    "password1": password1,
                    "state": state,
                    "e": e,
                    "m": m,
                    "sfz": sfz
                }
                headers = self.headers.copy()
                headers["Host"] = "jypt.cdhrss.gov.cn:8045"
                headers["Origin"] = "http://jypt.cdhrss.gov.cn:8048"
                yield FormRequest(submit_url, headers=headers, formdata=formdata, dont_filter=True,
                                  meta=meta, callback=self.login_step3, errback=self.err_callback)
            else:
                raise HttpStatusException()
        except Exception:
            yield self._get_retry_request(response)

    ########################################################
    # 单点登录：获取token
    ########################################################
    def login_step3(self, response):
        meta = response.meta
        try:
            headers = self.headers.copy()
            headers["Host"] = "insurance.cdhrss.gov.cn"
            resp = http_get(response.url, headers=headers, allow_redirects=False)
            _cookies = resp.cookies
            yield Request(self.base_domain + "/QueryInsuranceInfo.do?flag=1", meta=meta,
                          cookies={c.name: c.value for c in _cookies}, dont_filter=True,
                          callback=self.get_private_info, errback=self.err_callback)
        except Exception:
            yield self._get_retry_request(response)

    #######################################################################
    # 获取参保人信息
    #######################################################################
    def get_private_info(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            # 社保编码
            item["private_no"] = response.xpath("//table[@class='tb5']/tr[1]/td[1]/text()").extract_first()
            # 姓名
            item["real_name"] = response.xpath("//table[@class='tb5']/tr[1]/td[2]/text()").extract_first()
            # 身份证号
            item["identification_number"] = response.xpath("//table[@class='tb5']/tr[1]/td[3]/text()").extract_first()
            # 性别
            item["sex"] = response.xpath("//table[@class='tb5']/tr[2]/td[1]/text()").extract_first()
            # 出生日期
            item["birthday"] = response.xpath("//table[@class='tb5']/tr[2]/td[2]/text()").extract_first()
            # 参加工作时间
            item["date_of_recruitment"] = response.xpath("//table[@class='tb5']/tr[2]/td[3]/text()").extract_first()
            # 参保状态
            item["status"] = response.xpath("//table[@class='tb5']/tr[3]/td[1]/text()").extract_first()
            # 个人身份
            item["identity"] = response.xpath("//table[@class='tb5']/tr[3]/td[2]/text()").extract_first()
            # 经办机构
            item["agency"] = response.xpath("//table[@class='tb5']/tr[3]/td[3]/text()").extract_first()

            yield Request(self.base_domain + "/QueryInsuranceInfo.do?flag=2", dont_filter=True,
                          meta=meta, callback=self.get_insurance_item, errback=self.err_callback)
        except Exception:
            yield item
            yield self._get_retry_request(response)

    #######################################################################
    # 获取保险的主要项目
    #######################################################################
    def get_insurance_item(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            insurance_detail_list = []
            insurance_item_list = response.xpath("//div[@id='box']//table[@class='tb6']/tr[position()>2]")
            for i in range(3, len(insurance_item_list) + 3):
                insurance_item = {
                    "insurance_type": response.xpath("//div[@id='box']//table[@class='tb6']/tr["
                                                     + str(i) + "]/td[2]/text()").extract_first(),
                    "company": response.xpath("//div[@id='box']//table[@class='tb6']/tr["
                                              + str(i) + "]/td[4]/text()").extract_first(),
                    "status": response.xpath("//div[@id='box']//table[@class='tb6']/tr["
                                             + str(i) + "]/td[5]/text()").extract_first(),
                    "detail_url": response.xpath("//div[@id='box']//table[@class='tb6']/tr["
                                                 + str(i) + "]/td[9]/a/@href").extract_first(),
                }
                insurance_detail_list.append(insurance_item)

            item["insurance_detail"] = insurance_detail_list
            request_count = len(insurance_detail_list)
            index = 0
            insurance_sub_item = insurance_detail_list[0]
            detail_url = insurance_sub_item["detail_url"]
            is_health_insurance = (insurance_sub_item["insurance_type"] == "基本医疗保险")

            meta.update({'insurance_detail_list': insurance_detail_list,
                         'index': index,
                         'total': request_count,
                         'is_health_insurance': is_health_insurance,
                         })
            yield Request(self.base_domain + str(detail_url), dont_filter=True, meta=meta,
                          callback=self.get_insurance_detail, errback=self.err_callback)
        except Exception:
            yield item
            yield self._get_retry_request(response)

    #######################################################################
    # 获取五险详情
    #######################################################################
    def get_insurance_detail(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            insurance_detail_list = meta["insurance_detail_list"]
            index = int(meta["index"])
            insurance_item = insurance_detail_list[index]
            index += 1
            # is_health_insurance = ("医疗保险" in insurance_item["insurance_type"])
            is_health_insurance = meta["is_health_insurance"]

            total = int(meta["total"])
            detail_list = []
            insurance_item_list = response.xpath("//div[@id='box']//table/tr[position()>2]")

            base_index = 0 if is_health_insurance else 1
            for i in range(3, len(insurance_item_list) + 3):
                data_item = {
                    "month": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                            + str(base_index + 1) + "]/text()").extract(),
                    "company": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                              + str(base_index + 2) + "]/text()").extract(),
                    "base_fee": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                               + str(base_index + 3) + "]/text()").extract(),
                    "fee": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                          + str(base_index + 4) + "]/text()").extract(),
                    "fee_type": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                               + str(base_index + 5) + "]/text()").extract(),
                    "fee_rate": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                               + str(base_index + 6) + "]/text()").extract(),
                    "fee_date": response.xpath("//div[@id='box']//table/tr[" + str(i) + "]/td["
                                               + str(base_index + 7) + "]/text()").extract(),
                }
                detail_list.append(data_item)

            insurance_item["detail_list"] = detail_list
            if index >= total:
                # 处理完，返回爬取的结果
                yield from self.crawling_done(item)
            else:
                detail_url = insurance_item["detail_url"]
                meta["index"] = index
                yield Request(self.base_domain + str(detail_url), dont_filter=True, meta=meta,
                              callback=self.get_insurance_detail, errback=self.err_callback)
        except Exception:
            yield item
            yield self._get_retry_request(response)

    #######################################################################
    # 爬虫解析主流程
    #######################################################################
    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        try_times = meta.setdefault('try_count', self.try_times)

        driver = self.spider.getdriver(executable_path=self.settings["PHANTOMJS_EXECUTABLE_PATH"], use_proxy=True)
        try:
            driver.set_window_size(1920, 1080)
            driver.start_session(webdriver.DesiredCapabilities.PHANTOMJS)
            wait = ui.WebDriverWait(driver, 20)

            if try_times > 0:
                try:
                    yield self.login(driver, wait, response)
                except (CaptcherInvalidException, InvalidWebpageException, TimeoutException):
                    meta["try_count"] -= 1
                    yield self._get_retry_request(response)
                except Exception:
                    yield item
                    yield from self.except_handle(username, "成都社保---爬取异常：")
            else:
                yield item
                yield from self.error_handle(username,
                                             "成都社保---尝试取%s次后仍然无法得到完整数据" % self.try_times,
                                             tell_msg="尝试多次也无法获取数据")
        finally:
            driver.quit()
