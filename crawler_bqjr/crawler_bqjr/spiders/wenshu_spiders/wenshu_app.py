# -*- coding: utf-8 -*-

"""
    # 查找条件，1刑事案件，2民事案件，3行政案件，4赔偿案件，5执行案件，不写则查全部
    # "condition": ""
    # "condition": "/CaseInfo/案/@案件类型=4"
    # condition = / CaseInfo / 案 / @ 文书类型 = 判决书     -->  文书类型
    # condition = / CaseInfo / 案 / @ DocContent = 广东     -->  全文检索
    # condition=/CaseInfo/案/@案件名称=王某   -->  案件名称
    # / CaseInfo / 案 / @ 案号 = *256 *
    # / CaseInfo / 案 / @ 法院名称 = *人民法院 *
    # / CaseInfo / 案 / @ 法院层级 = 1
    # / CaseInfo / 案 / @ 案件类型 = 1
    # / CaseInfo / 案 / @ 审判程序 = 一审
    # / CaseInfo / 案 / @ 文书类型 = 判决书
    # / CaseInfo / 案 / @ 裁判日期 = [2015 - 03 - 13 TO 2099 - 12 - 31]
    # / CaseInfo / 案 / 审判组织 / 审判人员 / @ 姓名 = *王昭君 *
    # / CaseInfo / 案 / 当事人 / @ 姓名或名称 = *李希 *
    # / CaseInfo / 案 / 当事人 / 代理律师 / @ 所在律所 = *大秦 *
    # / CaseInfo / 案 / 当事人 / 代理律师 / @ 姓名 = *王海 *
    # ( / CaseInfo / 案 / 法律依据 / @ 引用法律法规名称 = *宪法 * OR / CaseInfo / 案 / 法律依据 / @ 标准法规名称 = *宪法 *)  --> 法律依据

    # 旧数据爬取组合方案：法院名称 + 案件类型 + 裁判日期，以裁判日期倒序
    # 组合方案出现查询数据大概最多的情况：检索条件：一级案由:民事案由  基层法院:青州市人民法院  24346 条结果，最多一年有6625条数据，按日期365条，大概每天18条，
    # 而接口本身最多返回200条左右数据，所以裁判日期查询范围十一可基本涵盖所有数据
    # （只是列表）请求量和时间初步估算：法院数量大概 3688  案件类型 5种 查询时间 365/11 = 33  （13） 大概请求次数： 3688 * 5 * 33  608520次，每次假设1秒，大概七天能爬完一年的，
    # 最多一年的数据是2016年，共9788339，每次处理约2秒（请求1秒+保存1秒），约226天
    # 新数据增量爬取方案：法院名称 + 案件类型 + 上传日期，上传日期查询范围一天
"""

from base64 import b64decode
from random import choice as rand_choice
from time import localtime, strftime

from Crypto.Cipher import AES
from Crypto.Hash import MD5
from scrapy.http import Request

from crawler_bqjr.items.wenshu_items import WenshuItem
from crawler_bqjr.spiders.wenshu_spiders.base import WenshuSpider
from global_utils import json_loads, json_dumps


def get_reqtoken():
    """
    获取reqtoken, 获取原则md5(时间+key)
    :return:
    """
    token = strftime("%Y%m%d%H%M", localtime()) + "lawyeecourtwenshuapp"
    return MD5.new(token.encode('utf-8')).hexdigest().upper()


def decrypt(text):
    # key = iv = b"lawyeecourtwensh"
    cryptor = AES.new(b"lawyeecourtwensh", AES.MODE_CBC, b"lawyeecourtwensh")
    return cryptor.decrypt(text).rstrip(b"\0")


test_condition = [
    '[["case_type","0"],["court","上海市高级人民法院"],["date","2017-03-01 TO 2017-03-31"]]',
    '[["case_type","0"],["court","上海市第一中级人民法院"],["date","2017-03-01 TO 2017-03-05"]]',
]
DEBUG = True


class WenshuAppSpider(WenshuSpider):
    """
    爬取策略：
    wenshu_old爬虫，按照上传日期并以裁判日期倒序爬取，爬取上传日期范围：1995-12-31 TO 2017-04-11
    wenshu_today爬虫，在此过程中网站还在不停更新文书内容，更新的文书内容则按照上传日期进行检索爬取，更新的爬虫爬取2017年4月12日及之后的数据即可

    去重：
    爬取过程中需在ssdb中记录当前的start_index（当前爬取到的数据位置）及已经爬取到的文书id，避免重复爬取

    """

    name = "wenshu_app_spider"
    allowed_domains = ["wenshu.court.gov.cn"]

    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPERROR_ALLOWED_CODES": [400, 401, 403, 404, 500, 501, 502, 503],
        # "RETRY_ENABLED": True,
        # "RETRY_TIMES": 1000,
        # "DOWNLOAD_TIMEOUT": 180,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_url = "http://wenshuapp.court.gov.cn/MobileServices/GetLawListData"  # app 文书列表
        self.doc_url = "http://wenshuapp.court.gov.cn/MobileServices/GetAllFileInfoByIDNew"  # app 文件内容
        self.page_size = 20  # 分页大小（经测试改成其他数值无效）
        self.start_index = 0
        self.condition = {}  # 当前查询条件
        self.headers = {
            "Accept-Encoding": "gzip",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.0; FRD-AL10 Build/HUAWEIFRD-AL10)",
            "Content-Type": "application/json",
            "Connection": "Keep-Alive",
            # "Host": "wenshuapp.court.gov.cn",
        }
        self.req_data = {
            "limit": str(self.page_size),  # 分页大小
            "dicval": "asc",  # 排序，asc升序，desc降序
            "reqtoken": get_reqtoken(),  # 请求的token，md5
            "skip": self.start_index,  # 跳过数量，也可以理解为起始位置
            "dickey": "/CaseInfo/案/@法院层级",  # 排序字段(法院层级、裁判日期、审判程序)
            "condition": ""
        }

    def set_proxy(self, request):
        # 设置代理
        self.logger.info("current proxy->%s" % self.proxy)
        request.meta["proxy"] = "http://" + self.proxy

    def reset_req(self):
        """
        重置请求，拿出新的查询条件，并将请求起始位置重置为0
        :return:
        """
        # 从查询条件的ssdb队列中获取查询条件
        if DEBUG:
            self.condition = dict(eval(rand_choice(test_condition)))
        else:
            self.condition = dict(eval(self.get_wenshu_condition()))
        if self.condition["case_type"] == "0":
            self.req_data["condition"] = "/CaseInfo/案/@法院名称=*%s* AND /CaseInfo/案/@裁判日期=[%s]" \
                                         % (self.condition["court"], self.condition["date"])
        else:
            self.req_data["condition"] = "/CaseInfo/案/@法院名称=*%s* AND /CaseInfo/案/@案件类型=%s " \
                                         "AND /CaseInfo/案/@裁判日期=[%s]" \
                                         % (self.condition["court"], self.condition["case_type"],
                                            self.condition["date"])
        self.start_index = 0

    def start_requests(self):
        # 重置请求
        self.reset_req()

        try:
            request = Request(
                url=self.list_url,
                method='POST',
                callback=self.parse,
                body=json_dumps(self.req_data),
                headers=self.headers,
                dont_filter=True,
                errback=self.err_callback
            )
            self.set_proxy(request)
            yield request
        except Exception:
            self.exception_handle(self.condition, "start_requests error")

    def parse(self, response):
        self.exception_response(self.condition, response)
        self.logger.info("list_req_data->%s" % self.req_data)
        self.logger.info("skip->%s" % self.start_index)
        self.logger.info("parse_response->%s" % response.text)

        try:
            # 接收到数据先base64解码，再aes解密，并转换为字符串
            text = decrypt(b64decode(response.text)).decode("utf-8")
            # 将最后]出现的位置之后的字符全部过滤掉
            text = text[:text.rfind(']') + 1]
            docs = json_loads(text)
            self.logger.info("list->%s：%s" % (str(len(docs)), text))

            for doc in docs:
                item = WenshuItem()
                item["case_type"] = doc.get("案件类型", "")
                item["sentence_date"] = doc.get("裁判日期", "")
                item["case_name"] = doc.get("案件名称", "")
                item["file_id"] = doc.get("文书ID", "")
                item["trial_procedure"] = doc.get("审判程序", "")
                item["case_no"] = doc.get("案号", "")
                item["court_name"] = doc.get("法院名称", "")
                item["relation"] = doc.get("关联文书", "")
                # 文书ID为空则跳过
                if not item["file_id"] or self.is_wenshu_id_exists(item["file_id"]):
                    self.logger.info("%s has saved!continue!" % item["file_id"])
                    continue
                req_data = {
                    "fileId": item["file_id"],  # 文书ID
                    "reqtoken": get_reqtoken()  # 请求token
                }
                self.logger.info("doc_req_data->%s" % req_data)
                request = Request(
                    url=self.doc_url,
                    method='POST',
                    callback=self.parse_doc,
                    body=json_dumps(req_data),
                    meta={"item": item},
                    headers=self.headers,
                    dont_filter=True,
                    errback=self.err_callback
                )
                self.set_proxy(request)
                yield request

            # 让数据起始值加分页大小，好下一次请求可以请求到下一页的数据,
            self.start_index += self.page_size
            # 记录查询条件的爬取状态(已经爬取过的状态改为1)
            self.record_query_condition(self.dict_sorted(self.condition), 1)

            # 查询结果至少第一页应该有数据，否则就可能是代理的问题
            if not docs and self.start_index <= 20:
                self.logger.debug("查询结果至少第一页应该有数据，否则就可能是代理的问题")
                self.push_wenshu_condition(self.condition)
                self.proxy = self.proxy_api.get_proxy_one()  # 更换代理
                self.reset_req()

            # 如果没有数据或者start_index大于220了则读取下一个查询条件并改变查询的条件，且让start_index变为0
            if not docs or self.start_index > 220:
                # 重置请求
                self.reset_req()
            self.req_data["skip"] = str(self.start_index)
            request = Request(
                url=self.list_url,
                method='POST',
                callback=self.parse,
                body=json_dumps(self.req_data),
                headers=self.headers,
                dont_filter=True,
                errback=self.err_callback
            )
            self.set_proxy(request)
            yield request
        except Exception:
            self.exception_handle(self.condition, "parse error")

    def parse_doc(self, response):
        self.exception_response(self.condition, response)
        self.logger.info("%s" % response.url)
        item = response.meta["item"]
        text = response.text

        try:
            self.logger.info("parse_doc_response->%s" % text)
            doc = dict()
            if "m6ezxFExcBjVdXhvTG5nHQ==" not in text:
                try:
                    # 接收到数据先base64解码，再aes解密，并转换为字符串
                    text = decrypt(b64decode(text)).decode("utf-8")
                    # 将最后}出现的位置之后的字符全部过滤掉
                    text = text[:text.rfind("}") + 1]
                    # 过滤掉反斜线
                    text = text.replace("\\", "")
                    doc = json_loads(text)
                except Exception:
                    self.logger.exception("decrypt or json_loads error")

            item["title"] = doc.get("Title", "")  # 文书标题
            item["pub_date"] = doc.get("PubDate", "")  # 发布日期
            html = doc.get("Html", "")
            if html:  # 文书内容
                item["html"] = '<meta http-equiv="Content-Type" content="text/html;charset=UTF-8">' + html
            yield item
        except Exception as e:
            self.record_wenshu_id_error(item["file_id"])
            self.exception_handle(self.condition, "parse_doc error:" + str(e))
