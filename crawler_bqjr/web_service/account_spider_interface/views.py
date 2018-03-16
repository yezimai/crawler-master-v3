# -*- coding: utf-8 -*-

from base64 import b64decode

from captchas_upload.views import save_captcha_2_file
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from requests import post as http_post
from utils import catch_except, add_ajax_ok_json, add_ajax_error_json, rsa_long_decrypt

from crawler_bqjr.spiders.communications_spiders.phone_num_util import get_phone_info
from crawler_bqjr.spiders_settings import AccountType_2_SpiderName_DICT, \
    ACCOUNT_CRAWLING_QUEUE_SSDB_SUFFIX, COMMUNICATIONS_BRAND_DICT, USERINFO_DICT, \
    HOUSEFUND_CITY_DICT, SHEBAO_CITY_DICT, BANK_DICT, ZHENANGXIN_DICT, \
    EMAIL_DICT, OTHER_EMAIL_SPIDER_NAME
from crawler_bqjr.spiders_settings import DATA_EXPIRE_TIME, \
    ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX, ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX, ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX, ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX, ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX, ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX, \
    ACCOUNT_CRAWLING_IMG_DESCRIBE_SSDB_SUFFIX, ACCOUNT_CRAWLING_NEED_NAME_IDCARD_SMS_SSDB_SUFFIX
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_dumps as data_dumps, json_loads as data_loads
from constants_settings import WEB_SETTINGS_ACCESS_DOMAIN

CAPTCHA_DIR = settings.CAPTCHA_DIR
CHECK_STATUS_LIST = [None, "error"]
if settings.DEBUG:
    CHECK_STATUS_LIST.append("done")


def get_customer_id_context(request):
    args = request.GET
    session = request.session
    customer_id = args.get("customer_id", "") or session.get("customer_id", "")
    serial_no = args.get("serial_no", "") or session.get("serial_no", "")
    session["customer_id"] = customer_id
    session["serial_no"] = serial_no

    return {'customer_id': customer_id,
            'serial_no': serial_no,
            }


def render_with_customer_id(request, template_name, context=None,
                            content_type=None, status=None, using=None):
    new_context = get_customer_id_context(request)
    if context:
        new_context.update(context)
    return render(request, template_name, new_context, content_type, status, using)


@require_http_methods(["GET"])
@catch_except
def show_communications_crawler_form(request):
    return render_with_customer_id(request, 'public/show_communications_crawler_form.html')


@require_http_methods(["GET"])
@catch_except
def show_5xian1jin_crawler_form(request):
    return render_with_customer_id(request, 'show_5xian1jin_crawler_form.html')


@require_http_methods(["GET"])
@catch_except
def show_bank_crawler_form(request):
    return render_with_customer_id(request, 'show_bank_crawler_form.html')


@require_http_methods(["GET"])
@catch_except
def show_ecommerce_jingdong_crawler_form(request):
    return render_with_customer_id(request, "public/ecommerce/jingdong/show_jingdong_crawler_form.html")


@require_http_methods(["GET"])
@catch_except
def show_ecommerce_taobao_crawler_form(request):
    return render_with_customer_id(request, "public/ecommerce/taobao/show_taobao_crawler_form.html")


@require_http_methods(["GET"])
@catch_except
def show_ecommerce_alipay_crawler_form(request):
    return render_with_customer_id(request, "public/ecommerce/alipay/show_alipay_crawler_form.html")


@require_http_methods(["GET"])
@catch_except
def show_xuexin_crawler_form(request):
    return render_with_customer_id(request, "public/xuexin/show_xuexin_crawler_form.html")


@require_http_methods(["GET"])
@catch_except
def show_qq_qrcode_login(request):
    return render_with_customer_id(request, "public/email/show_qq_qrcode_form.html")


@require_http_methods(["GET"])
@catch_except
def show_emailbill_crawler_form(request):
    return render_with_customer_id(request, "public/email/show_credit_card_email_form.html")


@require_http_methods(["GET"])
@catch_except
def show_zhengxin_crawler_form(request):
    session = request.session
    customer_id = session.get('zhengxin_customer_id', "")
    serial_no = session.get('zhengxin_serial_no', "")
    username = session['zhengxin_username']
    password = session['zhengxin_password']
    return render(request, "public/zhengxin/show_zhengxin_crawl_shibie.html", locals())


def push_data_2_ssbd(username, spider_name, account_type, ssdb_data, crawling_info=""):
    ssdb_conn = get_ssdb_conn()

    ssdb_conn.multi_del(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_IMG_HEADERS_SSDB_SUFFIX + account_type,
                        username + ACCOUNT_CRAWLING_SMS_HEADERS_SSDB_SUFFIX + account_type,
                        # username + ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX + account_type,
                        )

    ssdb_conn.setx(username + ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX + account_type,
                   "crawling", DATA_EXPIRE_TIME)
    ssdb_conn.setx(username + ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX + account_type,
                   crawling_info, DATA_EXPIRE_TIME)
    ssdb_conn.qpush_back(spider_name + ACCOUNT_CRAWLING_QUEUE_SSDB_SUFFIX,
                         data_dumps(ssdb_data))


def _format_ssdb_data(args):
    return {"username": args["username"].strip(),
            "password": args["password"].strip(),
            "customer_id": args.get("customer_id", ""),
            "serial_no": args.get("serial_no", ""),
            }


def _handle_communications_crawling(args):
    """
    运营商爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data, "号码为空")
        return JsonResponse(ret_data)

    info = get_phone_info(username)

    if info:
        brand = info["brand"]

        if brand in COMMUNICATIONS_BRAND_DICT:
            if brand == "电信":
                add_ajax_error_json(ret_data, "暂不支持" + brand)
                return JsonResponse(ret_data)

            spider_name = COMMUNICATIONS_BRAND_DICT[brand]
            account_type = args["account_type"].strip()

            ssdb_data = _format_ssdb_data(args)
            ssdb_data.update(info)

            crawling_info = "".join([info["province"], info["city"], brand, ":", username])
            push_data_2_ssbd(username, spider_name, account_type, ssdb_data, crawling_info)

            add_ajax_ok_json(ret_data)
        else:
            add_ajax_error_json(ret_data, "不支持" + brand)
    else:
        add_ajax_error_json(ret_data, "无法获取号码信息")

    return JsonResponse(ret_data)


def _handle_5xian1jin_crawling(args, account_type):
    """
    五险一金爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    city = args["city"].strip()
    try:
        if "housefund" == account_type:
            spider_name = HOUSEFUND_CITY_DICT[city]
        else:
            spider_name = SHEBAO_CITY_DICT[city]
    except KeyError:
        add_ajax_error_json(ret_data, "暂不支持该城市")
        return JsonResponse(ret_data)

    ssdb_data = _format_ssdb_data(args)
    ssdb_data["city"] = city

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


def _handle_xuexin_crawling(args):
    """
    学信网爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    spider_name = USERINFO_DICT['学信']
    account_type = args["account_type"].strip()

    ssdb_data = _format_ssdb_data(args)

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


def _handle_bank_crawling(args):
    """
    银行交易数据爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    bank = args["bank"].strip()
    spider_name = BANK_DICT[bank]
    account_type = args["account_type"].strip()

    ssdb_data = _format_ssdb_data(args)
    ssdb_data.update({"bank": bank,
                      "id": args.get("id", "").strip(),
                      })

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


def _handle_emailbill_crawling(args):
    """
    邮箱账单爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    spider_name = EMAIL_DICT.get(username.rsplit("@", 1)[-1], OTHER_EMAIL_SPIDER_NAME)
    account_type = args["account_type"].strip()

    ssdb_data = _format_ssdb_data(args)

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


def _handle_zhengxin_crawling(args, password):
    """
    征信爬虫处理
    """
    username = args["username"].strip()
    args = args.dict()
    args['password'] = password
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    spider_name = ZHENANGXIN_DICT['人行征信']
    account_type = args["account_type"].strip()

    ssdb_data = _format_ssdb_data(args)
    ssdb_data['code'] = args["code"].strip()

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


def _handle_ecommerce_crawling(args):
    """
    电子商务数据爬虫处理
    """
    username = args["username"].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data)
        return JsonResponse(ret_data)

    account_type = args["account_type"].strip()
    spider_name = AccountType_2_SpiderName_DICT[account_type]

    ssdb_data = _format_ssdb_data(args)
    ssdb_data["id"] = args.get("id", "").strip()

    push_data_2_ssbd(username, spider_name, account_type, ssdb_data)

    add_ajax_ok_json(ret_data)

    return JsonResponse(ret_data)


@require_http_methods(["POST"])
@catch_except
def crawl_account(request):
    args = request.POST
    account_type = args["account_type"]
    username = args["username"]

    ssdb_conn = get_ssdb_conn()
    status = ssdb_conn.get(username + ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX + account_type)
    if status not in CHECK_STATUS_LIST:
        ret_data = {}
        add_ajax_ok_json(ret_data)
        return JsonResponse(ret_data)

    if "communications" == account_type:
        return _handle_communications_crawling(args)
    elif account_type in ["housefund", "shebao"]:
        return _handle_5xian1jin_crawling(args, account_type)
    elif "xuexin" == account_type:
        return _handle_xuexin_crawling(args)
    elif "bank" == account_type:
        return _handle_bank_crawling(args)
    elif "emailbill" == account_type:
        return _handle_emailbill_crawling(args)
    elif "zhengxin" == account_type:
        password = request.session['zhengxin_password']
        return _handle_zhengxin_crawling(args, password)
    elif account_type in ["jingdong", "alipay", "taobao", "yhd"]:
        return _handle_ecommerce_crawling(args)

    return HttpResponseBadRequest()


@require_http_methods(["POST"])
@catch_except
def get_crawling_status(request):
    args = request.POST
    account_type = args["account_type"]
    if "communications" == account_type:
        return _get_communications_crawling_status(args)
    elif account_type in ["housefund", "shebao"]:
        return _get_5xian1jin_crawling_status(args)
    elif "xuexin" == account_type:
        return _get_xuexin_crawling_status(args)
    elif "bank" == account_type:
        return _get_bank_crawling_status(args)
    elif "emailbill" == account_type:
        return _get_emailbill_crawling_status(args)
    elif "zhengxin" == account_type:
        return _get_zhengxin_crawling_status(args)
    elif account_type in ["jingdong", "alipay", "taobao", "yhd"]:
        return _get_ecommerce_crawling_status(args)

    return HttpResponseBadRequest()


def save_img_file_from_ssdb(uid, website=""):
    ssbd_connect = get_ssdb_conn()
    file_b64_data = ssbd_connect.get(uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX)
    _uid, file_type = uid.rsplit(".", 1)
    save_captcha_2_file(b64decode(file_b64_data), _uid, "." + file_type, website)


@require_http_methods(["POST"])
@catch_except
def submit_captcha_code(request):
    args = request.POST
    account_type = args["account_type"]
    username = args["username"]

    ssbd_connect = get_ssdb_conn()
    for the_type in ["sms", "img", "extra", "qrcode", "name_idcard_sms"]:
        arg_key = the_type + "_captcha"
        if arg_key in args:
            uid = args[the_type + "_uid"]
            captcha_code = args[arg_key].strip()
            ssbd_connect.delete(username + "-need_" + the_type + "_captcha-" + account_type)
            ssbd_connect.setx(uid, captcha_code, DATA_EXPIRE_TIME)
            if "img" == the_type:
                ssbd_connect.delete(username + ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX + account_type)

    data = {}
    add_ajax_ok_json(data)
    return JsonResponse(data)


def get_crawling_data(ssbd_connect, username, account_type, crawling_info=""):
    # 返回爬取状态
    status = ssbd_connect.get(username + ACCOUNT_CRAWLING_STATUS_SSDB_SUFFIX + account_type)
    msg = ssbd_connect.get(username + ACCOUNT_CRAWLING_MSG_SSDB_SUFFIX + account_type)
    # tell_data_key = ssbd_connect.get(username + ACCOUNT_CRAWLING_DATA_SSDB_SUFFIX + account_type)
    # tell_data = ssbd_connect.get(tell_data_key) if tell_data_key else None

    return {"crawling_status": status,
            "crawling_msg": msg or "",
            "crawling_info": crawling_info or username,
            # "crawling_data": data_loads(tell_data) if tell_data else None
            }


def _get_communications_crawling_status(args):
    """
    运营商爬虫状态
    """
    account_type = args["account_type"]
    username = args["username"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码并输入短信验证码
    uid_str = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SMS_SSDB_SUFFIX + account_type)
    if uid_str is not None:
        uid_dict = data_loads(uid_str)
        uid, sms_type = uid_dict["uid"], uid_dict["sms_type"]
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_sms_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["sms_type"] = sms_type
        data["sms_uid"] = uid + ACCOUNT_CRAWLING_SMS_UID_SSDB_SUFFIX
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 需要短信验证码
    uid_str = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX + account_type)
    if uid_str is not None:
        uid_dict = data_loads(uid_str)
        uid, sms_type = uid_dict["uid"], uid_dict["sms_type"]
        data["crawling_status"] = "sms_captcha"
        data["username"] = username
        data["sms_uid"] = uid
        data["sms_type"] = sms_type
        return JsonResponse(data)

    # 需要姓名、身份证号、短信验证码
    uid_str = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_NAME_IDCARD_SMS_SSDB_SUFFIX + account_type)
    if uid_str is not None:
        uid_dict = data_loads(uid_str)
        uid, sms_type = uid_dict["uid"], uid_dict["sms_type"]
        data["crawling_status"] = "name_idcard_sms_captcha"
        data["username"] = username
        data["sms_uid"] = uid
        data["sms_type"] = sms_type
        return JsonResponse(data)

    # 返回爬取状态
    crawling_info = ssbd_connect.get(username + ACCOUNT_CRAWLING_INFO_SSDB_SUFFIX + account_type)
    data.update(get_crawling_data(ssbd_connect, username, account_type, crawling_info))
    return JsonResponse(data)


def _get_5xian1jin_crawling_status(args):
    """
    五险一金爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]
    city = args["city"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, city + ":" + username))
    return JsonResponse(data)


def _get_xuexin_crawling_status(args):
    """
    学信网爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, username))
    return JsonResponse(data)


def _get_bank_crawling_status(args):
    """
    银行交易数据爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]
    bank = args["bank"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 需要短信验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "sms_captcha"
        data["username"] = username
        data["sms_uid"] = uid
        return JsonResponse(data)

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, bank + ":" + username))
    return JsonResponse(data)


def _get_emailbill_crawling_status(args):
    """
    163数据爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        img_desc = ssbd_connect.get(uid + ACCOUNT_CRAWLING_IMG_DESCRIBE_SSDB_SUFFIX)
        if img_desc is not None:
            data["img_desc"] = img_desc
        return JsonResponse(data)

    # 需要短信验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "sms_captcha"
        data["username"] = username
        data["sms_uid"] = uid
        return JsonResponse(data)

    # 需要独立密码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_EXTRA_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "extra_captcha"
        data["username"] = username
        data["extra_uid"] = uid
        return JsonResponse(data)

    # 需要扫描二维码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "scan_qrcode"
        data["username"] = username
        data["qrcode_uid"] = uid
        data["qrcode_pic"] = ssbd_connect.get(uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX)
        return JsonResponse(data)

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, username))
    return JsonResponse(data)


def _get_zhengxin_crawling_status(args):
    """
    征信数据爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, username))
    return JsonResponse(data)


def _get_ecommerce_crawling_status(args):
    """
    电子商务数据爬虫状态
    """
    username = args["username"]
    account_type = args["account_type"]

    data = {}
    add_ajax_ok_json(data)

    ssbd_connect = get_ssdb_conn()

    # 需要识别图片验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_IMG_SSDB_SUFFIX + account_type)
    if uid is not None:
        save_img_file_from_ssdb(uid)
        data["crawling_status"] = "img_captcha"
        data["username"] = username
        data["img_uid"] = uid
        data["img_src"] = static("/".join((CAPTCHA_DIR, uid)))
        return JsonResponse(data)

    # 需要短信验证码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_SMS_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "sms_captcha"
        data["username"] = username
        data["sms_uid"] = uid
        return JsonResponse(data)

    # 需要扫描二维码
    uid = ssbd_connect.get(username + ACCOUNT_CRAWLING_NEED_QRCODE_SSDB_SUFFIX + account_type)
    if uid is not None:
        data["crawling_status"] = "scan_qrcode"
        data["username"] = username
        data["qrcode_uid"] = uid
        data["qrcode_pic"] = ssbd_connect.get(uid + ACCOUNT_CRAWLING_IMG_DATA_SSDB_SUFFIX)
        return JsonResponse(data)

    # 返回爬取状态
    data.update(get_crawling_data(ssbd_connect, username, account_type, username))
    return JsonResponse(data)


def do_nothing(request):
    return HttpResponse()


@catch_except
def crawl_nav(request):
    return render(request, 'show_crawl_nav.html')


@require_http_methods(["POST"])
@catch_except
@csrf_exempt
def access_token(request):
    result = {"code": 0}
    try:
        # 接收密文
        body = data_loads(request.body)
        if not isinstance(body, dict):
            raise ValueError("arguments must json")
        elif body["cipher_text"] is None or body["cipher_text"] == "":
            raise ValueError("arguments cipher_text is not null")
        # 解密
        plain_text = rsa_long_decrypt(settings.PRIVATE_KEY, body["cipher_text"])
        plain_text = data_loads(plain_text)
        if not isinstance(plain_text, dict):
            raise ValueError("plain_text must json")
        # 请求access token
        token_url = "%so/token/?client_id=%s&grant_type=client_credentials&client_secret=%s" % \
                    (WEB_SETTINGS_ACCESS_DOMAIN, plain_text["client_id"], plain_text["client_secret"])
        res = http_post(token_url)
        result["code"] = 1
        result["body"] = data_loads(res.text)
        result["message"] = "success"
    except Exception as e:
        result["message"] = "error.detail:%s" % str(e)

    return JsonResponse(result)


@require_http_methods(["POST"])
@catch_except
def ask_send_sms_captcha(request):
    """请求需要发送验证码"""
    args = request.POST
    account_type = args["account_type"]
    if "communications" == account_type:
        return _ask_send_communications_sms_captcha(args)
    elif account_type in ["jingdong", "alipay", "taobao", "yhd"]:
        return _ask_send_ecommerce_sms_captcha(args)
    return HttpResponseBadRequest()


def _ask_send_communications_sms_captcha(args):
    """告诉爬虫端 需要运营商发送短信验证码"""
    username = args['username'].strip()
    account_type = args['account_type'].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data, "号码为空")
        return JsonResponse(ret_data)

    ssbd_connect = get_ssdb_conn()
    ssbd_connect.setx(username + ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX + account_type,
                      True, DATA_EXPIRE_TIME)

    add_ajax_ok_json(ret_data)
    return JsonResponse(ret_data)


def _ask_send_ecommerce_sms_captcha(args):
    """告诉爬虫端 需要电商发送短信验证码"""
    username = args['username'].strip()
    account_type = args['account_type'].strip()
    ret_data = {}

    if not username:
        add_ajax_error_json(ret_data, "用户名为空")
        return JsonResponse(ret_data)

    ssbd_connect = get_ssdb_conn()
    ssbd_connect.setx(username + ACCOUNT_CRAWLING_ASK_SEND_SMS_SSDB_SUFFIX + account_type, True, DATA_EXPIRE_TIME)

    add_ajax_ok_json(ret_data)
    return JsonResponse(ret_data)
