# -*- coding: utf-8 -*-

from collections import defaultdict
from re import compile as re_compile
from urllib.request import urlopen, Request

from global_utils import json_loads

taobao_province = re_compile(r"province:'(\S+)'")
taobao_brand = re_compile(r"catName:'(\S+)'")
space_pattern = re_compile(r"\s*")

ASK_TIMEOUT = 3


def _get_phone_info_from_juhe(phone_num):
    url = "http://apis.juhe.cn/mobile/get?key=bab37bb3f7b19c816e1f2d23100efa4f&phone=" + phone_num
    data = json_loads(urlopen(url, timeout=ASK_TIMEOUT).read())
    if data["resultcode"] == '200':
        result = data["result"]
        return result["company"], result["province"], result["city"]
    else:
        raise Exception


def _get_phone_info_from_taobao(phone_num):
    url = "https://tcc.taobao.com/cc/json/mobile_tel_segment.htm?tel=" + phone_num
    data = urlopen(url, timeout=ASK_TIMEOUT).read().decode("gbk")
    brand = taobao_brand.search(data).group(1).lstrip("中国")
    province = taobao_province.search(data).group(1)
    return brand, province, ""


def _get_phone_info_from_baifubao(phone_num):
    url = "https://www.baifubao.com/callback?cmd=1059&callback=phone&phone=" + phone_num
    data = urlopen(url, timeout=ASK_TIMEOUT).read()
    data = data[data.find(b'{"meta":{'):-1]
    data = json_loads(data)
    if data["meta"]["result"] == '0':
        result = data["data"]
        return result["operator"], result["area"], ""
    else:
        raise Exception


def _get_baidu_api_ret(url):
    req = Request(url)
    req.add_header('apikey', '72a0d84c0c95a75cd5aa8c1c3e698946')
    return json_loads(urlopen(req, timeout=ASK_TIMEOUT).read())


def _get_phone_info_from_baidu_api0(phone_num):
    """
    此接口已经不存在了
    """
    url = "http://apis.baidu.com/apistore/mobilenumber/mobilenumber?phone=" + phone_num
    data = _get_baidu_api_ret(url)
    if data["errNum"] == 0:
        result = data["retData"]
        return result["supplier"], result["province"], result["city"]
    else:
        raise Exception


def _get_phone_info_from_jd_jisu(phone_num):
    """
    京东万象（极速数据）
    """
    url = "https://way.jd.com/jisuapi/query4?shouji=%s&appkey=54c96204934e754bed98473949c48559" % phone_num
    data = json_loads(urlopen(url, timeout=ASK_TIMEOUT).read())
    if data["result"]["status"] == '0':
        result = data["result"]["result"]
        return result["company"].lstrip("中国"), result["province"], result["city"]
    else:
        raise Exception


def _get_phone_info_from_jd_shujujia(phone_num):
    """
    京东万象（数据加）
    """
    url = "https://way.jd.com/shujujia/mobile?mobile=%s&appkey=54c96204934e754bed98473949c48559" % phone_num
    data = json_loads(urlopen(url, timeout=ASK_TIMEOUT).read())
    result = data["result"]
    if result["status"] == 1:
        return result.get("operator", "未知"), \
               result["province"].rstrip("市省自治区壮族回维吾尔特别行政"), \
               result["city"].rstrip("市")
    else:
        raise Exception


def _get_phone_info_from_aliyun_api0(phone_num):
    """
    阿里云（api0,可以无限购买，每次购买0元10000次）
    """
    url = "http://jshmgsdmfb.market.alicloudapi.com/shouji/query?shouji=%s" % phone_num
    req = Request(url)
    req.add_header('Authorization', 'APPCODE 4dda59bc51eb4fd78bcdb3c54e5c3405')
    data = json_loads(urlopen(req, timeout=ASK_TIMEOUT).read())
    if data["status"] == "0":
        result = data["result"]
        return result["company"].lstrip("中国"), result["province"], result["city"]
    else:
        raise Exception


def _get_phone_info_from_aliyun_api1(phone_num):
    """
    阿里云（api1,可以无限购买，每次购买0元1000次）
    """
    url = "http://showphone.market.alicloudapi.com/6-1?num=%s" % phone_num
    req = Request(url)
    req.add_header('Authorization', 'APPCODE 4dda59bc51eb4fd78bcdb3c54e5c3405')
    data = json_loads(urlopen(req, timeout=ASK_TIMEOUT).read())
    if data["showapi_res_body"]["ret_code"] == 0:
        result = data["showapi_res_body"]
        brand = space_pattern.sub("", result["name"].replace("虚拟运营商", ""))
        for i in ["移动", "联通", "电信"]:
            if brand.startswith(i):
                brand = i
                break
        return brand, result["prov"], result["city"].rstrip("市")
    else:
        raise Exception


regex_baidu = re_compile(r"百度安全卫士.*?有<b>(\d+?)人.*?<b>(.*?)</b>")
regex_sogou = re_compile(r"搜狗号码通.*?<b>(.*?)</b>")
regex_360 = re_compile(r"360手机卫士.*?有<b>(\d+?)人.*?<b>(.*?)</b>")

YOURNUMBER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3166.0 Safari/537.36',
}


def get_phone_info_from_yournumber(phone_num):
    """
    从yournumber.cn获取号码标记信息
    :param phone_num:
    :return:
    """
    url = "http://www.yournumber.cn/index/index/s/%s.html" % phone_num
    req = Request(url, headers=YOURNUMBER_HEADERS)
    content = urlopen(req, timeout=ASK_TIMEOUT).read().decode("utf-8")
    result_baidu = regex_baidu.search(content)
    result_sogou = regex_sogou.search(content)
    result_360 = regex_360.search(content)
    result = defaultdict(int)

    if result_baidu:
        count, the_type = result_baidu.groups()
        result[the_type] = int(count)

    if result_360:
        count, the_type = result_360.groups()
        result[the_type] += int(count)

    if result_sogou:
        the_type = result_sogou.groups()
        result[the_type] += 1

    return result


API_LIST = [_get_phone_info_from_juhe,
            _get_phone_info_from_taobao,
            _get_phone_info_from_aliyun_api1,
            _get_phone_info_from_aliyun_api0,
            _get_phone_info_from_baifubao,
            _get_phone_info_from_jd_jisu,
            _get_phone_info_from_jd_shujujia,
            ]


def get_phone_info(phone_num):
    """
        返回字典
        {"brand":"移动",
         "province":"四川",
         "city":"成都",
         }
    """
    for api_func in API_LIST:
        try:
            brand, province, city = api_func(phone_num)
        except Exception:
            continue
        else:
            return {"brand": brand,
                    "province": province,
                    "city": city,
                    }

    return None


import unittest


class TestPhoneInfoAPI(unittest.TestCase):
    def setUp(self):
        self.test_case = [(("阿里通信", "广东", "东莞"), _get_phone_info_from_juhe, "17097530633"),
                          (("联通", "广西", ""), _get_phone_info_from_taobao, "13211331331"),
                          (('爱施德U.友移动', '四川', '成都'), _get_phone_info_from_aliyun_api1, "17052835154"),
                          (('虚拟运营商', '广东', '东莞'), _get_phone_info_from_aliyun_api0, "17097530633"),
                          (('电信', '北京', '北京'), _get_phone_info_from_jd_shujujia, "15311768291"),
                          (('电信', '湖南', '常德'), _get_phone_info_from_jd_jisu, "15386176525"),
                          (("移动", "湖南", ""), _get_phone_info_from_baifubao, "15243611372"),
                          ({"brand": "电信", "province": "广东", "city": "深圳"}, get_phone_info, "18123836335"),
                          ]

    def test_func(self):
        from time import clock
        for ret, func, phone in self.test_case:
            a = clock()
            self.assertEqual(func(phone), ret)
            b = clock()
            print(func.__name__, b - a)


if __name__ == '__main__':
    unittest.main()
