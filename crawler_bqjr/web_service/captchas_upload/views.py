# -*- coding: utf-8 -*-

from hashlib import md5
from io import IOBase
from logging import getLogger
from os import path as os_path
from time import sleep
from webbrowser import open_new_tab

from captchas_upload.models import CaptchaList
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseNotFound, JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from utils import catch_except, add_ajax_ok_json, add_ajax_error_json

from data_storage.ssdb_db import get_ssdb_conn

web_logger = getLogger(__name__)

CAPTCHA_DIR = settings.CAPTCHA_DIR
STATIC_PATH = settings.STATICFILES_DIRS[0]
HOST_URL = settings.DOMAIN


class BadCaptchaFormat(Exception):
    pass


def save_captcha_2_file(content, uid, file_type=".jpg", website=""):
    try:
        _ = CaptchaList.objects.get(uid=uid)
    except ObjectDoesNotExist:
        full_file_name = uid + file_type
        save_path = os_path.join(STATIC_PATH, CAPTCHA_DIR, full_file_name)
        with open(save_path, 'wb') as f:
            f.write(content)

        try:
            CaptchaList.objects.create(uid=uid, filename=full_file_name, website=website)
        except Exception:
            web_logger.exception("save captcha info to DB:")


def save_captcha(captcha, file_type=".jpg", website=""):
    if isinstance(captcha, bytes):
        content = captcha
    elif isinstance(captcha, IOBase):
        content = captcha.read()
    else:
        raise BadCaptchaFormat

    uid = md5(content).hexdigest()
    save_captcha_2_file(content, uid, file_type, website)
    return uid


@require_http_methods(["POST"])
@catch_except
def upload_captcha(request):
    args = request.POST
    file_type = args.get("file_type", ".jpg")
    website = args.get("website", "")
    # username = args.get("username", "")

    file = request.FILES['file']
    data = {"uid": save_captcha(file, file_type, website)}

    add_ajax_ok_json(data)
    return JsonResponse(data)


def _get_captcha_page(request, uid):
    try:
        captcha = CaptchaList.objects.get(uid=uid)
    except ObjectDoesNotExist:
        return HttpResponseNotFound(u"验证码不存在")

    return render(request, 'show_captcha.html', {'img_src': "/".join((CAPTCHA_DIR, captcha.filename)),
                                                 'uid': uid,
                                                 }
                  )


@require_http_methods(["GET"])
@catch_except
def show_captcha(request):
    return _get_captcha_page(request, request.GET["uid"])


@require_http_methods(["POST"])
@catch_except
def verify_captcha(request):
    args = request.POST
    captcha = args["captcha"]
    uid = args["uid"]

    ssbd_connect = get_ssdb_conn()
    ssbd_connect.setx(uid, captcha, 1800)

    try:
        captcha_obj = CaptchaList.objects.get(uid=uid)
        captcha_obj.result = captcha
        captcha_obj.save()
    except ObjectDoesNotExist:
        return HttpResponseNotFound(u"验证码不存在")

    return HttpResponse(u"谢谢")


def _get_captcha_result(uid):
    ssbd_connect = get_ssdb_conn()
    ssbd_connect.delete(uid)

    open_new_tab(HOST_URL + "captchas_upload/show_captcha/?uid=" + uid)

    captcha = None
    for i in range(100):
        captcha = ssbd_connect.get(uid)
        if captcha is not None:
            ssbd_connect.delete(uid)
            break
        sleep(0.5)

    return captcha


@require_http_methods(["POST"])
@catch_except
def recognize_captcha(request):
    args = request.POST
    file_type = args.get("file_type", ".jpg")
    website = args.get("website", "")
    # username = args.get("username", "")

    file = request.FILES['file']
    uid = save_captcha(file, file_type, website)

    captcha = _get_captcha_result(uid)
    data = {"captcha": captcha}

    if captcha:
        add_ajax_ok_json(data)
    else:
        add_ajax_error_json(data)

    return JsonResponse(data)
