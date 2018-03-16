# -*- coding: utf-8 -*-

from io import BytesIO, IOBase
from traceback import print_exc

from requests import post as http_post
from scrapy.utils.project import get_project_settings

from crawler_bqjr.captcha.ml.KNN import get_knn_distance
from web_service.process_captcha import recognize_captcha_from_file

scrapy_settings = get_project_settings()
RECOGNIZE_CAPTCHA_API = scrapy_settings["RECOGNIZE_CAPTCHA_API"]


class BadCaptchaFormat(Exception):
    pass


def recognize_captcha_manual(captcha_body, params=None):
    try:
        if isinstance(captcha_body, bytes):
            captcha_file_like = BytesIO(captcha_body)
        elif isinstance(captcha_body, IOBase):
            captcha_file_like = captcha_body
        else:
            raise BadCaptchaFormat

        files = {'file': captcha_file_like}
        response = http_post(RECOGNIZE_CAPTCHA_API, data=params, files=files)
        captcha_info = response.json()
        return captcha_info["captcha"] if captcha_info["status"] == 'ok' else ""
    except Exception:
        print_exc()
        return ""


def recognize_captcha_auto(captcha_body, params=None,
                           digits_only=False, letters_only=False, del_noise=False):
    try:
        if isinstance(captcha_body, bytes):
            captcha_file_like = BytesIO(captcha_body)
        elif isinstance(captcha_body, IOBase):
            captcha_file_like = captcha_body
        else:
            raise BadCaptchaFormat

        return recognize_captcha_from_file(captcha_file_like, digits_only=digits_only,
                                           letters_only=letters_only, del_noise=del_noise)
    except Exception:
        print_exc()
        return ""


def recognize_captcha_with_ml_knn(image, train_data_path):
    distance = get_knn_distance(image)
    distance = int(distance)

    result = None
    with open(train_data_path, "r") as train_data_file:
        result = train_data_file.read()
    if result is None:
        return None
    if str(distance) in result:
        result_label = result[str(distance)]
        return result_label[1]
    else:
        return None
