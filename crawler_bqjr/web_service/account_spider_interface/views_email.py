# coding:utf-8

from base64 import b64encode
from random import random
from re import compile as re_compile

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from requests import get as http_get
from scrapy import Selector
from utils import add_ajax_ok_json, add_ajax_error_json, catch_except

from crawler_bqjr.spiders_settings import ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

qq_appid_pattern = re_compile(r"appid=(\d+)&")
qq_daid_pattern = re_compile(r"daid=(\d+)&")
qq_qr_result_list_pattern = re_compile(r"ptuiCB\((.*)\)")
qq_qr_result_info_pattern = re_compile(r"'(.*)'")

QQ_GET_QRCODE_HEADERS = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.8',
}
QQ_GET_QRCODE_STATUS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36",
    "Accept": "text/plain, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}


def __hash_33(t):
    e = 0
    for char in t:
        e += (e << 5) + ord(char)
    return 2147483647 & e


@catch_except
def qq_get_qrcode(request):
    """
    获取qq登录二维码图片
    :param request:
    :return:
    """

    index_url = 'https://mail.qq.com/cgi-bin/loginpage'
    ret_data = {}
    try:
        index_r = http_get(index_url, headers=QQ_GET_QRCODE_HEADERS)
        index_text = index_r.text
        iframe_url = Selector(text=index_text).xpath("//iframe/@src").extract_first("")
        iframe_r = http_get(iframe_url, headers=QQ_GET_QRCODE_HEADERS)
        cookies = iframe_r.cookies.get_dict()
        appid = qq_appid_pattern.search(iframe_url).group(1)
        daid = qq_daid_pattern.search(iframe_url).group(1)
        qr_url = "https://ssl.ptlogin2.qq.com/ptqrshow?" \
                 "appid={0}&e=2&l=M&s=3&d=72&v=4&t={1}&" \
                 "daid={2}&pt_3rd_aid=0".format(appid, random(), daid)

        qr = http_get(qr_url, headers=QQ_GET_QRCODE_HEADERS, cookies=cookies)
        cookies.update(qr.cookies.get_dict())
        data = {
            'pic': b64encode(qr.content).decode(),
            'cookies': cookies,
            'appid': appid,
            'daid': daid
        }
        ret_data["data"] = data
        add_ajax_ok_json(ret_data)
    except Exception:
        add_ajax_error_json(ret_data, "无法获取二维码")
    finally:
        return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def qq_get_qrcode_status(request):
    """
    检查qq登录二维码图片有效性
    :param request:
    :return:
    """
    ret_data = {}
    try:
        args = request.POST
        cookies = json_loads(args.get('cookies', {}))
        appid = args.get('appid', '522005705')
        daid = args.get('daid', '4')
        ptqrtoken = __hash_33(cookies.get('qrsig'))
        scan_url = "https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https%3A%2F%2Fmail.qq.com%2Fcgi-bin%2Freadtemplate%3" \
                   "Fcheck%3Dfalse%26t%3Dloginpage_new_jump%26vt%3Dpassport%26vm%3Dwpt%26ft%3Dlogi" \
                   "npage%26target%3D&ptqrtoken={0}&ptredirect=0&h=1&t=1&g=1&from_ui=1&pt" \
                   "lang=2052&action=1-1-1513651703600&js_ver=10232&js_type=1&login_s" \
                   "ig=&pt_uistyle=25&aid={1}&daid={2}&".format(ptqrtoken, appid, daid)
        headers = QQ_GET_QRCODE_STATUS_HEADERS.copy()
        headers['Cookie'] = "qrsig=" + cookies.get('qrsig')
        scan_text = http_get(scan_url, headers=headers, cookies=cookies).text
        qr_result_list = qq_qr_result_list_pattern.search(scan_text).group(1).split(',')
        qr_result_code = qq_qr_result_info_pattern.search(qr_result_list[0]).group(1)
        qr_result_url = qq_qr_result_info_pattern.search(qr_result_list[2]).group(1)
        qr_result_status = qq_qr_result_info_pattern.search(qr_result_list[4]).group(1)
        qr_result_nick_name = qq_qr_result_info_pattern.search(qr_result_list[5]).group(1)
        data = {
            'qr_code': qr_result_code,
            'qr_url': qr_result_url,
            'qr_status': qr_result_status,
            'qr_nick_name': qr_result_nick_name
        }

        ret_data["data"] = data
        add_ajax_ok_json(ret_data)
    except Exception:
        add_ajax_error_json(ret_data, "二维码失效")
    finally:
        return JsonResponse(ret_data)


###############################################################################
#
#  sina验证码切换
#
###############################################################################
@require_http_methods(["POST"])
@catch_except
def get_sina_img_captcha(request):
    """获取图片验证码"""
    ret_data = {}
    args = request.POST
    username = args["username"].strip()
    account_type = args["account_type"]

    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    header_key = username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX + account_type
    url_key = username + ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX + account_type
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(header_key)
        if headers is not None:
            captcha_url = ssdb_conn.get(url_key)
            img_content = http_get(captcha_url, headers=eval(headers)).content
            ret_data["img_data"] = bytes.decode(b64encode(img_content))
        else:
            add_ajax_error_json(ret_data, "无法获取图片验证码")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取图片验证码")
    else:
        add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


############################################################################################
#
# 搜狐验证码
#
############################################################################################
@require_http_methods(["POST"])
@catch_except
def get_sohu_img_captcha(request):
    """获取图片验证码"""
    ret_data = {}
    args = request.POST
    username = args["username"].strip()
    account_type = args["account_type"]

    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    header_key = username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX + account_type
    url_key = username + ACCOUNT_CRAWLING_IMG_URL_SSDB_SUFFIX + account_type
    try:
        ssdb_conn = get_ssdb_conn()
        cookies_dict = ssdb_conn.get(header_key)
        if cookies_dict:
            cookies_dict = eval(cookies_dict)
            captcha_url = ssdb_conn.get(url_key)
            img_content = http_get(captcha_url, cookies=cookies_dict).content
            ret_data["img_data"] = bytes.decode(b64encode(img_content))
        else:
            add_ajax_error_json(ret_data, "无法获取图片验证码")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取图片验证码")
    else:
        add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)
