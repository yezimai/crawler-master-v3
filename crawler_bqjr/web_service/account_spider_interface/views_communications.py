# -*- coding: utf-8 -*-

from base64 import b64encode
from random import randint, random as rand_0_1
from time import strftime
from urllib.parse import urlencode

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from requests import post as http_post, get as http_get
from utils import catch_except, add_ajax_ok_json, add_ajax_error_json

from crawler_bqjr.spiders.communications_spiders.phone_num_util import get_phone_info
from crawler_bqjr.spiders_settings import ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX, ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX
from crawler_bqjr.tools.dianxin_data_convert import DXConvertData
from crawler_bqjr.utils import get_js_time
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads, json_dumps
from .views import get_crawling_data


@require_http_methods(["POST"])
@catch_except
def check_communications(request):
    """检查号码所属运营商"""
    ret_data = {}
    username = request.POST["username"].strip()

    if not username:
        add_ajax_error_json(ret_data, "号码为空")
        return JsonResponse(ret_data)

    phone_brand = check_phone_type(username)
    if phone_brand:
        add_ajax_ok_json(ret_data)
        if phone_brand in ["移动", "联通", "电信"]:
            ret_data['brand'] = phone_brand
        else:
            ret_data['brand'] = ""
    else:
        add_ajax_error_json(ret_data, "无法获取号码信息")

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def get_img_captcha(request):
    """获取图片验证码"""
    ret_data = {}
    args = request.POST
    username = args["username"].strip()
    account_type = args["account_type"]
    url = "http://shop.10086.cn/i/authImg?t=" + str(rand_0_1())

    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    key = username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX + account_type
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            img_content = http_get(url, headers=eval(headers)).content
            ret_data["img_data"] = bytes.decode(b64encode(img_content))
        else:
            add_ajax_error_json(ret_data, "无法获取图片验证码")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取图片验证码")
    else:
        add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def get_sms_captcha(request):
    """发送短信验证码"""
    args = request.POST
    username = args["username"].strip()

    if not username:
        ret_data = {}
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    phone_brand = check_phone_type(username)
    if "移动" == phone_brand:
        return _get_mobile_sms_captcha(args)
    elif "联通" == phone_brand:
        return _get_unicom_sms_captcha(args)
    elif "电信" == phone_brand:
        return _get_telecom_sms_captcha(args)

    return HttpResponseBadRequest()


def check_phone_type(phone):
    """检查手机号类型"""
    try:
        return get_phone_info(phone)["brand"]
    except Exception:
        return None


def _get_mobile_sms_captcha(args):
    """移动发送短信验证码"""
    sms_type = args["sms_type"]
    if sms_type == "login":
        return _get_mobile_login_sms_captcha(args)
    elif sms_type == "general":
        return _get_mobile_bills_sms_captcha(args)
    else:
        return HttpResponseBadRequest()


def _get_mobile_login_sms_captcha(args):
    """移动发送登录短信验证码"""
    ret_data = {}
    username = args["username"].strip()
    url = "https://login.10086.cn/sendRandomCodeAction.action"

    form_data = {
        "userName": username,
        "type": "01",
        "channelID": "12003"
    }

    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            sms_content = http_post(url, headers=eval(headers), data=form_data, verify=False).text
            if sms_content == '0':
                add_ajax_ok_json(ret_data)
            elif sms_content == '2':
                add_ajax_error_json(ret_data, "当日短信验证码已达上限，请明天再试！")
            else:
                add_ajax_error_json(ret_data, "短信验证码发送失败，请重试!")
        else:
            add_ajax_error_json(ret_data, "无法获取短信验证码，请刷新页面重试！")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取短信验证码，请重试。")

    return JsonResponse(ret_data)


def _get_mobile_bills_sms_captcha(args):
    """移动发送账单短信验证码"""
    ret_data = {}
    username = args["username"].strip()
    form_data = {"callback": "jQuery1830" + str(randint(1E16, 1E17 - 1)) + "_" + get_js_time(),
                 "_": get_js_time(),
                 }
    url = "https://shop.10086.cn/i/v1/fee/detbillrandomcodejsonp/" + username + "?" + urlencode(form_data)

    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            sms_content = http_get(url, headers=eval(headers), verify=False).content.decode()
            if '"retCode":"000000"' in sms_content:  # 成功
                add_ajax_ok_json(ret_data)
            elif '"retCode":"570007"' in sms_content:  # 系统繁忙！
                add_ajax_error_json(ret_data, "系统繁忙，请重试。")
            else:
                add_ajax_error_json(ret_data, sms_content)
        else:
            add_ajax_error_json(ret_data, "无法获取短信验证码，请刷新页面重试！")
    except Exception:
        add_ajax_error_json(ret_data, "获取短信验证码失败，请重试。")

    return JsonResponse(ret_data)


def _get_unicom_sms_captcha(args):
    """联通发送短信验证码"""
    sms_type = args["sms_type"]
    if sms_type == "login":
        return _get_unicom_login_sms_captcha(args)
    elif sms_type == "general":
        return _get_unicom_bills_sms_captcha(args)
    else:
        return HttpResponseBadRequest()


def _get_unicom_login_sms_captcha(args):
    """联通发送登录ck短信验证码"""
    ret_data = {}
    username = args["username"].strip()
    the_time = get_js_time()

    form_data = {'mobile': username,
                 'req_time': the_time,
                 '_': int(the_time) + 1,
                 'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                 }
    # url = "https://uac.10010.com/portal/Service/SendCkMSG?" + urlencode(form_data)
    url = "https://uac.10010.com/portal/Service/SendCkMSG"
    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]

    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            sms_content = http_get(url, headers=eval(headers), params=form_data, verify=False).text
            if 'resultCode:"0000"' in sms_content:
                add_ajax_ok_json(ret_data)
            elif 'resultCode:"4000"' in sms_content or 'resultCode:"7096"' in sms_content:
                add_ajax_error_json(ret_data, "系统忙，请稍后再试!")
            else:
                add_ajax_error_json(ret_data, "发送失败：" + sms_content)
        else:
            add_ajax_error_json(ret_data, "无法获取短信验证码，请刷新页面重试！")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取短信验证码，请重试。")

    return JsonResponse(ret_data)


def _get_unicom_bills_sms_captcha(args):
    """联通发送一般短信验证码"""
    ret_data = {}
    username = args["username"].strip()
    the_time = get_js_time()

    form_data = {'mobile': username,
                 'req_time': the_time,
                 '_': int(the_time) + 1,
                 'callback': "jQuery1720" + str(randint(1E16, 1E17 - 1)) + "_" + the_time
                 }
    # url = "https://uac.10010.com/portal/Service/SendMSG?" + urlencode(form_data)
    url = "https://uac.10010.com/portal/Service/SendMSG"
    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]

    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            sms_content = http_get(url, headers=eval(headers), params=form_data, verify=False).text
            if 'resultCode:"0000"' in sms_content:
                add_ajax_ok_json(ret_data)
            elif 'resultCode:"7096"' in sms_content:  # 验证码请求过快
                add_ajax_error_json(ret_data, "验证码请求过快，请稍后再试。")
            elif 'resultCode:"7098"' in sms_content:  # 7098谁请求达到上限
                add_ajax_error_json(ret_data, "请求短信验证码达到上限，请明天再试!")
            else:
                add_ajax_error_json(ret_data, "发送失败：" + sms_content)
        else:
            add_ajax_error_json(ret_data, "无法获取短信验证码，请刷新页面重试！")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取短信验证码，请重试。")

    return JsonResponse(ret_data)


def _get_telecom_sms_captcha(args):
    """电信发送短信验证码"""
    sms_type = args["sms_type"]
    if sms_type == "general":
        return _get_telecom_bills_sms_captcha(args)
    else:
        return HttpResponseBadRequest()


CSERVICE_HEADERS = {
    "User-Agent": "Huawei DUK-AL20/6.2.1",
    "Content-Type": "text/xml",
    "Connection": "Keep-Alive",
    "Host": "cservice.client.189.cn:8004"
}


def _get_telecom_bills_sms_captcha(args):
    """电信发送一般短信验证码"""
    ret_data = {}
    username = args["username"].strip()
    dx_conver = DXConvertData()

    url = "http://cservice.client.189.cn:8004/map/clientXML?encrypted=true"
    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            token = json_loads(headers)["token"]
            form_data = {
                "Request": {
                    "HeaderInfos": {
                        "ClientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                        "Source": "110003",
                        "SourcePassword": "Sid98s",
                        "Token": token,
                        "UserLoginName": username,
                        "Code": "getRandomV2",
                        "Timestamp": strftime("%Y%m%d%H%M%S"),
                    },
                    "Content": {
                        "Attach": "test",
                        "FieldData": {
                            "PhoneNbr": username,
                            "SceneType": "7",
                            "Imsi": {}
                        }
                    }
                }
            }
            form_str = dx_conver.convert_request_data(form_data)
            sms_text = http_post(url, headers=CSERVICE_HEADERS, data=form_str, verify=False).text

            sms_dict = dx_conver.convert_response_data(sms_text)
            sms_str = json_dumps(sms_dict, ensure_ascii=False)
            if '"ResultCode":{"value":"0000"}' in sms_str:
                add_ajax_ok_json(ret_data)
            elif "服务中断" in sms_text:
                add_ajax_error_json(ret_data, "电信服务中断，请稍后再试！")
            else:
                add_ajax_error_json(ret_data, "发送失败：" + sms_str)
        else:
            add_ajax_error_json(ret_data, "无法获取短信验证码，请刷新页面重试！")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取短信验证码，请重试。")

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def check_sms_timeout(request):
    """检测短信验证码是否超时"""
    ret_data = {}
    args = request.POST
    account_type = args["account_type"]
    username = args["username"].strip()

    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    ssbd_connect = get_ssdb_conn()
    try:
        crawling_info = ssbd_connect.get(username + ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX + account_type)
        ret_data.update(get_crawling_data(ssbd_connect, username, account_type, crawling_info))
    except Exception:
        add_ajax_error_json(ret_data, "获取用户状态失败")
    else:
        add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def telecom_bills_validation(request):
    """电信账单验证"""
    ret_data = {}
    args = request.POST
    username = args["username"].strip()
    sms_captcha = args["sms_captcha"]
    name = args["name"]
    id_card = args["id_card"]
    dx_conver = DXConvertData()

    url = "http://cservice.client.189.cn:8004/map/clientXML?encrypted=true"
    key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + args["account_type"]
    try:
        ssdb_conn = get_ssdb_conn()
        headers = ssdb_conn.get(key)
        if headers is not None:
            token = json_loads(headers)["token"]
            form_data = {
                "Request": {
                    "HeaderInfos": {
                        "ClientType": "#6.2.1#channel8#Huawei DUK-AL20#",
                        "Source": "110003",
                        "SourcePassword": "Sid98s",
                        "Token": token,
                        "UserLoginName": username,
                        "Code": "randomCodeAndAuthValidate",
                        "Timestamp": strftime("%Y%m%d%H%M%S"),
                    },
                    "Content": {
                        "Attach": "test",
                        "FieldData": {
                            "ShopId": "20002",
                            "IdCardNum": id_card,
                            "RandomCode": sms_captcha,
                            "PhoneNum": username,
                            "Username": name,
                            "ValidateType": "1"
                        }
                    }
                }
            }
            form_str = dx_conver.convert_request_data(form_data)
            res_content = http_post(url, headers=CSERVICE_HEADERS, data=form_str, verify=False)

            # 返回数据解密
            res_dict = dx_conver.convert_response_data(res_content.text)
            res_str = json_dumps(res_dict, ensure_ascii=False)

            if '"ResultCode": {"value": "0000"}' in res_str:
                add_ajax_ok_json(ret_data)
            elif '"ResultCode": {"value": "0001"}' in res_str:
                add_ajax_error_json(ret_data, "非实名制用户")
            elif '"ResultCode": {"value": "9152"}' in res_str:
                add_ajax_error_json(ret_data, "验证码错误！")
            else:
                add_ajax_error_json(ret_data, "验证失败，请重试：" + res_str)
        else:
            add_ajax_error_json(ret_data, "验证失败，没有用户信息，请刷新重试。")
    except Exception:
        add_ajax_error_json(ret_data, "验证失败，请重试。")

    return JsonResponse(ret_data)
