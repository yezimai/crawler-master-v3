# -*-coding:utf-8-*-

# from scrapy.core.downloader import Downloader
# from scrapy.core.downloader.handlers.file import FileDownloadHandler
# from scrapy.core.downloader.handlers.http import HttpDownloadHandler
# from scrapy.core.downloader.handlers.http import HttpDownloadHandler
# from scrapy.core.downloader.handlers.s3 import S3DownloadHandler

from urllib.parse import urlsplit, urlunsplit

from scrapy import twisted_version
from scrapy.http import HtmlResponse
from selenium.webdriver import PhantomJS
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait

if twisted_version >= (11, 1, 0):
    from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler as HTTPDownloadHandler
else:
    from scrapy.core.downloader.handlers.http10 import HTTP10DownloadHandler as HTTPDownloadHandler


class PhantomJSHandler(object):
    def __init__(self, settings):
        self.executable_path = settings['PHANTOMJS_EXECUTABLE_PATH']
        self.service_args = settings.get('PHANTOMJS_OPTIONS', ["--load-images=false",
                                                               "--disk-cache=false"])
        self.check_wait_time = settings.get("WEBDRIVER_CHECK_WAIT_TIME", 0.1)
        self.page_load_timeout = settings['WEBDRIVER_LOAD_TIMEOUT']
        self.dcap = DesiredCapabilities.PHANTOMJS.copy()
        self.dcap["phantomjs.page.settings.resourceTimeout"] = self.page_load_timeout * 1000  # 单位是毫秒

    def get_driver(self, ua, proxy=None):
        if not proxy:
            service_args = self.service_args
        else:
            service_args = self.service_args.copy()
            p = urlsplit(proxy)
            service_args += ["--proxy=" + (p.netloc or p.path),
                             "--proxy-type=" + (p.scheme or "http")]

        dcap = self.dcap.copy()
        dcap["phantomjs.page.settings.userAgent"] = ua

        driver = PhantomJS(executable_path=self.executable_path,
                           service_args=service_args,
                           desired_capabilities=dcap)
        driver.set_page_load_timeout(self.page_load_timeout)
        driver.set_script_timeout(self.page_load_timeout)
        return driver

    def wait_xpath(self, driver, xpath):
        wait = WebDriverWait(driver, 30, poll_frequency=self.check_wait_time)
        try:
            wait.until(lambda dr: dr.find_element_by_xpath(xpath))
        except TimeoutException:
            pass

    def download_request(self, request, spider):
        meta = request.meta
        phantomjs_finish_xpath = meta.get("phantomjs_finish_xpath")
        proxy = meta.get("proxy")
        url = meta.get("original_url", urlunsplit(("http",) + urlsplit(request.url)[1:]))
        ua = request.headers.get('User-Agent',
                                 b'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0')

        driver = self.get_driver(ua.decode('utf-8'), proxy)
        try:
            driver.get(url)

            if phantomjs_finish_xpath:  # 等待元素加载
                self.wait_xpath(driver, phantomjs_finish_xpath)

            html_body = driver.page_source
            headers = request.headers
            return HtmlResponse(url, encoding="utf-8", body=html_body, headers=headers)
        except Exception:
            raise
        finally:
            driver.quit()
