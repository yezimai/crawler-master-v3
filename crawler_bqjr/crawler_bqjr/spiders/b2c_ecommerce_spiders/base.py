# coding:utf-8

from re import compile as re_compile

from lxml import html as lxml_html

from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.utils import get_content_by_requests, get_content_by_requests_post, \
    get_response_by_requests, get_response_by_requests_post
from global_utils import json_loads


class EcommerceSpider(AccountSpider):
    """
    电商爬虫基类
    """
    LOGIN_TYPE = {
        "account_login": 1,
        "qrcode_login": 2,
        "mobile_login": 3,
        "jump_login": 4
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, sdch, br",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.04",
        }
        self.cookies = None

        # find element method
        self.BY_ID = 1
        self.BY_NAME = 2
        self.BY_XPATH = 3
        self.BY_CLASS = 4
        self.BY_LINK = 5
        self.SCAN_QRCODE_SUCC = "ok"  # 扫描二维码成功标识
        self.split_str = "##LOGIN_TYPE##"
        self.reg_blank = re_compile(r'\s+')

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        meta = request.meta
        password = meta["item"]["password"]
        if password and self.split_str in password:
            password, login_type = password.split(self.split_str)
            meta["item"]["password"] = password
        else:
            login_type = self.LOGIN_TYPE.get("account_login", 1)
        meta["login_type"] = int(login_type)
        return request

    def _get_element(self, driver, element, by=None, wait_time=3):
        """
        获取Element
        :param driver:
        :param element:
        :param by:
        :param wait_time:
        :return:
        """
        if by is None:
            by = self.BY_ID
        re_data = None
        try:
            if not driver:
                return None
            driver.implicitly_wait(wait_time)
            if by == self.BY_ID:
                re_data = driver.find_element_by_id(element)
            elif by == self.BY_NAME:
                re_data = driver.find_element_by_name(element)
            elif by == self.BY_XPATH:
                re_data = driver.find_element_by_xpath(element)
            elif by == self.BY_CLASS:
                re_data = driver.find_element_by_class_name(element)
            elif by == self.BY_LINK:
                re_data = driver.find_element_by_link_text(element)
            else:
                pass
        except Exception:
            self.logger.info("[-]NO SUCH ELEMENT:%s" % element)
        finally:
            return re_data

    def reg_match(self, content, pattern, get_one=True, default=None, strip=True, no_blank=True, charset="utf-8"):
        """
        正则匹配
        :param content:
        :param pattern:
        :param get_one:
        :param default:
        :param strip:
        :param no_blank:
        :param charset:
        :return:
        """
        try:
            if not content:
                self.logger.error("正则匹配文本为空")
                return
            if isinstance(content, bytes):
                content = content.decode(charset)
            if isinstance(pattern, str):
                pattern = re_compile(pattern)
            if get_one:
                res = pattern.search(content)
                if res:
                    res = res.group(1)
            else:
                res = pattern.findall(content)

            if not res:
                return default

            re_data = self.trim_all(res, no_blank=no_blank, strip=strip)

            if not re_data and default is not None:
                re_data = default

            return re_data
        except Exception:
            self.logger.exception("匹配正则出错: %s" % pattern.pattern)
            return

    def get_value_by_name(self, response, name):
        """
        通过属性值获取input的value值
        :param response:
        :param name:
        :return:
        """
        try:
            pattern = '//input[@name="%s"]/@value' % name
            return response.xpath(pattern).extract_first("")
        except Exception:
            self.logger.exception("获取%s失败:" % name)
            return ""

    def http_request(self, url, method="GET", data=None, headers=None, cookies=None,
                     to_json=False, get_str=True, charset="utf-8", get_cookies=False):
        """
        封装HTTP请求
        :param url:
        :param data:
        :param method:
        :param headers:
        :param cookies:
        :param to_json:
        :param get_str:
        :param charset:
        :param get_cookies:
        :return:
        """
        try:
            cookies_dic = {}
            if headers is None:
                headers = self.headers or {}
            if cookies is None:
                cookies = self.cookies or {}
            if isinstance(cookies, list):
                cookies = {cookie["name"]: cookie["value"] for cookie in cookies}

            if method == "GET":
                if get_cookies:
                    resp = get_response_by_requests(url, headers=headers, cookie_jar=cookies)
                    cookies_dic = resp.cookies.get_dict()
                    content = resp.content
                else:
                    content = get_content_by_requests(url, headers=headers, cookie_jar=cookies)
            elif method == "POST":
                if get_cookies:
                    resp = get_response_by_requests_post(url, headers=headers, cookie_jar=cookies)
                    cookies_dic = resp.cookies.get_dict()
                    content = resp.content
                else:
                    content = get_content_by_requests_post(url, data=data, headers=headers, cookie_jar=cookies)
            else:
                self.logger.error("暂不支持该请求方法")
                return

            if not get_str:
                if get_cookies:
                    return {"result": content, "cookies": cookies_dic}
                return content
            page = content.decode(charset)

            if not to_json:
                if get_cookies:
                    return {"result": page, "cookies": cookies_dic}
                return page

            if get_cookies:
                return {"result": json_loads(page), "cookies": cookies_dic}

            return json_loads(page)
        except Exception:
            self.logger.exception("请求出错: url:%s" % url)
            return

    def xpath_match(self, element, xpath, get_one=True, default=None, no_blank=True, strip=True):
        """
        XPATH匹配
        :param element:
        :param xpath:
        :param get_one:
        :param default:
        :return:
        """
        try:
            dom = lxml_html.fromstring(element) if isinstance(element, str) else element
            res = dom.xpath(xpath)
            if res:
                if get_one:
                    return self.trim_all(res[0], no_blank=no_blank, strip=strip)
                else:
                    return res
            elif default:
                return default
            else:
                return
        except Exception:
            self.logger.exception("XPATH匹配出错：%s" % xpath)
            return

    def trim_all(self, text, opt_value=None, no_blank=True, strip=True):
        """
        去除空格换行等字符
        :param text:
        :param opt_value:
        :param no_blank:
        :param strip:
        :return:
        """
        try:
            if not isinstance(text, str):
                return text
            res = ""
            default_list = ["&nbsp;", "\xa0", "\t", "\n"]
            if opt_value is not None:
                default_list += list(opt_value) if isinstance(opt_value, str) else opt_value
            for i in set(default_list):
                res = text.replace(i, "")
            if no_blank:
                res = self.reg_blank.sub(" ", res)
            if strip:
                res = res.strip()
            return res
        except Exception:
            self.logger.exception("转换字符串失败:")
            return text
