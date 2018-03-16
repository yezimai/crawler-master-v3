from base64 import b64encode
from re import compile as re_compile, S as re_S
from time import time

from django.http import JsonResponse
from django.shortcuts import render, reverse
from django.views.decorators.http import require_http_methods
from lxml import etree
from requests import get as http_get, post as http_post
from utils import catch_except, add_ajax_ok_json, add_ajax_error_json

from global_utils import json_loads

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Host": "account.chsi.com.cn"
}
user_reg_error_pattern = re_compile(r'<ul.*?id="user_reg_fm_error_info".*?<span>(.*?)</span>', re_S)
vcode_pattern = re_compile(r'<[^>]+>', re_S)
user_retrivePsd_error_pattern = re_compile(r'<ul.*?id="user_retrivePsd_form_error_info".*?<span>(.*?)</span>', re_S)
ctoken_pattern = re_compile(r'<input.*?name="ctoken".*?value="(.*?)".*?/>', re_S)
key_pattern = re_compile(r'<input.*?name="key".*?value="(.*?)".*?/>', re_S)
clst_pattern = re_compile(r'<input.*?name="clst".*?value="(.*?)".*?/>', re_S)
error_info_pattern = re_compile(r'<ul.*?id=".*?error_info".*?<span>(.*?)</span>', re_S)


def new_cookie_request(func):
    """
    获取同一个requests.session的装饰器
    :param func:
    :return:
    """

    def _deco(*args, **kwargs):
        # 第一个参数必须是request
        url = "https://account.chsi.com.cn/account/password!retrive.action"
        response = http_get(url, headers=HEADERS, verify=False)
        session = args[0].session
        session.set_expiry(0)
        session["req_cookie"] = dict(response.cookies)

        return func(*args, **kwargs)

    return _deco


def get_cookie_request(func):
    """
    获取同一个requests.session的装饰器
    :param func:
    :return:
    """

    def _deco(*args, **kwargs):
        # 第一个参数必须是request
        session = args[0].session
        if "req_cookie" not in session:
            url = "https://account.chsi.com.cn/account/password!retrive.action"
            response = http_get(url, headers=HEADERS, verify=False)
            session.set_expiry(0)
            session["req_cookie"] = dict(response.cookies)

        return func(*args, **kwargs)

    return _deco


@catch_except
@new_cookie_request
def show_xuexin_reg_form(request):
    """
    显示注册界面
    :param request:
    :return:
    """
    return render(request, "public/xuexin/show_xuexin_reg_form.html", locals())


@catch_except
@new_cookie_request
def show_xuexin_find_password_form_step1(request):
    """
    找回密码界面
    https://account.chsi.com.cn/account/forgot/rtvbymphone.action post
    ctoken	9671bdc3552f4ebf96b21ef5fa9ffab0

    https://account.chsi.com.cn/account/password!retrive get
    https://account.chsi.com.cn/account/password!retrive.action post
    loginName	15908143404
    captch	EM5eMc
    :param request:
    :return:
    """
    return render(request, "public/xuexin/show_xuexin_find_password_form_step1.html", locals())


@catch_except
def show_xuexin_find_password_form_step2(request):
    """
    找回密码第二步
    :param request:
    :return:
    """
    return render(request, "public/xuexin/show_xuexin_find_password_form_step2.html", locals())


@catch_except
def show_xuexin_update_password_form(request):
    """
    修改密码界面
    :param request:
    :return:
    """
    return render(request, "public/xuexin/show_xuexin_update_password_form.html", locals())


@catch_except
@new_cookie_request
def show_xuexin_find_username_form(request):
    """
    找回用户名界面

    """
    return render(request, "public/xuexin/show_xuexin_find_username_form.html", locals())


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_reg_request(request):
    """
    发起注册请求
    https://account.chsi.com.cn/account/registerprocess.action
    from	chsi-home
    mphone	15908143404
    ignoremphone	true
    vcode	888888
    password	123456
    password1	123456
    xm	你好
    credentialtype	SFZ
    sfzh	510722198609271058
    from	chsi-home
    email	dddd@qq.com
    pwdreq1
    pwdanswer1
    pwdreq2
    pwdanswer2
    pwdreq3
    pwdanswer3
    continueurl
    serviceId
    serviceNote	1
    serviceNote_res	0
    <ul                                id="user_reg_fm_error_info"                                class="errorMessage"                            >
                        <li><span>邮箱已被使用,可直接登录</span></li>
        </ul>
    :param request:
    :return:
    """
    args = request.POST
    mphone = args.get("mphone", "")
    vcode = args.get("vcode", "")
    password = args.get("password", "")
    password1 = args.get("password1", "")
    xm = args.get("xm", "")
    credentialtype = args.get("credentialtype", "")
    sfzh = args.get("sfzh", "")

    url = "https://account.chsi.com.cn/account/registerprocess.action"
    data = {
        "from": "chsi-home",
        "mphone": mphone,
        "ignoremphone": "true",
        "vcode": vcode,
        "password": password,
        "password1": password1,
        "xm": xm,
        "credentialtype": credentialtype,
        "sfzh": sfzh,
        "email": "",
        "pwdreq1": "",
        "pwdanswer1": "",
        "pwdreq2": "",
        "pwdanswer2": "",
        "pwdreq3": "",
        "pwdanswer3": "",
        "continueurl": "",
        "serviceId": "",
        "serviceNote": "1",
        "serviceNote_res": "0"
    }

    req_cookie = request.session.get("req_cookie")
    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
    result = dict()
    # 使用正则表达式查找user_reg_fm_error_info
    error_msg = user_reg_error_pattern.search(response.text)
    if error_msg:
        add_ajax_error_json(result, error_msg.group(1))
    else:
        result["msg"] = "现在<a href='" + reverse("show_xuexin_crawler_form") + "'>去认证</a>。"
        add_ajax_ok_json(result)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_get_vcode(request):
    """
    获取手机验证码
    https://account.chsi.com.cn/account/getmphonpincode.action  post
    captch:MzxrYm
    mobilePhone:15908143404
    optType:REGISTER
    ignoremphone:true
    :param request:
    :return:
    """
    args = request.POST
    mphone = args.get("mphone", "")
    captch = args.get("captch", "")
    url = "https://account.chsi.com.cn/account/getmphonpincode.action"
    data = {
        "captch": captch,
        "mobilePhone": mphone,
        "optType": "REGISTER",
        "ignoremphone": "true",
    }

    req_cookie = request.session.get("req_cookie")
    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)

    text = response.text.replace("'", "\"")
    text = vcode_pattern.sub('', text)

    result = dict()
    result["result"] = json_loads(text)
    add_ajax_ok_json(result)

    return JsonResponse(result)


@catch_except
@get_cookie_request
def xuexin_get_pic_vcode(request):
    """
    获取图片验证码
    :param request:
    :return:
    """
    url = "https://account.chsi.com.cn/account/captchimagecreateaction.action?time=" \
          + str(int(time()))
    req_cookie = request.session.get("req_cookie")
    response = http_get(url, verify=False, cookies=req_cookie)
    pic_text = b64encode(response.content).decode("utf-8")

    result = dict()
    result["pic"] = pic_text
    add_ajax_ok_json(result)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_check_mobile(request):
    """
    检查手机号是否被注册
    :param request:
    :return:
    """
    mphone = request.POST.get("mphone", "")
    url = "https://account.chsi.com.cn/account/checkmobilephoneother.action"
    data = {
        "mphone": mphone,
        "dataInfo": mphone,
        "optType": "REGISTER"
    }
    req_cookie = request.session.get("req_cookie")
    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)

    result = dict()
    result["result"] = response.text.strip()
    add_ajax_ok_json(result)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_find_password_step1(request):
    """
    学信网找回密码第一步
    :param request:
    :return:
    """
    args = request.POST
    captch = args.get("captch", "")
    mphone = args.get("mphone", "")
    url = "https://account.chsi.com.cn/account/password!retrive.action"
    data = {
        "loginName": mphone,
        "captch": captch
    }
    req_cookie = request.session.get("req_cookie")
    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
    text = response.text
    error_msg = user_retrivePsd_error_pattern.search(text)
    result = {}
    if error_msg:
        add_ajax_error_json(result, error_msg.group(1))
    else:
        result["msg"] = "成功"
        add_ajax_ok_json(result)

        # 进入找回密码的第二步
        # 获取ctoken
        ctoken = ctoken_pattern.search(text)
        if ctoken:
            ctoken = ctoken.group(1)

        data = {"ctoken": ctoken}
        url = "https://account.chsi.com.cn/account/forgot/rtvbymphoneindex.action"
        response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
        result["ctoken"] = ctoken_pattern.search(response.text).group(1)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_find_password_step2(request):
    """
    学信网找回密码第二步
    https://account.chsi.com.cn/account/forgot/rtvbymphone.action post
    captch	88
    mphone	15908143404
    ctoken	9671bdc3552f4ebf96b21ef5fa9ffab0
    xm	胡明星1
    sfzh	510722198609271058

    重置密码短信已发送至15908143404,登录用户名15908143404
    :param request:
    :return:
    """
    args = request.POST
    captch = args.get("captch", "")
    mphone = args.get("mphone", "")
    xm = args.get("xm", "")
    sfzh = args.get("sfzh", "")
    ctoken = args.get("ctoken", "")

    req_cookie = request.session.get("req_cookie")
    url = "https://account.chsi.com.cn/account/forgot/rtvbymphone.action"
    data = {
        "captch": captch,
        "mphone": mphone,
        "ctoken": ctoken,
        "xm": xm,
        "sfzh": sfzh
    }

    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
    text = response.text

    result = dict()
    if "重置密码短信已发送至" in text:
        result["msg"] = "成功"
        add_ajax_ok_json(result)

        key = key_pattern.search(text)
        if key:
            key = key.group(1)
        result["key"] = key

        clst = clst_pattern.search(text)
        if clst:
            clst = clst.group(1)
        result["clst"] = clst
    else:
        err_msg = error_info_pattern.search(text)
        add_ajax_error_json(result, err_msg.group(1) if err_msg else "未知错误")

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_update_password(request):
    """
    修改密码
    https://account.chsi.com.cn/account/forgot/rstpwdbymphone.action  post
    clst	e64e5d78880648f79ca6d145b7653e79
    password	489544240
    key
    password1	489544240
    vcode	111111
    :param request:
    :return:
    """
    args = request.POST
    password = args.get("password", "")
    password1 = args.get("password1", "")
    vcode = args.get("vcode", "")
    key = args.get("key", "")
    clst = args.get("clst", "")
    req_cookie = request.session.get("req_cookie")
    url = "https://account.chsi.com.cn/account/forgot/rstpwdbymphone.action"
    data = {
        "clst": clst,
        "password": password,
        "key": key,
        "password1": password1,
        "vcode": vcode
    }

    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
    text = response.text
    result = dict()
    if "密码重置成功" in text:
        result["msg"] = "密码修改成功"
        add_ajax_ok_json(result)
    else:
        err_msg = error_info_pattern.search(text)
        add_ajax_error_json(result, err_msg.group(1) if err_msg else "未知错误")

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
@get_cookie_request
def xuexin_find_username(request):
    """
    学信网找回用户名
    https://account.chsi.com.cn/account/password!rtvlgname.action post
    captch	88
    xm	胡明星1
    sfzh	510722198609271058

    :param request:
    :return:
    """
    args = request.POST
    captch = args.get("captch", "")
    xm = args.get("xm", "")
    sfzh = args.get("sfzh", "")

    req_cookie = request.session.get("req_cookie")
    url = "https://account.chsi.com.cn/account/password!rtvlgname.action"
    data = {
        "captch": captch,
        "xm": xm,
        "sfzh": sfzh
    }

    response = http_post(url, data=data, headers=HEADERS, verify=False, cookies=req_cookie)
    text = response.text

    result = dict()
    if "找回用户名操作完成" in text:
        add_ajax_ok_json(result)

        tree = etree.HTML(text)
        key = tree.xpath('//td')
        if key:
            msg = '恭喜你，找回用户名成功！您的用户名是: ' + key[0].text
        else:
            msg = ''
        result["msg"] = msg
    else:
        tree = etree.HTML(text)
        error_list = tree.xpath('//ul[@id="user_retrivelgname_fm_error_info"]/li/span')
        add_ajax_error_json(result, error_list[0].text if error_list else "未知错误")

    return JsonResponse(result)
