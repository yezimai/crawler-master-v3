# coding:utf-8

from traceback import print_exc

from crawler_bqjr.spiders_settings import DIANXIN_APP_ENCRYPT_KEY, DIANXIN_APP_ENCRYPT_IV
from crawler_bqjr.tools.dict2xml import dict2xml
from crawler_bqjr.tools.triple_des import TripleDES, DES3
from crawler_bqjr.tools.xml2dict import XML2Dict

xml_tool = XML2Dict()


class DXConvertData(object):
    """
    电信APP网络请求数据转换工具类
    电信APP请求加密方式:
    3DES-CBC-pkcs5
    key：1234567`90koiuyhgtfrdewsaqaqsqde
    iv: 00000000
    """

    def __init__(self, key=None, iv=None, mode=None):
        self.__key = key or DIANXIN_APP_ENCRYPT_KEY
        self.__iv = iv or DIANXIN_APP_ENCRYPT_IV
        self._mode = mode or DES3.MODE_CBC
        self.des_tool = TripleDES(key=self.__key, iv=self.__iv, mode=self._mode)

    def convert_request_data(self, request_data):
        """
        转换请求数据(dict-->xml-->encrypt_data)
        :param request_data:
        :return:加密hex数据
        """
        ret_str = ""
        try:
            if isinstance(request_data, dict):
                # 第一步:将dict转化为xml
                xml_str = dict2xml(request_data)
                # 第二步:将xml数据进行3des加密
                ret_str = self.des_tool.encrypt(text=xml_str, get_hex=True)
        except Exception:
            print("[-]转换请求数据失败:%s" % request_data)
            print_exc()
        finally:
            return ret_str

    def convert_response_data(self, response_data):
        """
        转换响应数据(encrypt_str-->xml-->dict)
        :param response_data:
        :return: dict or None
        """
        ret_data = None
        try:
            if isinstance(response_data, str):
                # 第一步:解密数据
                raw_str = self.des_tool.decrypt(text=response_data, is_hex=True)
                # 第二步: 将xml转化为dict
                ret_data = xml_tool.get_dict(xml_or_path=raw_str)
        except Exception:
            print("[-]转换响应数据失败:%s" % response_data)
            print_exc()
        finally:
            return ret_data


if __name__ == '__main__':
    tool = DXConvertData()

    request_data = {
        "Request": {
            "HeaderInfos": {
                "ClientType": "#6.2.1#channel29#Huawei LON-AL00#",
                "Source": "110003",
                "SourcePassword": "Sid98s",
                "Code": "queryPhoneSections",
                "Timestamp": "20180108173628"
            },
            "Content": {
                "Attach": "test"
            }
        }
    }
    req_str = tool.convert_request_data(request_data)
    print(req_str, end="\n\n")

    response_data = "b5720f816f50db5eb94116fd795b9f770f4af1f252692aa8c138f0e8150856db0b52b7c8000a7be699aabc4ab106f380f9e488a10e8269792beb5b46a667cdf32e20cf7649e74841dcfc49d871e100bda5b005efdca1abf6d8f95b802b6db01dc0bc44d9f75be7b899fcac6bf3674bff51429cb76f9ea218fa2bad0b88a6c6c80d9edbb96f284e26c08a514ffe89869973b1d297873df3042f7fed5cff21498279cee5c1521deab082083b21bbdbcdcbe94fb492867d0f86334ca83f82fe25a9dbdce9257bf0611d6c1d1a6e8a965c31bcb6f4ce975072fdca2ea43d87135aaca53159643234664e1a7e537593add0d8f4552bc32f99bfc27526f2639e7a79835759e702f898baf011e7e75c9932cbd7315a18e4b28bb39991dde3c9731b152b00b4b33872e1443902512b516a512bdafd56907819d5e9359ce25aaa021ce130c23803218e77079c71d7fe9111687ba722c4961e2b09d23e3390fca0d38eb268f3894c8c851d78ea51c34f171589657fbfb5d0a5405703eacf70c40b94ad8f6129532e33567ca0cfbbe4322bb66aea488bb7edca867141f6a6e8f7060b07bd4d2ac5d19a42943589bdc4be22ac04c55323682fbe01f8e3d3"
    res_data = tool.convert_response_data(response_data)
    print(res_data, end="\n\n")
