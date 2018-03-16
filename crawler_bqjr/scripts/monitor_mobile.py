#!/usr/bin/env python

import datetime
from os import path as os_path
from sys import path as sys_path

sys_path.append(os_path.dirname((os_path.dirname(os_path.abspath(__file__)))))

import requests

from crawler_bqjr.mail import send_mail_2_admin, send_mail
from global_utils import json_loads


def monitor():
    # print("---------监控开始-----------")
    now = datetime.datetime.now()
    now_str = now.strftime('%Y-%m-%d')
    ip = "10.89.1.54"
    url = "http://%s/rest_api/get_mobile_phone/?update_time=%s 00:00:0.000" % (ip, now_str)
    title = "[%s]手机品牌监控出错啦[%s]" % (ip, now_str)
    try:
        response = requests.get(url)
        code = response.status_code
        result = response.text
        if code != 200:
            msg = "出错详情：接口访问出现错误，状态%d" % code
            send_mail_2_admin(title, msg)
        json_loads(result)
    except Exception as e:
        msg = "出错详情：%s" % str(e)
        send_mail_2_admin(title, msg)
        send_mail(["superplayer_dan@163.com"], title, msg)


if __name__ == '__main__':
    monitor()
