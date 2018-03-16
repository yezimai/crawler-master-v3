# -*- coding: utf-8 -*-

from base64 import b64encode
from random import choice

from requests import post as http_post

from crawler_bqjr.captcha.baidu_orc_api import convert_pic
from global_utils import json_dumps, json_loads


def jisu_alicloudapi(pic):
    """识别率90%"""
    host = 'http://tongyongwe.market.alicloudapi.com'
    path = '/generalrecognition/recognize'
    appcode = 'd6147d2ef06e4ce09ce029cae877daca'
    querys = 'type=cnen'
    url = host + path + '?' + querys

    bodys = {'pic': pic}
    headers = {'Authorization': 'APPCODE ' + appcode,
               'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
               }

    response = http_post(url, data=bodys, headers=headers)
    return response.text


def hanvon_table_alicloudapi(pic):
    """识别率70%"""
    host = 'http://table.aliapi.hanvon.com'
    path = '/rt/ws/v1/ocr/table/text/recg'
    appcode = 'd6147d2ef06e4ce09ce029cae877daca'
    querys = 'code=0d3b7d23-915a-4c6f-9886-6312440aba51'
    url = host + path + '?' + querys

    data = {'uid': "118.12.0.12",
            "lang": "chns",
            "color": "black",
            'image': pic
            }
    headers = {'Authorization': 'APPCODE ' + appcode,
               'Content-Type': 'application/json; charset=UTF-8',
               }

    response = http_post(url, data=json_dumps(data), headers=headers)
    return response.text


def hanvon_alicloudapi(pic):
    """识别率70%"""
    host = 'http://text.aliapi.hanvon.com'
    path = '/rt/ws/v1/ocr/text/recg'
    appcode = 'd6147d2ef06e4ce09ce029cae877daca'
    querys = 'code=74e51a88-41ec-413e-b162-bd031fe0407e'
    url = host + path + '?' + querys

    data = {'uid': "118.12.0.12",
            "lang": "chns",
            "color": "black",
            'image': pic
            }
    headers = {'Authorization': 'APPCODE ' + appcode,
               'Content-Type': 'application/json; charset=UTF-8',
               }

    response = http_post(url, data=json_dumps(data), headers=headers)
    return response.text


# 每个只有1000次调用次数
ALICLOUDAPI_APPCODE_LIST = ["d6147d2ef06e4ce09ce029cae877daca",
                            "9035255f6eed4c818d7516ee7742cb72",
                            "216428ac999346daa426c954d0051cc3",
                            "e33cb9cf1ba64c93a6f0701fff910327",
                            "d30561fba6874a4a9751124330ff4f7d",
                            "4dda59bc51eb4fd78bcdb3c54e5c3405",
                            ]


def _send_taobao_alicloudapi(url, b64_pic):
    data = {'img': b64_pic,
            'prob': 'false'
            }
    headers = {'Authorization': 'APPCODE ' + choice(ALICLOUDAPI_APPCODE_LIST),
               }

    response = http_post(url, data=json_dumps(data), headers=headers)
    data = json_loads(response.text)
    return [i["word"] for i in data["prism_wordsInfo"]] if "prism_wordsInfo" in data else None


def ugc_alicloudapi(b64_pic):
    """识别率100%"""
    return _send_taobao_alicloudapi('https://ocrapi-ugc.taobao.com/ocrservice/ugc', b64_pic)


def entertainment_alicloudapi(b64_pic):
    """识别率100%"""
    return _send_taobao_alicloudapi('https://ocrapi-entertainment.taobao.com/ocrservice/entertainment', b64_pic)


def ecommerce_alicloudapi(b64_pic):
    """识别率100%"""
    return _send_taobao_alicloudapi('https://ocrapi-ecommerce.taobao.com/ocrservice/ecommerce', b64_pic)


def document_alicloudapi(b64_pic):
    """识别率100%"""
    return _send_taobao_alicloudapi('https://ocrapi-document.taobao.com/ocrservice/document', b64_pic)


API_LIST = [ugc_alicloudapi,
            entertainment_alicloudapi,
            ecommerce_alicloudapi,
            document_alicloudapi,
            ]


def alicloud_orc(pic_data):
    b64_pic = b64encode(pic_data).decode()
    for i in range(3):
        result = choice(API_LIST)(b64_pic)
        if result:
            return result


if __name__ == '__main__':
    for i in range(1, 2):
        with open(r"F:\%d.jpg" % i, "rb") as f:
            img_bytes = convert_pic(f.read())
            new_data = alicloud_orc(img_bytes)
            print(i, "\n", new_data)
