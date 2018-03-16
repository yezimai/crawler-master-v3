# -*- coding: utf-8 -*-
####################################################
# webdriver包装器
# 作者： tao.jiang02@bqjr.cn
# 日期： 2017年1月6日
# 版本： V1.0
####################################################

from random import choice

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import ProxyType

from crawler_bqjr.settings import HEADLESS_CHROME_PATH


class UserAgentUtils(object):
    USER_AGENT = [
        "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50)",
        # safari 5.1 mac
        "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50)",
        # safari 5.1 windows
        "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0)",  # ff
        "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; InfoPath.3; rv:11.0) like Gecko)",
        # IE 11
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)",  # IE 9.0
        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0)",  # IE 8.0
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",  # IE 7.0
        " Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",  # IE6.0
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:2.0.1) Gecko/20100101 Firefox/4.0.1)",  # FF 4.0.1 mac
        "Mozilla/5.0 (Windows NT 6.1; rv:2.0.1) Gecko/20100101 Firefox/4.0.1)",  # FF 4.0.1 windows
        "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; en) Presto/2.8.131 Version/11.11)",  # Opera 11.11 – MAC
        "Opera/9.80 (Windows NT 6.1; U; en) Presto/2.8.131 Version/11.11)",  # Opera 11.11 – Windows
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        # Chrome 17.0 – MAC
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)"  # 360浏览器
    ]

    ############################################################################
    # 随机获取UserAgent
    ############################################################################
    @classmethod
    def randomUA(cls):
        return choice(cls.USER_AGENT)


class PhantomjsWebDriverBuilder(object):
    def __init__(self, browser_type=None, *args, **kwargs):
        self.driver = None
        self.log_path = None
        self.implicitly_wait = self.page_load_timeout = self.script_timeout = None

        self.browser_type = browser_type or "PHANTOMJS"
        if "CHROME" in self.browser_type:
            self.dcap = DesiredCapabilities.CHROME.copy()
            chrome_options = webdriver.ChromeOptions()
            chrome_options.binary_location = HEADLESS_CHROME_PATH
            if "HEADLESS" in self.browser_type:
                chrome_options.add_argument('headless')
            chrome_options.add_argument('disable-gpu')
            self.chrome_options = chrome_options
        elif self.browser_type == "IE":
            self.dcap = DesiredCapabilities.INTERNETEXPLORER.copy()
        else:
            self.dcap = DesiredCapabilities.PHANTOMJS.copy()

    def build(self, executable_path):
        self.dcap["phantomjs.page.settings.userAgent"] = UserAgentUtils.randomUA()
        if "CHROME" in self.browser_type:
            self.driver = webdriver.Chrome(executable_path=executable_path,
                                           chrome_options=self.chrome_options,
                                           desired_capabilities=self.dcap,
                                           service_log_path=self.log_path)
        elif self.browser_type == "IE":
            self.driver = webdriver.Ie(executable_path=executable_path,
                                       capabilities=self.dcap, log_file=self.log_path)
        else:
            self.driver = webdriver.PhantomJS(executable_path=executable_path,
                                              desired_capabilities=self.dcap,
                                              service_log_path=self.log_path)
        # 等待5秒再发送请求
        if self.implicitly_wait is not None:
            self.driver.implicitly_wait(self.implicitly_wait)
        # 加载页面超时时间
        if self.page_load_timeout is not None:
            self.driver.set_page_load_timeout(self.page_load_timeout)
        # 加载脚本超时时间
        if self.script_timeout is not None:
            self.driver.set_script_timeout(self.script_timeout)
        return self.driver

    def use_proxy(self, url):
        proxy = webdriver.Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = url
        proxy.ssl_proxy = url
        # 将代理设置添加到webdriver.DesiredCapabilities.PHANTOMJS中
        proxy.add_to_capabilities(self.dcap)
        return self

    def set_browser_type(self, type="PHANTOMJS"):
        self.browser_type = type
        return self

    def set_log_path(self, log_path):
        self.log_path = log_path
        return self

    #################################################
    # 设置发送请求的等待时间
    #################################################
    def set_implicitly_wait(self, implicitly_wait):
        self.implicitly_wait = implicitly_wait
        return self

    #################################################
    # 设置页面加载超时时间
    #################################################
    def set_page_load_timeout(self, page_load_timeout):
        self.page_load_timeout = page_load_timeout
        return self

    #################################################
    # 设置脚本加载的超时时间
    #################################################
    def set_script_timeout(self, script_timeout):
        self.script_timeout = script_timeout
        return self


class PhantomjsWebDriverFactory(object):
    @classmethod
    def new_builder(cls, browser_type=None):
        return PhantomjsWebDriverBuilder(browser_type)
