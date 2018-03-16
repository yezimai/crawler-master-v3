# -*- coding: utf-8 -*-

from base64 import b64decode
from calendar import monthrange
from datetime import date
from io import BytesIO
from random import choice as rand_choice
from re import compile as re_compile
from time import time, sleep, mktime

from PIL import Image
from dateutil.relativedelta import relativedelta
from requests import get as http_get, post as http_post
from scrapy.http.cookies import CookieJar
from scrapy.utils.project import get_project_settings

from crawler_bqjr.downloader_handlers import PhantomJSHandler

scrapy_settings = get_project_settings()

ASK_TIMEOUT = 11

numbers_pattern = re_compile(r'([\+\-]?\d+\.?\d*)')

# http://www.useragentstring.com/pages/useragentstring.php
USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2251.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/534.57.2 (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 OPR/26.0.1656.60',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36 QIHU 360SE',
    'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.3) QQBrowser/6.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36 TheWorld 6',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 UBrowser/4.0.3647.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36 SE 2.X MetaSr 1.0',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.122 BIDUBrowser/7.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Maxthon/4.4.3.4000 Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36 LBBROWSER',
]


def invert_dict(dic):
    return {v: k for k, v in dic.items()}


def get_one_ua():
    return rand_choice(USER_AGENT_LIST)


def get_js_time():
    return str(int(time() * 1E3))


def sleep_to_tomorrow():
    tomorrow = date.today() + relativedelta(days=1)
    sleep(mktime(tomorrow.timetuple()) - time() + 1000)


def get_numbers_in_text(text):
    """
        返回的是列表
    """
    return numbers_pattern.findall(text)


def find_str_range(str_obj, start_str, end_str):
    """
    截取字符串
    """
    start_index = str_obj.find(start_str)
    if start_index >= 0:
        return str_obj[start_index:str_obj.find(end_str, start_index)]
    elif isinstance(start_str, str):
        return ""
    else:
        return b""


def get_last_month_from_date(date_obj):
    return date_obj - relativedelta(months=1)


def get_month_last_date_by_date(date_obj):
    """
        返回日期字符串，例如：2016-07-31
    """
    year = date_obj.year
    month = date_obj.month
    day = monthrange(year, month)[1]
    return "%d-%02d-%02d" % (year, month, day)


def get_in_nets_duration_by_start_date(date_str):
    """
    :date_str: 例如：1999-01-01
    :return: 在网月数
    """
    the_date = date(*map(int, date_str.split("-")))
    return (date.today() - the_date).days // 30


def get_months_str_by_number(number, is_contain_now=True):
    """
    获取最近number个月组成的字符串
    :param number        : 指定最近的月份数量
    :param is_contain_now: 是否包含本月
    :return str          : eg: "201801,201802"
    """
    months = []
    for i in range(number):
        if (not is_contain_now) and (i == 0):
            continue
        now_date = date.today() - relativedelta(months=i)
        months.append(now_date.strftime("%Y%m"))
    return ",".join(months)


def get_headers_from_response(response):
    return {k: (v[0] if v else "") for k, v in response.request.headers.items()}


def get_cookies_list_from_webdriver(driver, sleep_time=0.1):
    cookies_list = []
    for i in range(3):
        cookies_list = driver.get_cookies()
        if cookies_list:
            break
        else:
            sleep(sleep_time)
    return cookies_list


def get_cookies_dict_from_webdriver(driver, sleep_time=0.1):
    return {cookie["name"]: cookie["value"] for cookie
            in get_cookies_list_from_webdriver(driver, sleep_time)}


def get_cookies_list_from_phantomjs(url, sleep_time=0.1):
    settings = scrapy_settings
    driver = PhantomJSHandler(settings).get_driver(settings["USER_AGENT"])
    try:
        driver.get(url)
        cookies_list = get_cookies_list_from_webdriver(driver, sleep_time)
        return cookies_list
    except Exception:
        return []
    finally:
        driver.quit()


def get_cookies_dict_from_phantomjs(url, sleep_time=0.1):
    return {cookie["name"]: cookie["value"] for cookie
            in get_cookies_list_from_phantomjs(url, sleep_time)}


def get_cookies_str_from_response(response):
    return b";".join(response.headers.getlist('Set-Cookie', []))


def get_cookies_str_from_request(request):
    return b";".join(request.headers.getlist('Cookie', []))


def get_cookiejar_from_response(response):
    cookie_jar = response.meta.setdefault('cookie_jar', CookieJar())
    cookie_jar.extract_cookies(response, response.request)
    return cookie_jar.jar


def yield_cookies_dict_from_request_for_scrapy(request):
    for c in request.headers.getlist('Cookie', []):
        yield dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv)


def yield_cookies_dict_from_response_for_scrapy(response):
    for c in response.headers.getlist('Set-Cookie', []):
        yield dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv)


def get_response_by_requests(url, headers, cookie_str=None, cookie_jar=None, proxies=None):
    if cookie_str is not None:
        headers['Cookie'] = cookie_str

    kwargs = {"headers": headers,
              "timeout": ASK_TIMEOUT,
              "verify": False,
              "proxies":proxies
              }

    if cookie_jar is not None:
        kwargs["cookies"] = cookie_jar

    return http_get(url, **kwargs)


def get_content_by_requests(url, headers, cookie_str=None, cookie_jar=None, proxies=None):
    resp = get_response_by_requests(url, headers=headers,
                                    cookie_str=cookie_str, cookie_jar=cookie_jar, proxies=proxies)
    return resp.content


def get_response_by_requests_post(url, headers, data=None, cookie_str=None, cookie_jar=None):
    if cookie_str is not None:
        headers['Cookie'] = cookie_str

    kwargs = {"headers": headers,
              "timeout": ASK_TIMEOUT,
              "verify": False,
              }

    if cookie_jar is not None:
        kwargs["cookies"] = cookie_jar

    return http_post(url, data=data, **kwargs)


def get_content_by_requests_post(url, headers, data=None, cookie_str=None, cookie_jar=None):
    resp = get_response_by_requests_post(url, headers=headers, data=data,
                                         cookie_str=cookie_str, cookie_jar=cookie_jar)
    return resp.content


#################################################################
# 秒转为时分秒
#################################################################
def seconds_format(seconds):
    if seconds <= 60:
        return seconds
    minutes = int(seconds / 60)
    seconds = seconds % 60
    if minutes <= 60:
        return "%s分%s秒" % (minutes, seconds)
    hours = int(minutes / 60)
    return "%s时%s分%s秒" % (hours, minutes, seconds)


def driver_screenshot_2_bytes(photo_base64, crop_box, img_format="PNG"):
    with BytesIO(b64decode(photo_base64)) as buffer, \
            Image.open(buffer) as img, BytesIO() as temp:
        im = img.crop(crop_box)
        im.save(temp, img_format)
        img_bytes = temp.getvalue()
        im.close()
        return img_bytes
