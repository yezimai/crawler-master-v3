# coding:utf-8

from base64 import b64encode
from time import time, sleep

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from requests import Session as req_session
from utils import add_ajax_ok_json, add_ajax_error_json, catch_except

from crawler_bqjr.spiders_settings import ACCOUNT_CRAWLING_QRCODE_COOKIES_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX, DATA_EXPIRE_TIME
from crawler_bqjr.utils import get_response_by_requests
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads, json_dumps

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, sdch, br",
    "Accept-Language": "zh-CN,zh;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.04",
}

SMS_SLEEP_TIME = 60


@catch_except
def get_qrcode_info(request):
    """
    获取二维码相关信息
    :param request:
    :return:
    """
    ret_data = {}
    try:
        qrurl = "https://qrlogin.taobao.com/qrcodelogin/generateQRCode4Login.do"
        res = get_response_by_requests(qrurl, headers=DEFAULT_HEADERS).json()
        if res.get("success"):
            url = res.get("url", "")
            qrcode_url = "https:" + url if not url.startswith("http") else url
            qrcode_body = get_response_by_requests(qrcode_url, headers=DEFAULT_HEADERS).content
            qrcode_info = {
                "lgToken": res.get("lgToken", ""),
                "adToken": res.get("adToken", ""),
                "qrcode_url": qrcode_url,
                "qrcode_body": bytes.decode(b64encode(qrcode_body))
            }
            ret_data["msg"] = "获取二维码相关信息成功"
            ret_data["data"] = qrcode_info
        else:
            add_ajax_error_json(ret_data, "获取二维码相关信息失败")
    except Exception:
        add_ajax_error_json(ret_data, "获取二维码相关信息出错")
    else:
        add_ajax_ok_json(ret_data)
    finally:
        return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def ask_qrcode_status(request):
    """
    获取扫描二维码状态
    :param request:
    :return:
    """
    ret_data = {}
    succ = False
    need_refresh = False
    try:
        args = request.POST
        username = args["username"]
        account_type = args["account_type"]
        lg_token = args.get("lg_token", "")
        check_url_base = "https://qrlogin.taobao.com/qrcodelogin/qrcodeLoginCheck.do?" \
                         "lgToken={lgToken}&defaulturl=https%3A%2F%2Fwww.taobao.com%2F"
        check_url = check_url_base.format(lgToken=lg_token)
        res_json = get_response_by_requests(check_url, headers=DEFAULT_HEADERS).json()

        session = req_session()
        msg = "通过扫描二维码登录失败"
        code = res_json.get("code")
        if code == "10000":
            msg = "请先扫描二维码"
        elif code == "10001":
            msg = "扫描成功后，请确认登录"
            succ = True
        elif code == "10004":
            msg = "二维码已失效，请重试"
            need_refresh = True
        elif code == "10006":
            redirect_url = res_json.get("url")
            resp = session.get(redirect_url, headers=DEFAULT_HEADERS, verify=False)
            if resp.status_code == 200:
                msg = "登录成功"
                cookies = session.cookies.get_dict(domain='.taobao.com')
                cookies_str = json_dumps(cookies)
                # 将登录成功的cookies信息存入ssdb，供爬虫端使用
                ssdb_connect = get_ssdb_conn()
                key = username + ACCOUNT_CRAWLING_QRCODE_COOKIES_SSDB_SUFFIX + account_type
                ssdb_connect.setx(key, cookies_str, DATA_EXPIRE_TIME)
                succ = True
        else:
            msg = res_json.get("msg", "通过扫描二维码登录失败")
    except Exception:
        msg = "获取扫描二维码状态出错"

    if succ:
        add_ajax_ok_json(ret_data)
    else:
        ret_data["need_refresh"] = need_refresh
        add_ajax_error_json(ret_data, msg)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def send_sms_code(request):
    """
    登录发送短信验证码
    :param request:
    :return:
    """
    ret_data = {}
    try:
        args = request.POST
        session = request.session
        if args.get("is_first", False) == "true":
            username = args["username"].strip()
            account_type = args["account_type"]
            key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + account_type
            ssdb_conn = get_ssdb_conn()
            headers_data = ssdb_conn.get(key)
            if not headers_data:
                add_ajax_error_json(ret_data, "获取短信验证码失败")
                return JsonResponse(ret_data)

            headers_dict = json_loads(headers_data)
            send_url = headers_dict.get("url", "")
            session["send_url"] = send_url
            session["last_send_time"] = time()

            # 第一次会自动发送,默认为发送成功
            res_json = {"stat": "ok", "info": {"sent": True}}
        else:
            last_send_time = session.get("last_send_time", 0)
            need_sleep_time = max(last_send_time + SMS_SLEEP_TIME + 2 - time(), 0) if last_send_time else 0
            sleep(need_sleep_time)

            send_url = session.get("send_url")
            res_json = get_response_by_requests(send_url, headers=DEFAULT_HEADERS).json()
        if res_json.get("stat") == "ok" and res_json.get("info", {}).get("sent"):
            add_ajax_ok_json(ret_data)
        else:
            error_msg = res_json.get("info", {}).get("errorMessage")
            add_ajax_error_json(ret_data, error_msg or "发送短信验证码失败")
    except Exception:
        add_ajax_error_json(ret_data, "发送短信验证码出错")

    return JsonResponse(ret_data)
