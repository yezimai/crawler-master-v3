# coding:utf-8

from base64 import b64encode
from datetime import datetime
from io import BytesIO
from random import random as rand_0_1
from re import compile as re_compile, S as re_S
from string import digits, ascii_letters
from urllib.parse import urlencode

import cv2
import numpy
from PIL import Image
from account_spider_interface.models import ZhengXinUserDB
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from lxml import etree
from piltesseract import get_text_from_image
from pytz import utc
from requests import get as http_get, post as http_post, Session as req_session
from utils import catch_except, add_ajax_ok_json, add_ajax_error_json

from crawler_bqjr.settings import USER_AGENT, DEFAULT_REQUEST_HEADERS
from crawler_bqjr.utils import get_js_time

HEADERS = {
    'Referer': 'https://ipcrs.pbccrc.org.cn/top1.do',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
}
pattern_error_user = re_compile(r'<span id="_error_field_">(.*?)</', re_S)  # 用户已注册异常
zhengxin_token_pattern = re_compile(r'TOKEN" value="(\w+)"')
captcha_char_whitelist = digits + ascii_letters


def get_captcha_code(req_ses):
    captcha_code = ""
    headers = HEADERS.copy()
    while len(captcha_code) != 6:
        url = "https://ipcrs.pbccrc.org.cn/imgrc.do?" + get_js_time()
        captcha_body = req_ses.get(url, headers=headers, verify=False)
        captcha_code = parse_capatcha(captcha_body.content)

    return captcha_code


def get_cookie_request(call_time=False):
    """
    获取同一个requests.session的装饰器
    """

    def write_session(func):
        def _deco(*args, **kwargs):
            # 第一个参数必须是request
            session = args[0].session
            if call_time:
                session["req_cookie"] = None

            if not session.get("req_cookie"):
                req_ses = req_session()
                url = "https://ipcrs.pbccrc.org.cn/userReg.do?method=initReg"
                response = req_ses.get(url, headers=HEADERS, verify=False)
                token = etree.HTML(response.content).xpath("//input[@name='org.apache.struts."
                                                           "taglib.html.TOKEN']/@value")[0]
                session.set_expiry(0)
                session["req_cookie"] = response.cookies.get_dict()
                session["token"] = token
                session["captcha_code"] = get_captcha_code(req_ses)  # 获取并解析验证码

            return func(*args, **kwargs)

        return _deco

    return write_session


@catch_except
def user_choose(req):
    """
     首页选项
    :param req:
    :return:
    """
    args = req.GET
    customer_id = args.get("customer_id", "")
    serial_no = args.get("serial_no", "")
    if customer_id and serial_no:
        session = req.session
        session['zhengxin_customer_id'] = customer_id
        session['zhengxin_serial_no'] = serial_no

    return render(req, 'public/zhengxin/show_zhengxin_crawl_login_choose_from.html', locals())


def get_zhengxin_reg_captcha():
    """
    获取图片验证码
    """
    data = {"method": "initReg"}
    kwargs = {"timeout": 6,
              "verify": False,
              }

    _session = req_session()
    _session.headers['User-Agent'] = USER_AGENT
    _session.headers['Referer'] = "https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp"

    resp = _session.post("https://ipcrs.pbccrc.org.cn/userReg.do", data, **kwargs)
    token = zhengxin_token_pattern.search(resp.text).group(1)

    resp = _session.get("https://ipcrs.pbccrc.org.cn/imgrc.do?" + get_js_time())
    captcha_body = resp.content

    return captcha_body, token, _session.cookies


def _get_captcha_body(request):
    cookies = request.session["req_cookie"]
    headers = DEFAULT_REQUEST_HEADERS.copy()
    headers['User-Agent'] = USER_AGENT
    headers["Referer"] = "https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp"
    return http_get("https://ipcrs.pbccrc.org.cn/imgrc.do?a=" + get_js_time(),
                    headers=headers, cookies=cookies.get_dict(), verify=False).content


@catch_except
def get_captcha_body(request):
    captcha_body = _get_captcha_body(request)
    ret_data = {}
    ret_data['img_src'] = bytes.decode(b64encode(captcha_body))
    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def get_zhengxin_AcvitaveCode(request):
    """
        获取短信验证码
    """
    phone_number = request.POST["number"]

    data = {"method": "getAcvitaveCode",
            "mobileTel": phone_number}

    headers = DEFAULT_REQUEST_HEADERS.copy()
    headers["Referer"] = "https://ipcrs.pbccrc.org.cn/userReg.do"
    kwargs = {"timeout": 6,
              "verify": False,
              "headers": headers,
              "cookies": request.session.get("req_cookie")
              }

    resp = http_post("https://ipcrs.pbccrc.org.cn/userReg.do", data, **kwargs)
    text = resp.text

    # TODO 容错
    ret_data = {}
    if resp.status_code == 200 and text:
        add_ajax_ok_json(ret_data)
        ret_data["tcId"] = text
    else:
        add_ajax_error_json(ret_data)

    return JsonResponse(ret_data)


@catch_except
def show_zhengxin_reg(request):
    captcha_body, token, cookies = get_zhengxin_reg_captcha()  # 获取图片验证码以及cookie
    request.session["req_cookie"] = cookies
    return render(request, 'public/zhengxin/show_zhengxin_crawl_register_from.html',
                  {'img_src': bytes.decode(b64encode(captcha_body)),
                   'token': token,
                   })


@require_http_methods(["POST"])
@catch_except
@get_cookie_request(call_time=False)
def zhengxin_user_yanzhen(request):
    """
    用户验证是否已注册
    :param request:
    :return:
    """
    username = request.POST.get('username', '')
    req_cookie = request.session.get('req_cookie')
    url = 'https://ipcrs.pbccrc.org.cn/userReg.do?num=' + str(rand_0_1())
    data = {
        'method': 'checkRegLoginnameHasUsed',
        'loginname': username,
    }
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/userReg.do'
    response = http_post(url=url, data=data, headers=headers, verify=False, cookies=req_cookie)
    result = {}
    if response.text == '0':
        add_ajax_ok_json(result)
    else:
        add_ajax_error_json(result)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
def zhengxin_reg_request(request):
    """
        执行注册第一步
    """
    args = request.POST
    data = {"method": "checkIdentity",
            "1": "on",
            "org.apache.struts.taglib.html.TOKEN": args["org.apache.struts.taglib.html.TOKEN"],
            "userInfoVO.name": args["name"],
            "userInfoVO.certType": args["certType"],
            "userInfoVO.certNo": args["certNo"],
            "_@IMGRC@_": args["Yzm"],
            }
    params = urlencode(data, encoding="gb2312")

    headers = DEFAULT_REQUEST_HEADERS.copy()
    headers['User-Agent'] = USER_AGENT
    headers["Referer"] = "https://ipcrs.pbccrc.org.cn/userReg.do"
    kwargs = {"timeout": 6,
              "verify": False,
              "headers": headers,
              "cookies": request.session.get("req_cookie"),
              "params": params,
              }

    resp = http_post("https://ipcrs.pbccrc.org.cn/userReg.do", **kwargs)

    # TODO 容错
    if resp.status_code == 200:
        text = resp.text
        token = zhengxin_token_pattern.search(text).group(1)
        error_msg = pattern_error_user.search(text)
        if error_msg:
            error_msg = error_msg.group(1).strip()
            if '验证码输入错误' in error_msg or '目前系统尚未收录您的个人信息' in error_msg:
                msg = error_msg
            elif '您已使用其他登录名注册系统并通过验证' in error_msg:
                msg = '您已使用其他登录名注册系统并通过验证,' \
                      '请点击,<a href="/account_spider/zhengxin/back_username/">找回登录名</a>'
            else:
                msg = ""

            captcha_body = _get_captcha_body(request)
            return render(request, 'public/zhengxin/show_zhengxin_crawl_register_from.html',
                          {'img_src': bytes.decode(b64encode(captcha_body)),
                           'token': token,
                           'msg': msg
                           })

        return render(request, 'public/zhengxin/show_zhengxin_crawl_register2_form.html', {'token': token})
    else:
        return HttpResponse("ERROR")


@require_http_methods(["POST"])
@catch_except
def zhengxin_reg2_request(request):
    """
       执行注册第二步
    """
    args = request.POST
    data = {"method": "saveUser",
            "userInfoVO.smsrcvtimeflag": "2",
            "userInfoVO.email": args["email"],
            "org.apache.struts.taglib.html.TOKEN": args["org.apache.struts.taglib.html.TOKEN"],
            "userInfoVO.loginName": args["loginName"],
            "userInfoVO.password": args["password"],
            "userInfoVO.confirmpassword": args["confirmpassword"],
            "userInfoVO.mobileTel": args["mobileTel"],
            "userInfoVO.verifyCode": args["verifyCode"],
            "tcId": args["tcId"],
            }
    params = urlencode(data, encoding="gb2312")

    headers = DEFAULT_REQUEST_HEADERS.copy()
    headers['User-Agent'] = USER_AGENT
    headers["Referer"] = "https://ipcrs.pbccrc.org.cn/userReg.do"
    kwargs = {"timeout": 6,
              "verify": False,
              "headers": headers,
              "cookies": request.session.get("req_cookie"),
              "params": params,
              }

    resp = http_post("https://ipcrs.pbccrc.org.cn/userReg.do", **kwargs)

    # TODO 容错
    ret_data = {}
    if resp.status_code == 200:
        text = resp.text
        error_msg = pattern_error_user.search(text)
        if error_msg:
            add_ajax_error_json(ret_data, error_msg.group(1))
        elif '注册成功' in text:
            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, "注册失败")
    else:
        add_ajax_error_json(ret_data)

    return JsonResponse(ret_data)


#########################################################################
#
#       以下是处理人行银行 问题回答认证
#
#########################################################################


error_pattern = re_compile(r'<div class="erro_div3">.*?<span>(.*?)</div>', re_S)
yanz_pattern = re_compile(r'<span id="_error_field_">(.*?)</span>', re_S)


@require_http_methods(["POST"])
@catch_except
def login(request):
    """
      接收用户登录请求, 如果无误 ,跳转验证选项页面
    :param request:
    :return:
    """
    args = request.POST
    username = args.get('username', '')
    password = args.get('password', '')
    customer_id = args.get('customer_id', '')
    # serial_no = args.get('serial_no', '')
    result = automatic_login(request, username, password, customer_id)

    return JsonResponse(result)


def automatic_login(request, username, password, customer_id):
    """
        自动登录,和普通登录共用!
    """
    req_ses = req_session()
    login_url = 'https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp'
    response = req_ses.get(url=login_url, headers=HEADERS, verify=False)
    response = etree.HTML(response.text)
    # token = response.xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0]
    date = response.xpath("//input[@name='date']/@value")[0]
    datas = {
        "method": "login",
        "date": date,
        "loginname": username,
        "password": password,
        "_@IMGRC@_": ''
    }
    # headers = HEADERS.copy()
    # headers['Referer'] = login_url
    # response = req_ses.post(url='https://ipcrs.pbccrc.org.cn/login.do',
    #                         data=datas, headers=headers, verify=False)
    error_yanz = chuck_login(login_url, req_ses, datas)
    result = {}
    while error_yanz:  # 登录不成功 说明验证码错误
        error_msg = error_yanz.group(1)
        if '验证码输入错误,请重新输入' in error_msg:
            error_yanz = chuck_login(login_url, req_ses, datas)
        else:
            add_ajax_error_json(result, yanz_pattern.search(error_msg).group(1))
            return result

    session = request.session
    session['question_cookies'] = req_ses.cookies.get_dict()
    session['zhengxin_username'] = username
    session['zhengxin_password'] = password
    if customer_id:
        try:
            zh = ZhengXinUserDB.objects.get(customerId=customer_id)
        except ObjectDoesNotExist:
            # 抛出异常说明未查询到数据 ,新添加数据
            zhs = ZhengXinUserDB(customerId=customer_id, username=username, password=password)
            zhs.save()
        else:
            zh.customerId = customer_id
            zh.username = username
            zh.password = password
            zh.save()

    # 验证用户是否存在身份验证,如果存在,则跳转页面如果不存在,则直接跳转问题回答
    htmls = req_ses.get('https://ipcrs.pbccrc.org.cn/reportAction.do?method=applicationReport', verify=False)
    status = etree.HTML(htmls.text).xpath('//font[@class="span-red span-12"]/text()')
    if status:
        status_str = status[0]
        if '成功' in status_str or '已通过' in status_str:
            result['succ'] = True
            result['succ_msg'] = ''
        elif '处理' in status_str:
            result['succ'] = True
            result['succ_msg'] = '账号正在处理中,请耐心等待!'
        else:
            result['succ'] = False

    add_ajax_ok_json(result)
    return result


def chuck_login(login_url, req_ses, datas):
    headers = HEADERS.copy()
    headers['Referer'] = login_url
    datas['_@IMGRC@_'] = get_captcha_code(req_ses)
    response = req_ses.post(url='https://ipcrs.pbccrc.org.cn/login.do',
                            data=datas, headers=headers, verify=False)
    return error_pattern.search(response.text)


@catch_except
def option_question(request):
    """
         选择验证方式
    :param request:
    :return:
    """
    return render(request, 'public/zhengxin/show_zhengxin_crawl_question.html', locals())


question_pattern = re_compile(r'<p>问题<span>(.*?)</span>', re_S)
question_options_pattern = re_compile(r'<p>.*?<input class="radio_type1".*?<span>(.*?)</sp', re_S)


def _get_question_data(prefix, inp):
    return {
        prefix + 'derivativecode': us_gbk(inp[0].xpath('@value')[0]),
        prefix + 'businesstype': us_gbk(inp[1].xpath('@value')[0]),
        prefix + 'questionno': us_gbk(inp[2].xpath('@value')[0]),
        prefix + 'kbanum': us_gbk(inp[3].xpath('@value')[0]),
        prefix + 'question': inp[4].xpath('@value')[0].encode('gb2312', 'replace'),
        prefix + 'options1': us_gbk(inp[5].xpath('@value')[0]),
        prefix + 'options2': us_gbk(inp[6].xpath('@value')[0]),
        prefix + 'options3': us_gbk(inp[7].xpath('@value')[0]),
        prefix + 'options4': us_gbk(inp[8].xpath('@value')[0]),
        prefix + 'options5': us_gbk(inp[9].xpath('@value')[0]),
        prefix + 'answerresult': '',
        prefix + 'options': '',
    }


@catch_except
def option_question_detail(request):
    """
        返回给用户回答问题, 每套题目限时10分钟, 过时退出登录
    :param request:
    :return:
    """
    result = {}
    try:
        session = request.session
        question_cookies = session.get('question_cookies')
        url = 'https://ipcrs.pbccrc.org.cn/reportAction.do?method=applicationReport'
        headers = HEADERS.copy()
        headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/menu.do'
        report_action = http_get(url=url, headers=headers, cookies=question_cookies, verify=False)
        token = etree.HTML(report_action.text).xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0]

        # 获取答题信息
        data = {
            'method': 'checkishasreport',
            'org.apache.struts.taglib.html.TOKEN': token,
            'authtype': '2',
            'ApplicationOption': [25, 24, 21],  # 25 24 21
        }
        url = 'https://ipcrs.pbccrc.org.cn/reportAction.do'
        checkishasreport = http_post(url=url, data=data, headers=headers,
                                     cookies=question_cookies, verify=False)
        n = 0
        data = dict()
        items_options_questions = question_options_pattern.findall(checkishasreport.text)
        for item in question_pattern.findall(checkishasreport.text):
            data[item] = items_options_questions[n:n + 5]
            n += 5

        result['datas'] = data
        # 封装题干信息
        datas = dict()
        x = etree.HTML(checkishasreport.text)
        inps = x.xpath('//div[@class="qustion"]/ul/input')
        count = int(len(inps) / 5)
        datas.update({
            'method': '',
            'org.apache.struts.taglib.html.TOKEN':
                x.xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0],
            'authtype': x.xpath("//input[@name='authtype']/@value")[0],
            'ApplicationOption': [25, 24, 21],  #
        })

        try:
            for i in range(1, 6):
                inp = inps[(i - 1) * count:i * count - 1]
                prefix = 'kbaList[' + str(i - 1) + '].'
                datas.update(_get_question_data(prefix, inp))
                n += 1
            session['quest_data'] = datas
        except IndexError:
            add_ajax_error_json(result, x.xpath('//div[@class="erro_div1"]/text()')[0])
        else:
            add_ajax_ok_json(result)
    except Exception:
        from traceback import print_exc
        print_exc()
        add_ajax_error_json(result, "发生异常")
    finally:
        return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
def submit_question(request):
    """
        用户提交答案:
    :param request:
    :return:
    """
    args = request.POST
    session = request.session
    # awsers = args.get('st')
    datas = session.get('quest_data')
    cookies = session.get('question_cookies')
    for x in range(5):
        i = str(x)
        datas['kbaList[' + i + '].answerresult'] = args.get("st[key[" + i + "].options]")
        datas['kbaList[' + i + '].options'] = args.get("st[key[" + i + "].options]")

    url = 'https://ipcrs.pbccrc.org.cn/reportAction.do?method=submitKBA'
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/reportAction.do?method=checkishasreport'
    response = http_post(url=url, data=datas, headers=headers, cookies=cookies, verify=False)
    result = dict()
    try:
        msg = etree.HTML(response.text).xpath('//div[@class="span-grey2 span-14 p1 margin_top_80"]')[0]
        if '您的查询申请已提交' in msg.xpath('string(.)'):
            result['msg'] = msg.xpath('string(.)')
            add_ajax_ok_json(result)
        else:
            add_ajax_error_json(result)
    except Exception:
        add_ajax_error_json(result)
        result['msg'] = "用户提交异常,请<a href='/account_spider/zhengxin/'>返回</a>重新提交;"

    return JsonResponse(result)


def us_gbk(value):
    if value >= '\u4e00' and value[:-1] <= '\u9fa5':
        value = value.encode('gb2312', 'replace')
    return value.strip()


###############################################################################
#
#  找回登录名
#
###############################################################################

@catch_except
def back_username(request):
    """
        返回找回登录页面
    :param request:
    :return:
    """
    return render(request, 'public/zhengxin/show_zhengxin_back_username_from.html', locals())


back_error_pattern = re_compile(r'<span id="_@MSG@_" class="p4">(.*?)<', re_S)
back_error_user_pattern = re_compile(r'<span id="_error_field_">(.*?)</', re_S)


@require_http_methods(["POST"])
@catch_except
def back_chuck_username(request):
    """
    提交找回用户需要的信息
    :param request:
    :return:
    """
    args = request.POST
    user = args['name']
    certNO = args['certNo']
    certType = args['certType']
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp'
    url = "https://ipcrs.pbccrc.org.cn/findLoginName.do?method=init"
    req_ses = req_session()
    response = req_ses.get(url=url, headers=headers, verify=False)
    token = etree.HTML(response.text).xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0]
    # 您无法使用该功能找回登录名，可能是因为您的安全等级为低、未注册或已销户，请重新注册
    # 您的登录名已短信发送至平台预留的手机号码，请查收。
    # 若您在5分钟内未收到短信或您的手机号码已修改，请使用“用户销户”功能先销户后再重新注册。
    data = {
        'org.apache.struts.taglib.html.TOKEN': token,
        'method': 'findLoginName',
        'name': user.encode('gb2312', 'replace'),
        'certType': certType,
        'certNo': certNO,
        '_@IMGRC@_': '',
    }
    error_msg1, error_msg2 = find_username(req_ses, data)
    result = {}
    while error_msg1:
        error_msg1, error_msg2 = find_username(req_ses, data)
    else:
        if error_msg2:
            add_ajax_error_json(result, error_msg2.group(1))
        else:
            result['msg'] = '您的登录名已短信发送至平台预留的手机号码，请查收。' \
                            '<br/>若您在5分钟内未收到短信或您的手机号码已修改，' \
                            '请使用“用户销户”功能先销户后再重新注册。'
            add_ajax_ok_json(result)

    return JsonResponse(result)


def find_username(req_ses, datas):
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/findLoginName.do?method=init'
    datas['_@IMGRC@_'] = get_captcha_code(req_ses)
    response = req_ses.post(url='https://ipcrs.pbccrc.org.cn/findLoginName.do',
                            data=datas, headers=headers, verify=False)
    text = response.text
    return back_error_pattern.search(text), back_error_user_pattern.search(text)


##################################################################################
#
#  找回密码
#
##################################################################################

@catch_except
def back_passwd(request):
    """
        返回找回密码输入页
    :param request:
    :return:
    """
    return render(request, 'public/zhengxin/show_zhengxin_back_passwd_from.html', locals())


passwd_error_pattern = re_compile(r'<span id="_error_field_">(.*?)</', re_S)


@require_http_methods(["POST"])
@catch_except
def back_chuck_passwd(request):
    """
        处理第一步找回密码信息
    :param request:
    :return:
    """
    args = request.POST
    loginName = args['loginName']
    name = args['name']
    certNo = args['certNo']
    certType = args['certType']
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp'
    url = 'https://ipcrs.pbccrc.org.cn/resetPassword.do?method=init'
    req_ses = req_session()
    response = req_ses.get(url=url, headers=headers, verify=False)
    token = etree.HTML(response.text).xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0]
    datas = {
        'org.apache.struts.taglib.html.TOKEN': token,
        'method': 'checkLoginName',
        'loginname': loginName,
        'name': name.encode('gb2312', 'replace'),
        'certType': certType,
        'certNo': certNo,
        '_@IMGRC@_': '',
    }
    phone, error_msg1, error_msg2 = find_password(req_ses, datas)
    msg = ''
    while error_msg1:
        error_msg = error_msg1.group(1)
        if '验证码输入错误,请重新输入' in error_msg:
            phone, error_msg1, error_msg2 = find_password(req_ses, datas)

    if error_msg2:
        msg = error_msg2.group(1)

    if phone:
        request.session['passwd_cookies'] = req_ses.cookies.get_dict()
        return render(request, 'public/zhengxin/show_zhengxin_back_passwd2_from.html', locals())

    return render(request, 'public/zhengxin/show_zhengxin_back_passwd_from.html', locals())


@require_http_methods(["POST"])
@catch_except
def back_chuck2_passwd(request):
    """
        处理第二步,设置新密码 和验证码
    :param request:
    :return:
    """
    args = request.POST
    session = request.session
    passwd_cookies = session.get('passwd_cookies')
    passwd = args.get('passwd')
    passwd1 = args.get('passwd1')
    vcode = args.get('vcode')
    data = {
        'method': 'resetPassword',
        'counttime': '99',
        'password': passwd,
        'confirmpassword': passwd1,
        'verifyCode': vcode
    }
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/resetPassword.do'
    response = http_post(url='https://ipcrs.pbccrc.org.cn/resetPassword.do',
                         data=data, headers=headers, cookies=passwd_cookies, verify=False)
    token = ''
    try:
        token = etree.HTML(response.text).xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0]
    except Exception:
        pass
    if token == '':
        return HttpResponse('手机状态码已经过期,请重新获取.')
    datas = {
        'org.apache.struts.taglib.html.TOKEN': token,
        'method': 'chooseCertify',
        'authtype': '2'
    }
    resetPassword = http_post(url='https://ipcrs.pbccrc.org.cn/resetPassword.do',
                              data=datas, headers=headers, cookies=passwd_cookies, verify=False)
    result = {}
    n = 0
    data = dict()

    items_options_questions = question_options_pattern.findall(resetPassword.text)
    for item in question_pattern.findall(resetPassword.text):
        data[item] = items_options_questions[n:n + 5]
        n += 5

    # 封装题干信息
    result['datas'] = data
    datas = dict()
    x = etree.HTML(resetPassword.text)
    inps = x.xpath('//div[@class="qustion"]/ul/input')
    count = int(len(inps) / 5)
    try:
        for i in range(1, 6):
            inp = inps[(i - 1) * count:i * count - 1]
            prefix = 'kbaList[' + str(i - 1) + '].'
            datas.update(_get_question_data(prefix, inp))
            n += 1
            datas.update({
                'method': 'saveKbaApply',
                'org.apache.struts.taglib.html.TOKEN':
                    x.xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value")[0],
            })
        session['submit_passwd_quest_data'] = datas
    except IndexError:
        add_ajax_error_json(result, x.xpath('//span[@id="_error_field_"]/text()')[0])
    else:
        add_ajax_ok_json(result)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
def back_submit_passwd_question(request):
    args = request.POST
    session = request.session
    # awsers = args.get('dict')
    datas = session.get('submit_passwd_quest_data')
    passwd_cookies = session.get('passwd_cookies')
    for x in range(5):
        i = str(x)
        datas['kbaList[' + i + '].answerresult'] = args.get("dict[key[" + i + "].options]")
        datas['kbaList[' + i + '].options'] = args.get("dict[key[" + i + "].options]")

    url = 'https://ipcrs.pbccrc.org.cn/resetPassword.do'
    headers = HEADERS.copy()
    headers['Referer'] = url
    response = http_post(url=url, data=datas, headers=headers, cookies=passwd_cookies, verify=False)
    test = ''
    try:
        test = etree.HTML(response.text).xpath('//font[@class="span-14 padding_left_130"]/text()')[0]
    except Exception:
        pass

    result = {}
    if '您的重置密码申请已提交' in test:
        result['msg'] = test
        add_ajax_ok_json(result)
    else:
        add_ajax_error_json(result, "重置密码失败")

    return JsonResponse(result)


@catch_except
def back_phone_vcode(req):
    """
        返回手机验证码
    :param req:
    :return:
    """
    passwd_cookies = req.session.get('passwd_cookies')
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/resetPassword.do'
    url = 'https://ipcrs.pbccrc.org.cn/resetPassword.do?num=' + str(rand_0_1())
    data = {
        'method': 'getAcvitaveCode',
        'counttime': '119',
    }
    response = http_post(url=url, data=data, headers=headers, cookies=passwd_cookies, verify=False)
    result = dict()
    if 'success' in response.text:
        add_ajax_ok_json(result)
    else:
        add_ajax_error_json(result)

    return JsonResponse(result)


def find_password(req_ses, datas):
    headers = HEADERS.copy()
    headers['Referer'] = 'https://ipcrs.pbccrc.org.cn/resetPassword.do?method=init'
    datas['_@IMGRC@_'] = get_captcha_code(req_ses)
    response = req_ses.post(url='https://ipcrs.pbccrc.org.cn/resetPassword.do',
                            data=datas, headers=headers, verify=False)
    text = response.text

    phone = ''
    try:
        phone = etree.HTML(text).xpath('//span[@class="user_text span-14 span-grey"]/text()')[0]
    except Exception:
        pass

    return phone, back_error_pattern.search(text), passwd_error_pattern.search(text)


###################################################################
#
# 征信首页 ,身份验证码 二级处理
#
####################################################################

@require_http_methods(["GET"])
@catch_except
def zhenxin_user_login(req):
    """
      征信登录请求
    :param req:
    :return:
    """
    customer_id = req.GET.get("customer_id", "")
    if customer_id:
        try:
            zh = ZhengXinUserDB.objects.get(customerId=customer_id)
            fu_time = zh.pubDate
            fu_time = datetime.strptime(fu_time.astimezone(utc).strftime('%Y-%m-%d %H:%M:%S'),
                                        '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - fu_time).days < 1:  # 大于1 时间过去24 则认为无效 需要重新登录
                result = automatic_login(req, zh.username, zh.password, customer_id)
                if result['status'] == "ok":
                    try:
                        if result['succ']:  # 找不到此字段会抛出异常
                            if result['succ_msg'] == '':  # 报告已生成
                                return HttpResponseRedirect('/account_spider/zhengxin/login_form/')
                            # TODO 报告正在处理中的情况
                        else:
                            return HttpResponseRedirect('/account_spider/zhengxin/option_question/')
                    except Exception:
                        return HttpResponseRedirect('/account_spider/zhengxin/option_question/')
        except Exception:
            pass

    return render(req, 'public/zhengxin/show_zhengxin_crawl_login_from.html', locals())


def parse_capatcha(captcha_body):
    with BytesIO(captcha_body) as captcha_filelike, Image.open(captcha_filelike) as img:
        # img.show()

        # 构造算子为32位浮点三维矩阵kernel：[(1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
        #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
        #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
        #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
        #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)]
        # kernel = numpy.ones((5, 5), numpy.float32) / 19
        # sobelX = numpy.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
        # sobelY = numpy.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]])
        # kernel = numpy.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])

        # 做卷积去噪点
        eroded = numpy.array(img)
        eroded = cv2.fastNlMeansDenoisingColored(eroded)

        mask_img_arr = numpy.zeros((eroded.shape[0], eroded.shape[1]), numpy.uint8)
        dst_img = numpy.array(img)
        cv2.inpaint(eroded, mask_img_arr, 10, cv2.INPAINT_TELEA, dst=dst_img)

        # 图像灰度化处理
        eroded = cv2.cvtColor(eroded, cv2.COLOR_BGR2GRAY)

        # 图像二值化处理
        ret, eroded = cv2.threshold(eroded, 125, 255, cv2.THRESH_BINARY)

        dest_img = Image.fromarray(eroded)
        code = get_text_from_image(dest_img,
                                   tessedit_char_whitelist=captcha_char_whitelist).replace(' ', '')
        dest_img.close()

    return code
