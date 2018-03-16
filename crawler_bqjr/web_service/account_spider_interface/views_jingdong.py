# coding:utf-8

from base64 import b64encode
from re import compile as re_compile
from time import time, sleep
from urllib.parse import quote

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from lxml import html
from requests import get as http_get, post as http_post
from utils import add_ajax_ok_json, add_ajax_error_json, catch_except

from crawler_bqjr.spiders_settings import ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX
from crawler_bqjr.tools.rsa_tool import RsaNoPadding
from crawler_bqjr.utils import get_js_time
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://safe.jd.com/findPwd/index.action",
    "Host": "safe.jd.com",
    "Connection": "keep-alive",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36"
}
timeout = 10
sourceId = "usersafe"
rsa_pubkey = "b316e0613bb3dd9d42f99f6591912fea92cb6e574c579232c50f259470a363691978d4f88c3959cf9b4d9e97ef9d43c2ad486437507624fc81e025082c9cd275d40fe1b318720099ec791ebae4faa52875dd4c8ae9dc2c17449138206f2110a70a26ba309e5c5e080003ccc2984dfbe9baf355fd0787fd882068c3273f5671e9"
reg_uuid = re_compile(r"doIndex\('([^']+)'")
reg_key_value = re_compile(r'id="keyValue"\s*value="([^"]*)"')
host = "https://safe.jd.com"
eid, fp = ("", "")
sleep_time = 120


def get_cookie_request(func):
    """
    获取同一个requests.session的装饰器
    :param func:
    :return:
    """

    def _deco(*args, **kwargs):
        # 第一个参数必须是request
        session = args[0].session
        if "request_data" not in session:
            url = "https://safe.jd.com/findPwd/index.action"
            response = http_get(url, headers=HEADERS, verify=False)
            index_page = response.text
            element = html.fromstring(index_page)
            other_name = element.xpath('//input[@id="otherId"]/@name')[0]
            other_value = element.xpath('//input[@id="otherId"]/@value')[0]
            uuid = reg_uuid.search(index_page).group(1)

            session.set_expiry(0)
            session["req_cookie"] = dict(response.cookies)
            session["request_data"] = {"other_name": other_name,
                                       "other_value": other_value,
                                       "uuid": uuid
                                       }
        return func(*args, **kwargs)

    return _deco


@catch_except
def show_jingdong_find_password_form_step1(request):
    """
    找回密码第一步，填写用户名
    :param request:
    :return:
    """
    return render(request, "public/ecommerce/jingdong/show_jingdong_find_password_form_step1.html", locals())


@require_http_methods(["GET"])
@catch_except
def show_jingdong_find_password_form_step2(request):
    """
    找回密码第二步，确认身份
    :param request:
    :return:
    """
    try:
        ret_k = request.GET.get("ret_k")
        url = "https://safe.jd.com/findPwd/findPwd.action?k={ret_k}".format(ret_k=ret_k)
        page = http_get(url, headers=HEADERS, verify=False, timeout=timeout).text
        element = html.fromstring(page)
        nickname = element.xpath('//div[@id="mobileDiv"]/div[1]/div[1]/strong/text()')[0]
        mobile = element.xpath('//*[@id="mobileSpan"]/text()')[0].strip()
        template_html = "public/ecommerce/jingdong/show_jingdong_find_password_form_step2.html"
        return render(request, template_html, {"nickname": nickname, "mobile": mobile})
    except Exception:
        return HttpResponseBadRequest("您的账户信息异常，暂时限制找回密码")


@catch_except
def show_jingdong_find_password_form_step3(request):
    """
    找回密码第三步，更新密码
    :param request:
    :return:
    """
    return render(request, "public/ecommerce/jingdong/show_jingdong_find_password_form_step3.html", locals())


@require_http_methods(["POST"])
@catch_except
def get_img_captcha(request):
    """
    获取登录图片验证码
    :param request:
    :return:
    """
    ret_data = {}
    args = request.POST
    username = args["username"].strip()
    account_type = args["account_type"]
    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    key = username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX + account_type
    try:
        ssdb_conn = get_ssdb_conn()
        headers_data = ssdb_conn.get(key)
        if headers_data is not None:
            headers_data_dic = json_loads(headers_data)
            tmp_headers = headers_data_dic.get("headers")
            uuid = headers_data_dic.get("uuid")
            captcha_url = "https://authcode.jd.com/verify/image?a=1&acid={uuid}&" \
                          "yys={stime}".format(uuid=uuid, stime=get_js_time())
            img_content = http_get(captcha_url, headers=tmp_headers, verify=False).content
            ret_data["img_data"] = bytes.decode(b64encode(img_content))
        else:
            add_ajax_error_json(ret_data, "无法获取验证码")
    except Exception:
        add_ajax_error_json(ret_data, "无法获取验证码")
    else:
        add_ajax_ok_json(ret_data)

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
    succ = False
    data = ""
    try:
        args = request.POST
        session = request.session
        if args.get("is_first", False) == "true":
            # 发送短信验证码(间隔120秒)
            # 第一次访问verify_url需要获取ret_key
            username = args["username"].strip()
            if not username:
                add_ajax_error_json(ret_data, "用户名为空")
                return JsonResponse(ret_data)

            account_type = args["account_type"]
            key = username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + account_type
            ssdb_conn = get_ssdb_conn()
            headers_data = ssdb_conn.get(key)
            if not headers_data:
                add_ajax_error_json(ret_data, "获取短信验证码失败")
                return JsonResponse(ret_data)

            headers_dict = json_loads(headers_data)
            verify_url = headers_dict.get("url", "")
            verify_page = http_get(verify_url, headers=HEADERS, verify=False).text
            key_value = reg_key_value.search(verify_page).group(1)
            session["ret_key"] = key_value
            session["last_send_time"] = time()
        else:
            last_send_time = session.get("last_send_time", 0)
            need_sleep_time = max(last_send_time + sleep_time + 2 - time(), 0) if last_send_time else 0
            sleep(need_sleep_time)

        ret_key = session.get("ret_key", "")
        send_url = "https://safe.jd.com/dangerousVerify/getDownLinkCode.action" \
                   "?k={key}&t={stime}".format(key=ret_key, stime=get_js_time())
        ret_json = http_get(send_url, headers=HEADERS, verify=False).json()
        if ret_json:
            if ret_json.get("resultCode") == "0":
                if ret_json.get("retryNum") <= 5:
                    msg = "24小时还可获取%s次短信校验码" % ret_json.get("retryNum")
                else:
                    msg = "短信校验码已发送，请查收短信"
                succ = True
                data = ret_key
            elif ret_json.get("resultMessage") != "":
                msg = "短信验证码发送失败:%s" % ret_json.get("resultMessage", "")
            else:
                msg = "网络连接超时，请重新获取校验码"
        else:
            msg = "登录发送短信验证码失败"

        if succ:
            ret_data["msg"] = msg
            ret_data["data"] = data
            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, msg)
    except Exception:
        add_ajax_error_json(ret_data, "登录发送短信验证码失败")

    return JsonResponse(ret_data)


@catch_except
@get_cookie_request
def get_img_captcha_find_password(request):
    """
    获取找回密码图片验证码
    :param request:
    :return:
    """
    ret_data = {}
    try:
        uuid = request.session.get("request_data", {}).get("uuid")
        code_url = "https://authcode.jd.com/verify/image?acid=%s&srcid=%s&_t=%s" \
                   % (uuid, sourceId, get_js_time())
        captcha_headers = HEADERS.copy()
        captcha_headers.update({
            "Host": "authcode.jd.com",
            "Referer": "https://safe.jd.com/findPwd/index.action",
            "Accept": "image/webp,image/*,*/*;q=0.8"
        })
        code_content = http_get(code_url, headers=captcha_headers, verify=False).content
        ret_data["img_data"] = bytes.decode(b64encode(code_content))
    except Exception:
        add_ajax_error_json(ret_data, "无法获取验证码")
    else:
        add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def fill_in_username(request):
    """
    找回密码第一步：填写账户名
    :param request:
    :return:
    """
    ret_data = {}
    ret_k = None
    try:
        args = request.POST
        session = request.session
        username = args["username"].strip()
        auth_code = args.get("captcha_code", "")
        cookies = session.get("req_cookie")
        other_name = session.get("request_data", {}).get("other_name")
        other_value = session.get("request_data", {}).get("other_value")
        uuid = session.get("request_data", {}).get("uuid")
        post_url = "{host}/findPwd/doIndex.action?&uuid={uuid}&sourceId={sourceId}&" \
                   "authCode={authCode}&username={username}&eid={eid}&fp={fp}&" \
                   "{o_name}={o_value}".format(host=host, uuid=uuid, sourceId=sourceId,
                                               authCode=auth_code, username=username, eid=eid,
                                               fp=fp, o_name=other_name, o_value=other_value)
        ret_json = http_get(post_url, headers=HEADERS, cookies=cookies, verify=False).json()
        result_code = ret_json.get("resultCode")
        if result_code == "ok":
            msg = "第一步成功"
            ret_k = ret_json.get("k")
        elif result_code == "authCodeFailure":
            msg = "验证码错误"
        elif result_code == "none":
            msg = "您输入的账户名不存在，请核对后重新输入"
        elif result_code == "usernameFailure":
            msg = "请输入用户名"
        else:
            msg = "网络连接超时，请重新修改登录密码"

        if ret_k:
            try:
                url = "https://safe.jd.com/findPwd/findPwd.action?k={ret_k}".format(ret_k=ret_k)
                page = http_get(url, headers=HEADERS, verify=False, timeout=timeout).text
                element = html.fromstring(page)
                nickname = element.xpath('//div[@id="mobileDiv"]/div[1]/div[1]/strong/text()')[0]
            except Exception:
                msg = "您的账户信息异常，暂时限制找回密码!"
                add_ajax_error_json(ret_data, msg)
            else:
                ret_data["ret_k"] = ret_k
                add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, msg)
    except Exception:
        add_ajax_error_json(ret_data, "找回密码第一步：填写账户名失败")

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def verify_identify(request):
    """
    找回密码第二步：验证身份
    :param request:
    :return:
    """
    ret_data = {}
    ret_key = None
    try:
        args = request.POST
        ret_k = args.get("ret_k", "")
        sms_code = args.get("sms_code", "")
        post_url = "{host}/findPwd/validFindPwdCode.action?code={sms_code}&k={k}&eid={eid}&fp={fp}"
        post_url = post_url.format(host=host, sms_code=sms_code, k=ret_k, eid=eid, fp=fp)
        ret_json = http_get(post_url, headers=HEADERS).json()
        result = ret_json.get("result")
        if result == "ok":
            msg = "验证手机成功"
            ret_key = ret_json.get("key")
        elif result == "codeFailure":
            msg = "短信验证码错误"
        elif result == "visitLock":
            msg = "短信验证码错误visitLock"
        elif result == "lock":
            msg = "您的账户信息异常，暂时限制找回密码"
        else:
            msg = "网络连接超时，请您稍后重试"

        if ret_key:
            ret_data["ret_key"] = ret_key
            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, msg)
    except Exception:
        add_ajax_error_json(ret_data, "找回密码第二步：验证身份失败")

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def send_sms_code_find_password(request):
    """
    找回密码发送短信验证码
    :param request:
    :return:
    """
    ret_data = {}
    succ = False
    try:
        ret_k = request.POST.get("ret_k", "")
        post_url = "{host}/findPwd/getCode.action?k={ret_k}".format(host=host, ret_k=ret_k)
        ret_page = http_get(post_url, headers=HEADERS).json()
        if ret_page == 0:
            msg = "短信发送成功"
            succ = True
        elif ret_page == "kError":
            msg = "参数错误"
        elif ret_page == 503:
            msg = "120秒内仅能获取一次验证码，请稍后重试"
        elif ret_page == 504:
            msg = "您申请获取短信验证码的次数过多，请于24小时后重试"
        elif ret_page == "lock":
            msg = "您的账户信息异常，暂时限制找回密码"
        elif isinstance(ret_page, dict) and ret_page.get("resultMessage"):
            msg = ret_page["resultMessage"]
        else:
            msg = "发送短信验证码失败，未知错误"
        if succ:
            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, msg)
    except Exception:
        add_ajax_error_json(ret_data, "找回密码发送短信验证码失败")

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def update_password(request):
    """
    找回密码第三步：更新密码
    :param request:
    :return:
    """
    ret_data = {}
    succ = False
    try:
        args = request.POST
        new_password = args.get("new_password")
        key = args.get("ret_key")
        mobile = args.get("mobile")
        need_history_name = args.get("history_name", "")

        # rsa_tool = RsaUtil(key_is_hex=True)
        # en_pwd = rsa_tool.encrypt(new_password, pubkey=rsa_pubkey, get_hex=True)

        rsa_tool = RsaNoPadding(pubkey=rsa_pubkey)
        en_pwd = rsa_tool.encrypt(new_password)

        params = {
            "host": host,
            "key": key,
            "en_newpwd": quote(en_pwd),
            "mobile": mobile,
            "name": quote(need_history_name),
            "eid": eid,
            "fp": fp,
        }
        my_headers = HEADERS.copy()
        referer = "https://safe.jd.com/findPwd/resetPassword.action?key={key}".format(key=key)
        my_headers["Referer"] = referer
        post_url = "{host}/findPwd/doResetPwd.action?key={key}&password={en_newpwd}&" \
                   "mobile={mobile}&historyName={name}&eid={eid}&fp={fp}".format(**params)
        ret_json = http_post(post_url, headers=my_headers, verify=False).json()
        result_code = ret_json.get("resultCode")
        if result_code == "0":
            msg = "重置密码成功"
            succ = True
        elif result_code in ["101", "102", "112", "116", "606",
                             "801", "802", "803", "804"]:
            msg = ret_json.get("resultMessage", "")
        elif result_code == "passwordError":
            msg = "密码设置级别太低"
        elif result_code in ("timeOut", "202"):
            msg = "操作超时"
        elif result_code == "mobileNameError":
            msg = "历史收货人姓名不能为手机号"
        else:
            msg = ret_json.get("resultMessage", "找回密码失败，未知错误")
        if succ:
            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, msg)
    except Exception:
        add_ajax_error_json(ret_data, "找回密码第三步：更新密码失败")

    return JsonResponse(ret_data)
