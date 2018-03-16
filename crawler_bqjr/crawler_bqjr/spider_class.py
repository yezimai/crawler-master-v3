# -*- coding: utf-8 -*-

from base64 import b64encode
from hashlib import md5
from io import IOBase
from os import path as os_path
from platform import system as get_os
from random import randint
from time import sleep, time

from scrapy import Spider, Request
from scrapy.http import Response
from scrapy.utils.project import get_project_settings
from scrapy.spidermiddlewares.httperror import HttpError
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Ie, Chrome, PhantomJS, ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait

from crawler_bqjr.captcha.recognize_captcha import BadCaptchaFormat
from crawler_bqjr.find_name_words import get_name_words
from crawler_bqjr.mail import send_mail_2_admin
from crawler_bqjr.settings import DO_NOTHING_URL, HEADLESS_CHROME_PATH, LOG_FILE
from crawler_bqjr.spiders_settings import SpiderName_2_AccountType_DICT, DATA_EXPIRE_TIME, \
    ACCOUNT_CRAWLING_QUEUE_SSDB_SUFFIX, ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX, ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX, ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX, ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX, ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_DESCRIBE_SSDB_SUFFIX, ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_QRCODE_COOKIES_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_NAME_IDCARD_SMS_SSDB_SUFFIX
from crawler_bqjr.utils import get_one_ua
from crawler_bqjr.webbrowser_driver import PhantomjsWebDriverFactory
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads as data_loads, json_dumps as data_dumps
from proxy_api.proxy_utils import ProxyApi


class ScrapyCustomSettingsMeta(type):
    """
    可继承custom_settings类属性的Scrapy爬虫元类
    """

    def __init__(cls, classname, superclasses, attributedict):
        super().__init__(classname, superclasses, attributedict)
        _custom_settings = cls.custom_settings
        if isinstance(_custom_settings, dict):
            for super_class in superclasses:
                if hasattr(super_class, "custom_settings") and super_class.custom_settings:
                    _custom_settings.update(super_class.custom_settings)


class IndependentLogMeta(ScrapyCustomSettingsMeta):
    """
    以爬虫类名作为日志文件名的Scrapy爬虫元类
    """

    def __init__(cls, classname, superclasses, attributedict):
        super().__init__(classname, superclasses, attributedict)
        if hasattr(cls, "start_urls"):  # 用这个属性判断是否为最终爬虫类
            if "custom_settings" not in cls.__dict__:
                setattr(cls, "custom_settings", cls.custom_settings.copy())

            if isinstance(LOG_FILE, str):
                log_file = os_path.join(os_path.dirname(LOG_FILE), classname + '.log')
            else:
                log_file = LOG_FILE
            cls.__dict__["custom_settings"].setdefault("LOG_FILE", log_file)


class PhantomjsRequestSpider(Spider):
    """
        使用Phantomjs自动加载每一个页面请求
    """

    def __init__(self, *args, phantomjs_finish_xpath=None, **kwargs):
        """
        :param name: 爬虫名字
        :param phantomjs_finish_xpath: 判断页面是否加载完成对xpath
        """
        super().__init__(*args, **kwargs)
        self.phantomjs_finish_xpath = phantomjs_finish_xpath


class LoggingClosedSpider(Spider):
    """
        爬虫关闭时记录日志
    """

    def closed(self, reason):
        msg = "%s closed with reason: [%s]" % (self.name, reason)
        self.logger.critical(msg)
        return msg


class NoticeClosedSpider(LoggingClosedSpider):
    """
        爬虫关闭时发送邮件通知
    """

    def closed(self, reason):
        msg = super().closed(reason)
        send_mail_2_admin("爬虫关闭", msg)


class NoticeChangeSpider(Spider):
    """
        提供一个函数，在页面变化时发送邮件通知
    """

    def notice_change(self, msg):
        self.logger.critical(msg)
        send_mail_2_admin(self.name + " 页面变化", msg)


class WebdriverSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = get_project_settings()
        self.check_wait_time = settings.get("WEBDRIVER_CHECK_WAIT_TIME", 0.1)
        self.page_load_timeout = settings['WEBDRIVER_LOAD_TIMEOUT']
        self.dcap = {}

    def wait_xpath(self, driver, xpath, raise_timeout=False, timeout=30, displayed=False):
        wait = WebDriverWait(driver, timeout, poll_frequency=self.check_wait_time)
        try:
            wait.until(lambda dr: dr.find_element_by_xpath(xpath))
            if displayed:
                wait.until(lambda dr: dr.find_element_by_xpath(xpath).is_displayed())
        except TimeoutException:
            if not raise_timeout:
                pass
            else:
                raise

    def get_driver(self, dcap):
        raise NotImplementedError

    def load_page_by_webdriver(self, url, finish_xpath=None):
        dcap = self.dcap.copy()

        driver = self.get_driver(dcap)
        driver.set_page_load_timeout(self.page_load_timeout)
        driver.set_script_timeout(self.page_load_timeout)
        for i in range(2):
            try:
                driver.get(url)
                if finish_xpath:
                    self.wait_xpath(driver, finish_xpath)
            except Exception:
                self.logger.exception("")
                continue
            else:
                break

        return driver


class PhantomJSWebdriverSpider(WebdriverSpider):
    """
        提供一个函数，返回Phantomjs执行页面请求的webdriver
    """

    def __init__(self, *args, load_images=True, **kwargs):
        super().__init__(*args, **kwargs)
        settings = get_project_settings()
        self.executable_path = settings['PHANTOMJS_EXECUTABLE_PATH']
        self.service_args = ["--load-images=" + str(load_images).lower(),
                             "--disk-cache=false"]
        self.dcap = DesiredCapabilities.PHANTOMJS.copy()
        self.dcap["phantomjs.page.settings.resourceTimeout"] = self.page_load_timeout * 1000  # 单位是毫秒

    def get_driver(self, dcap):
        dcap["phantomjs.page.settings.userAgent"] = get_one_ua()
        return PhantomJS(executable_path=self.executable_path,
                         service_args=self.service_args,
                         desired_capabilities=dcap)


class IEWebdriverSpider(WebdriverSpider):
    """
        提供一个函数，返回IE执行页面请求的webdriver
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = get_project_settings()
        self.executable_path = settings['IE_EXECUTABLE_PATH']
        self.dcap = DesiredCapabilities.INTERNETEXPLORER.copy()

    def get_driver(self, dcap):
        return Ie(executable_path=self.executable_path, capabilities=dcap)


class IE233WebdriverSpider(IEWebdriverSpider):
    """
        提供一个函数，返回IE执行页面请求的webdriver
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = get_project_settings()
        self.executable_path = settings['IE_EXECUTABLE_233_PATH']


class ChromeWebdriverSpider(WebdriverSpider):
    """
        提供一个函数，返回IE执行页面请求的webdriver
    """

    def __init__(self, *args, load_images=True, **kwargs):
        super().__init__(*args, **kwargs)
        settings = get_project_settings()
        self.executable_path = settings['CHROME_EXECUTABLE_PATH']
        self.dcap = DesiredCapabilities.CHROME.copy()
        self.load_images = load_images

    def get_driver(self, dcap, binary_location=None):
        options = ChromeOptions()
        if not self.load_images:
            options.add_argument('disable-images')
        if binary_location is not None:
            options.binary_location = binary_location

        return Chrome(executable_path=self.executable_path, desired_capabilities=dcap,
                      chrome_options=options)


class HeadlessChromeWebdriverSpider(ChromeWebdriverSpider):
    def __init__(self, *args, load_images=True, **kwargs):
        super().__init__(*args, load_images=load_images, **kwargs)
        options = ChromeOptions()
        if 'Windows' == get_os():
            options.binary_location = HEADLESS_CHROME_PATH
        options.add_argument('no-sandbox')
        options.add_argument('headless')
        options.add_argument('disable-gpu')
        if not load_images:
            options.add_argument('disable-images')
        self.options = options

    def get_driver(self, dcap, binary_location=HEADLESS_CHROME_PATH):
        return Chrome(executable_path=self.executable_path,
                      desired_capabilities=dcap, chrome_options=self.options)


class NameSearchSpider(NoticeClosedSpider):
    """
        使用中文姓名进行搜索的爬虫
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name_words = get_name_words()

    def __getattr__(self, name):
        return getattr(self.name_words, name)


class RecordSearchedSpider(Spider):
    """
        需要记录搜索过关键字的爬虫
    """

    def __init__(self, *args, ssdb_hset_for_record, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssdb_conn = get_ssdb_conn()
        self.__ssdb_hset_name = ssdb_hset_for_record

    def is_search_name_exists(self, search_name):
        try:
            return self.ssdb_conn.hexists(self.__ssdb_hset_name, search_name)
        except Exception:
            return True

    def record_search_name(self, search_name):
        try:
            self.ssdb_conn.hset(self.__ssdb_hset_name, search_name, "")
        except Exception:
            return


class ProxySpider(Spider):
    """
        提供一个接口，可以为每个请求设置代理
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxy_api = ProxyApi()
        self.proxy = self.proxy_api.get_proxy_one()

    def add_proxy(self, request):
        #  设置代理
        request.meta["proxy"] = "http://" + self.proxy

    def add_proxy_for_https(self, request):
        #  设置代理
        request.meta["proxy"] = "https://" + self.proxy

    def change_proxy(self):
        self.proxy = self.proxy_api.get_proxy_one()

    def err_callback(self, failure):
        self.logger.warning(repr(failure))
        self.change_proxy()

        try:
            request = failure.request
            self.add_proxy(request)
            return request
        except Exception:
            self.logger.exception("err_callback except")


###########################################
# 走动态代理的phantomjs爬虫
###########################################
class ProxyPhantomjsSpider(ProxySpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PROXY_USE_COUNT_SSDB_PREFIX = "ROXY_USE_COUNT-"
        self.builder = None
        self.proxy = self.proxy_api.get_proxy_one()
        self.use_count = 1
        self.ssdb_conn = get_ssdb_conn()
        self.set_ip_proxy_expire_till_tommorrow(1)
        self.logger.info("获取代理，代理ip:%s" % self.proxy)

    def __get_builder__(self, executable_path, use_proxy, browser_type=None):
        self.builder = PhantomjsWebDriverFactory.new_builder(browser_type=browser_type)

        if use_proxy:
            return self.builder.set_log_path("ghostdriver.log") \
                .set_implicitly_wait(10) \
                .set_page_load_timeout(160) \
                .set_script_timeout(100) \
                .use_proxy(self.proxy) \
                .build(executable_path)
        else:
            return self.builder.set_log_path("ghostdriver.log") \
                .set_implicitly_wait(10) \
                .set_page_load_timeout(160) \
                .set_script_timeout(100) \
                .build(executable_path)

    def getdriver(self, executable_path, browser_type=None, use_proxy=False, change_proxy=False):
        if use_proxy and change_proxy:
            self.proxy = self.proxy_api.get_proxy_one()
            self.set_ip_proxy_expire_till_tommorrow(1)
            self.logger.info("切换代理，代理ip:%s" % self.proxy)
        driver = self.__get_builder__(executable_path, use_proxy, browser_type)
        return driver

    def increase_ip_use_count(self):
        self.ssdb_conn.incr(self.PROXY_USE_COUNT_SSDB_PREFIX + self.proxy, 1)

    def set_ip_proxy_expire_till_tommorrow(self, count):
        self.ssdb_conn.setx(self.PROXY_USE_COUNT_SSDB_PREFIX + self.proxy, count, 86400)

    def check_count(self):
        ip_use_count = int(self.ssdb_conn.get(self.PROXY_USE_COUNT_SSDB_PREFIX + self.proxy))
        return ip_use_count == 6


###########################################
# 不走动态代理的phantomjs爬虫
###########################################
class WebBrowserSpider(Spider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.builder = None

    def __get_builder__(self, executable_path, browser_type=None):
        self.builder = PhantomjsWebDriverFactory.new_builder(browser_type=browser_type)
        return self.builder.set_log_path("ghostdriver.log") \
            .set_implicitly_wait(10) \
            .set_page_load_timeout(160) \
            .set_script_timeout(100) \
            .build(executable_path)

    def getdriver(self, executable_path, browser_type=None):
        driver = self.__get_builder__(executable_path, browser_type)
        return driver

    def start_new_session(self):
        self.builder.start_new_session()

    def err_callback(self, failure):
        self.logger.warning(repr(failure))

        try:
            request = failure.request
            return request
        except Exception:
            self.logger.exception("err_callback except")


######################################
# 验证码输入超时异常
######################################
class CaptchaTimeout(TimeoutError):
    pass


class AccountSpider(NoticeClosedSpider, metaclass=IndependentLogMeta):
    """
    使用账号爬取数据的爬虫
    """

    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, item_class, **kwargs):
        super().__init__(*args, **kwargs)
        self._start_url_ = self.start_urls[0]
        self.queue_name = self.name + ACCOUNT_CRAWLING_QUEUE_SSDB_SUFFIX
        self.ssdb_conn = get_ssdb_conn()
        self.RETRY_TIMES = 600
        self.RETRY_SLEEP = 0.5
        self.SSDB_RETRY = 2
        self.ItemClass = item_class

    def get_account_request(self, account_info):
        username = account_info["username"]
        password = account_info["password"]
        customer_id = account_info.get("customer_id")
        serial_no = account_info.get("serial_no")
        self.logger.critical("Get account: (username:%s, password:%s, customer_id:%s, serial_no:%s)" %
                             (username, password, customer_id, serial_no))

        request = Request(self._start_url_, self.parse, dont_filter=True, errback=self.err_callback)

        item = self.ItemClass()
        item["username"] = username
        item["password"] = password
        item["customer_id"] = customer_id
        item["serial_no"] = serial_no
        item["is_complete"] = False
        request.meta["item"] = item

        return request

    def get_next_request(self):
        # 由web服务向SSDB写入账号，然后爬虫从SSDB读取账号
        # 这种设计虽然耦合性比较大，但效率高要一些
        try:
            info = self.ssdb_conn.qpop_front(self.queue_name)

            if info is not None:
                info = data_loads(info)
                return self.get_account_request(info)
            else:
                # 需要一个空爬的Request，不能sleep，否则就一直阻塞了
                return Request(DO_NOTHING_URL, self.do_nothing,
                               errback=self.do_nothing, dont_filter=True)
        except Exception:
            return Request(DO_NOTHING_URL, self.do_nothing,
                           errback=self.do_nothing, dont_filter=True)

    def start_requests(self):
        yield self.get_next_request()

    def do_nothing(self, response):
        sleep(1)
        yield self.get_next_request()

    def parse_logout(self, arg):
        if isinstance(arg, Response):
            self.logger.debug("logout: " + arg.text)
        else:
            self.logger.error("logout: " + repr(arg))

    def err_callback(self, failure):
        self.logger.error(repr(failure))

        try:
            request = failure.request
            meta = request.meta
            retry_count = meta.setdefault("err_callback_retry", 0)
            if retry_count < 2:
                sleep(1)
                new_request = request.copy()
                new_request.meta["err_callback_retry"] += 1

                if failure.check(HttpError):
                    response = failure.value.response
                    self.logger.info("当前请求url：{0} 异常，状态码为：{1}，重试次数：{2}"
                                     "".format(response.url, response.status, retry_count + 1))

                return new_request
            else:
                item = meta["item"]
                return list(self.error_handle(item["username"], "err_callback"))
        except Exception:
            self.logger.exception("err_callback except")
            return self.get_next_request()

    def _set_crawling_status(self, username, status, tell_msg="",
                             logout_request=None, tell_data=""):
        if logout_request is not None:
            yield logout_request

        account_type = SpiderName_2_AccountType_DICT[self.name]
        ssdb_conn = self.ssdb_conn

        for i in range(self.SSDB_RETRY):
            try:
                if tell_msg:
                    ssdb_conn.setx(username + ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX + account_type,
                                   tell_msg, DATA_EXPIRE_TIME)
                if tell_data:
                    tell_data_key = md5(tell_data.encode()).hexdigest()
                    ssdb_conn.setx(username + ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX + account_type,
                                   tell_data_key, DATA_EXPIRE_TIME)
                    ssdb_conn.setx(tell_data_key, tell_data, DATA_EXPIRE_TIME)
                ssdb_conn.setx(username + ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX + account_type,
                               status, DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

        yield self.get_next_request()

    def crawling_done(self, item, logout_request=None):
        item["is_complete"] = True
        yield item

        # 告诉web服务爬取完毕
        yield from self._set_crawling_status(username=item["username"], status="done",
                                             logout_request=logout_request)

    def crawling_login(self, username, tell_msg=""):
        account_type = SpiderName_2_AccountType_DICT[self.name]

        for i in range(self.SSDB_RETRY):
            try:
                if tell_msg:
                    self.ssdb_conn.setx(username + ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX + account_type,
                                        tell_msg, DATA_EXPIRE_TIME)
                self.ssdb_conn.setx(username + ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX + account_type,
                                    "login", DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

    def crawling_failed(self, username, tell_msg="", logout_request=None):
        # 告诉web服务爬取失败
        yield from self._set_crawling_status(username=username, status="error",
                                             tell_msg=tell_msg, logout_request=logout_request)

    def except_handle(self, username, msg, tell_msg="", logout_request=None):
        self.logger.exception(msg)
        yield from self.crawling_failed(username, tell_msg, logout_request)

    def error_handle(self, username, msg, tell_msg="", logout_request=None):
        self.logger.error(msg)
        yield from self.crawling_failed(username, tell_msg, logout_request)

    def _setx_data_2_ssdb(self, key_prefix, value):
        key = key_prefix + SpiderName_2_AccountType_DICT[self.name]
        for i in range(self.SSDB_RETRY):
            try:
                self.ssdb_conn.setx(key, value, DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

    def ask_captcha_code(self, uid):
        # uid是由web服务返回的，使用它在SSDB里查找结果
        ssbd_connect = self.ssdb_conn
        sleep_time = self.RETRY_SLEEP
        for i in range(self.RETRY_TIMES):
            try:
                captcha_code = ssbd_connect.get(uid)
                if captcha_code is not None:
                    return captcha_code
            except Exception:
                pass
            sleep(sleep_time)

        raise CaptchaTimeout

    def need_image_captcha(self, captcha, username, file_type=".jpg", image_describe=None):
        """
        告诉web服务：需要识别图片验证码
        """
        if isinstance(captcha, bytes):
            content = captcha
        elif isinstance(captcha, IOBase):
            content = captcha.read()
        else:
            raise BadCaptchaFormat

        uid = md5(content).hexdigest() + file_type
        file_b64_data = b64encode(content).decode()

        account_type = SpiderName_2_AccountType_DICT[self.name]
        ssbd_connect = self.ssdb_conn

        for i in range(self.SSDB_RETRY):
            try:
                ssbd_connect.delete(uid)
                ssbd_connect.setx(uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX,
                                  file_b64_data, DATA_EXPIRE_TIME)
                ssbd_connect.setx(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type,
                                  uid, DATA_EXPIRE_TIME)
                if image_describe:
                    ssbd_connect.setx(uid + ACCOUNT_CRAWLING_IMG_DESCRIBE_SSDB_SUFFIX,
                                      image_describe, DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

        return uid

    def ask_image_captcha(self, captcha, username, file_type=".jpg", image_describe=None):
        uid = self.need_image_captcha(captcha, username, file_type, image_describe)

        # 识别结果直接去SSDB里取
        return self.ask_captcha_code(uid)

    def need_sms_captcha(self, username):
        """
        告诉web服务：需要短信验证码
        """
        key_prefix = username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX
        uid = username + "-sms-" + str(time()) + str(randint(0, 100))
        self._setx_data_2_ssdb(key_prefix, uid)
        return uid

    def need_sms_captcha_type(self, username, type="general"):
        """
        告诉web服务：需要短信验证码、类型
        :param username: 手机号
        :param type    : 短信类型， "login"表示登录短信   "general"表示一般短信
        :return:
        """
        key_prefix = username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX
        uid = username + "-sms-" + str(time()) + str(randint(0, 100))
        uid_dict = {
            "uid": uid,
            "sms_type": type
        }
        self._setx_data_2_ssdb(key_prefix, data_dumps(uid_dict))
        return uid

    def ask_sms_captcha(self, username):
        uid = self.need_sms_captcha(username)

        # web服务会把结果写入SSDB，由爬虫通过SSDB读取结果
        # 这种设计虽然耦合性比较大，但效率高要一些
        return self.ask_captcha_code(uid)

    def ask_send_sms_captcha(self, username):
        """
        请求是否发送短信验证码
        :param username: 用户名
        :return:
        """
        sleep_time = self.RETRY_SLEEP
        for i in range(self.RETRY_TIMES):
            if self.ask_send_sms_captcha_once(username):
                return True
            sleep(sleep_time)

        raise CaptchaTimeout

    def ask_send_sms_captcha_once(self, username):
        """
        向SSDB查询一次：前端是否点击发送短信验证码
        """
        ssbd_connect = self.ssdb_conn
        account_type = SpiderName_2_AccountType_DICT[self.name]
        key = username + ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX + account_type
        try:
            is_send = ssbd_connect.get(key)
            if is_send is not None:
                ssbd_connect.delete(key)
                return True
            else:
                return False
        except Exception:
            pass
        return False

    def need_image_and_sms_captcha(self, captcha, username, file_type=".jpg"):
        """
        告诉web服务：同时需要图片验证码和短信验证码
        """
        if isinstance(captcha, bytes):
            content = captcha
        elif isinstance(captcha, IOBase):
            content = captcha.read()
        else:
            raise BadCaptchaFormat

        img_uid = md5(content).hexdigest() + file_type
        sms_uid = img_uid + ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX
        file_b64_data = b64encode(content).decode()

        account_type = SpiderName_2_AccountType_DICT[self.name]
        ssbd_connect = self.ssdb_conn

        for i in range(self.SSDB_RETRY):
            try:
                ssbd_connect.multi_del(img_uid, sms_uid)
                ssbd_connect.setx(img_uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX,
                                  file_b64_data, DATA_EXPIRE_TIME)
                ssbd_connect.setx(username + ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX + account_type,
                                  img_uid, DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

        return img_uid, sms_uid

    def need_image_and_sms_captcha_type(self, captcha, username, file_type=".jpg", type="general"):
        """
        告诉web服务：同时需要图片验证码和短信验证码、类型
        """
        if isinstance(captcha, bytes):
            content = captcha
        elif isinstance(captcha, IOBase):
            content = captcha.read()
        else:
            raise BadCaptchaFormat

        img_uid = md5(content).hexdigest() + file_type
        sms_uid = img_uid + ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX
        file_b64_data = b64encode(content).decode()
        uid_dict = {
            "uid": img_uid,
            "sms_type": type,
        }

        account_type = SpiderName_2_AccountType_DICT[self.name]
        ssbd_connect = self.ssdb_conn

        for i in range(self.SSDB_RETRY):
            try:
                ssbd_connect.multi_del(img_uid, sms_uid)
                ssbd_connect.setx(img_uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX,
                                  file_b64_data, DATA_EXPIRE_TIME)
                ssbd_connect.setx(username + ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX + account_type,
                                  data_dumps(uid_dict), DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

        return img_uid, sms_uid

    def ask_image_and_sms_captcha(self, captcha, username, file_type=".jpg"):
        img_uid, sms_uid = self.need_image_and_sms_captcha(captcha, username, file_type)

        # 识别结果直接去SSDB里取
        return self.ask_captcha_code(img_uid), self.ask_captcha_code(sms_uid)

    def need_extra_captcha(self, username):
        """
        向web服务请求附加码（如qq的独立密码等）
        """
        key_prefix = username + ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX
        uid = username + "-extra-" + str(time()) + str(randint(0, 100))
        self._setx_data_2_ssdb(key_prefix, uid)
        return uid

    def ask_extra_captcha(self, username):
        uid = self.need_extra_captcha(username)

        # web服务会把结果写入SSDB，由爬虫通过SSDB读取结果
        # 这种设计虽然耦合性比较大，但效率高要一些
        return self.ask_captcha_code(uid)

    def need_scan_qrcode(self, qrcode, username, file_type=".jpg"):
        """
        告诉web服务：需要扫描二维码
        """
        if isinstance(qrcode, bytes):
            content = qrcode
        elif isinstance(qrcode, IOBase):
            content = qrcode.read()
        else:
            raise BadCaptchaFormat

        uid = md5(content).hexdigest() + file_type
        file_b64_data = b64encode(content).decode()
        account_type = SpiderName_2_AccountType_DICT[self.name]
        ssbd_connect = self.ssdb_conn

        for i in range(self.SSDB_RETRY):
            try:
                ssbd_connect.delete(uid)
                ssbd_connect.setx(uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX,
                                  file_b64_data, DATA_EXPIRE_TIME)
                ssbd_connect.setx(username + ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX + account_type,
                                  uid, DATA_EXPIRE_TIME)
                break
            except Exception:
                if self.SSDB_RETRY - 1 == i:
                    raise

        return uid

    def ask_scan_qrcode(self, qrcode, username, file_type=".jpg"):
        uid = self.need_scan_qrcode(qrcode, username, file_type)

        # 识别结果直接去SSDB里取
        return self.ask_captcha_code(uid)

    def need_send_sms_captcha(self, username):
        """
        告诉web服务：需要发送短信验证码
        """
        key_prefix = username + ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX
        uid = username + "-send_sms-" + str(time()) + str(randint(0, 100))
        self._setx_data_2_ssdb(key_prefix, uid)
        return uid

    def ask_sms_captcha_new(self, username, uid):
        # web服务会把结果写入SSDB，由爬虫通过SSDB读取结果
        # 这种设计虽然耦合性比较大，但效率高要一些
        return self.ask_captcha_code(uid)

    def set_image_captcha_headers_to_ssdb(self, headers, username):
        """
        将图片验证码的headers信息写入ssdb中，以供Django使用
        :param headers : 验证码头部信息
        :param username: 用户名
        :return:
        """
        key_prefix = username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX
        self._setx_data_2_ssdb(key_prefix, headers)

    def set_sms_captcha_headers_to_ssdb(self, headers, username):
        """
        将短信验证码的headers信息写入ssdb中，以供Django使用
        :param headers : 验证码头部信息
        :param username: 用户名
        :return:
        """
        key_prefix = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX
        self._setx_data_2_ssdb(key_prefix, headers)

    def set_email_img_url_to_ssdb(self, captcha_url, username):
        """
        将短信验证码的图片连接信息写入ssdb中，以供Django使用
        :param captcha_url : 验证url连接
        :param username: 用户名
        :return:
        """
        key_prefix = username + ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX
        self._setx_data_2_ssdb(key_prefix, captcha_url)

    def ask_qrcode_cookies(self, username, account_type):
        """
        获取扫描二维码登录成功后的cookies信息
        :param username:
        :param account_type:
        :return:
        """
        uid = username + ACCOUNT_CRAWLING_QRCODE_COOKIES_SSDB_SUFFIX + account_type
        return data_loads(self.ask_captcha_code(uid))

    def need_name_idcard_sms_captcha_type(self, username, type="general"):
        """
        告诉web服务：需要姓名、身份证号、短信验证码
        :param username: 用户名
        :param type    : 短信类型， "login"表示登录短信   "general"表示一般短信
        :return:
        """
        key_prefix = username + ACCOUNT_CRAWLING_NEED_NAME_IDCARD_SMS_SSDB_SUFFIX
        uid = username + "-name_idcard_sms-" + str(time()) + str(randint(0, 100))
        uid_dict = {
            "uid": uid,
            "sms_type": type
        }
        self._setx_data_2_ssdb(key_prefix, data_dumps(uid_dict))
        return uid

    # def ask_name_idcard_sms_captcha(self, uid):
    #     # uid是由web服务返回的，使用它在SSDB里查找结果
    #     ssbd_connect = self.ssdb_conn
    #     sleep_time = self.RETRY_SLEEP
    #     for i in range(self.RETRY_TIMES):
    #         try:
    #             datas = ssbd_connect.get(uid)
    #             if datas is not None:
    #                 datas_dict = data_loads(datas)
    #                 return datas_dict["name"], datas_dict["id_card"], datas_dict["sms_code"]
    #         except Exception:
    #             pass
    #         sleep(sleep_time)
    #
    #     raise CaptchaTimeout
