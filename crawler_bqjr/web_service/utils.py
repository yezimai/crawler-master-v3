from functools import wraps
from logging import getLogger

from django.http import HttpResponseBadRequest
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from base64 import b64encode, b64decode

logger = getLogger('django.request')


def catch_except(func):
    @wraps(func)
    def inner(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception:
            logger.exception(func.__name__)
            return HttpResponseBadRequest("Bad Request")

    return inner


# 包装ajax成功执行的标识
def add_ajax_ok_json(data):
    data['status'] = "ok"


# 包装ajax成功执行的标识
def add_ajax_error_json(data, msg=""):
    data['status'] = "fail"
    data['msg'] = msg


# ajax执行成功的json回复
def ajax_ok_json():
    data = {}
    add_ajax_ok_json(data)
    return data


# ajax执行失败的json回复
def ajax_error_json():
    data = {}
    add_ajax_error_json(data)
    return data


def rsa_long_encrypt(pub_key_str, msg, length=100):
    """
    单次加密串的长度最大为 (key_size/8)-11
    1024bit的证书用100， 2048bit的证书用 200
    """
    pubobj = RSA.importKey(pub_key_str)
    pubobj = PKCS1_v1_5.new(pubobj)
    res = b"".join(pubobj.encrypt(msg[i:i + length].encode("utf-8"))
                   for i in range(0, len(msg), length))
    return b64encode(res)


def rsa_long_decrypt(priv_key_str, msg, length=128):
    """
    1024bit的证书用128，2048bit证书用256位
    """
    privobj = RSA.importKey(priv_key_str)
    privobj = PKCS1_v1_5.new(privobj)
    res = []
    msg = b64decode(msg)
    for i in range(0, len(msg), length):
        res.append(privobj.decrypt(msg[i:i+length], 'xyz').decode("utf-8"))
    return "".join(res)
