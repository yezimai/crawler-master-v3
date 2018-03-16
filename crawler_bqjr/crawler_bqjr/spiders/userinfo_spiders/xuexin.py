# -*- coding: utf-8 -*-

from random import random
from re import compile as re_compile

from scrapy import Selector
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from crawler_bqjr.spider_class import PhantomJSWebdriverSpider
from crawler_bqjr.spiders.userinfo_spiders.base import UserInfoSpider
from crawler_bqjr.utils import get_cookies_dict_from_webdriver, get_content_by_requests


class XuexinPhantomJsSpider(PhantomJSWebdriverSpider, UserInfoSpider):
    name = "xuexin"
    allowed_domains = ["chsi.com.cn"]
    start_urls = ["https://my.chsi.com.cn/archive/gdjy/xj/show.action", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, load_images=False, **kwargs)
        self.login_url = self._start_url_
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.xj_values_pattern = re_compile(r'<.*?>')
        self.xj_data_pattern = re_compile(r'initDataInfo\("\S+?m(\d)", "(\S*)"')

    def _get_pic_by_requests(self, driver, url):
        cookiejar = get_cookies_dict_from_webdriver(driver)
        return get_content_by_requests(url, self.headers, cookie_jar=cookiejar)

    def _do_login(self, driver, item, success_xpath):
        username = item["username"]

        driver.execute_script('document.getElementById("username").value="%s";'
                              'document.getElementById("password").value="%s";'
                              % (username, item["password"]))

        try:
            driver.find_element_by_id('captcha')
        except NoSuchElementException:
            pass
        else:
            url = "https://account.chsi.com.cn/passport/captcha.image?id=" + str(random())
            captcha_body = self._get_pic_by_requests(driver, url)
            captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".jpeg")
            driver.execute_script('document.getElementById("captcha").value="'
                                  + captcha_code + '";')

        # 点击登录
        driver.execute_script('document.getElementsByName("submit")[0].click();')

        try:
            self.wait_xpath(driver, success_xpath, raise_timeout=True, timeout=11)
        except TimeoutException:
            page_source = driver.page_source
            if '"errors"' in page_source:
                return driver.find_element_by_xpath("//div[@class='errors']").text
            elif "t errors" in page_source:
                return self._do_login(driver, item, success_xpath)
            else:
                raise Exception(page_source)

        return None

    def _get_xj(self, xueli, title, table_info, driver):
        xueji = None
        for xj_item in xueli:
            if xj_item.get('类别：') == title:
                xueji = xj_item
                break

        if xueji is None:  # 没有学籍信息，通过学历栏获取相关信息
            xj_values_pattern = self.xj_values_pattern
            xl_keys = table_info.xpath('.//th/text()').extract()
            xl_td_values = table_info.xpath('.//td').extract()
            xueji = dict(zip(xl_keys, (xj_values_pattern.split(x)[1] for x in xl_td_values)))
            xueli.append(xueji)

        url = table_info.xpath('.//div[@class="pic"]/img/@src').extract_first()
        if url and 'no-photo' not in url:
            pic_data = self._get_pic_by_requests(driver, 'https://my.chsi.com.cn' + url)
        else:
            pic_data = b''

        xueji['证书编号：'] = table_info.xpath('.//td/text()').extract()[-1]
        if pic_data:
            xueji['毕业证照片：'] = pic_data

        return xueji

    def parse(self, response):
        item = response.meta['item']
        username = item["username"]

        driver = self.load_page_by_webdriver(self.login_url, "//input[@name='submit']")
        try:
            datas_xpath = '//div[@class="clearfix"]'
            msg = self._do_login(driver, item, datas_xpath)
            if msg is not None:
                yield from self.error_handle(username,
                                             "学信网---登录失败：(username:%s, password:%s) %s"
                                             % (username, item["password"], msg),
                                             tell_msg=msg)
                return

            self.crawling_login(username)  # 通知授权成功

            # 学籍信息
            xueli = []
            xj_values_pattern = self.xj_values_pattern
            xj_data_pattern = self.xj_data_pattern
            for table_info in Selector(text=driver.page_source).xpath(datas_xpath):
                # 学籍 table 信息
                xj_keys = table_info.xpath('.//th/text()').extract()
                xj_td_values = table_info.xpath('.//td').extract()
                xj_values = [xj_values_pattern.split(x)[1] for x in xj_td_values]

                script_html = table_info.xpath(".//script/text()").extract_first("")
                xj_datas_dict = dict(xj_data_pattern.findall(script_html))

                xj_values_dict = dict(zip(xj_keys, xj_values))
                xj_values_dict["学校名称："] = xj_datas_dict.get("1")
                xj_values_dict["专业："] = xj_datas_dict.get("2")
                xj_values_dict["学号："] = xj_datas_dict.get("4")
                xj_values_dict["层次："] = xj_datas_dict.get("5")
                xj_values_dict["学历类别："] = xj_datas_dict.get("6")
                xj_values_dict["学习形式："] = xj_datas_dict.get("7")
                xj_values_dict["证件号码："] = xj_datas_dict.get("8")

                title = table_info.xpath('.//div[@class="mb-title"]/text()').extract_first("")
                if title.startswith('本科'):
                    xj_values_dict["类别："] = '本科'
                elif title.startswith('专科'):
                     xj_values_dict["类别："] = '专科'
                elif title.startswith('硕士'):
                     xj_values_dict["类别："] = '硕士'
                elif title.startswith('博士'):
                     xj_values_dict["类别："] = '博士'
                elif title.startswith('博士后'):
                     xj_values_dict["类别："] = '博士后'

                xueli.append(xj_values_dict)

            # 学历信息
            driver.get('https://my.chsi.com.cn/archive/gdjy/xl/show.action')
            for table_info in Selector(text=driver.page_source).xpath(datas_xpath):
                title = table_info.xpath('.//div[@class="mb-title"]/text()').extract_first("")
                if title.startswith('本科'):
                    self._get_xj(xueli, '本科', table_info, driver)
                elif title.startswith('专科'):
                    self._get_xj(xueli, '专科', table_info, driver)
                elif title.startswith('硕士'):
                    self._get_xj(xueli, '硕士', table_info, driver)
                elif title.startswith('博士'):
                    self._get_xj(xueli, '博士', table_info, driver)
                elif title.startswith('博士后'):
                    self._get_xj(xueli, '博士后', table_info, driver)

            item['xueli'] = xueli
            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(username, "学信网---爬虫解析入口异常")
        finally:
            driver.quit()
