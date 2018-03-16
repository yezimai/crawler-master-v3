# -*- coding: utf-8 -*-

from scrapy.http import Request
from csv import DictReader
from global_utils import json_loads
from data_storage.db_settings import MONGO_OTHER_DB, MONGO_ADDRESS_COLLECTIONS, SSDB_ADDRESS_QUEUE
from data_storage.mongo_db import MongoDB
from data_storage.ssdb_db import get_ssdb_conn
from time import sleep
from random import shuffle
from crawler_bqjr.items.other_items import GpsspgItem
from crawler_bqjr.spider_class import NoticeClosedSpider

# 百度服务app key, key为ak，value为状态
BAIDU_AK = [
    {"xxwNacSMMFIktXlU70n5G44jKFzugSjI": True},
    {"fb8NkXmRf5yceQeseBLxH1kxGV5XIDq4": True},
    {"RxSOr71FupKUhKruVnAzbG5fxGcPhSHc": True},
    {"uGYxusqjp2T6PEpGU4c6lNRX617y3KSe": True},
    {"vS28uGHMjGA9P9F1l3ZVO9uHECMc9BCV": True},
    {"v39AOP782qMWqbmUIj5i54xST0sIwPZz": True},
    {"uFEZfFT3SRUGt5amtuEVaLaOBO22rILa": True}
]
# 地址csv文件路径
FILE_PATH = "E:/address/address.csv"
# 请求地址
BAIDU_URL = "http://api.map.baidu.com/geocoder/v2/?address=%s&output=json&ak=%s"


class GpsspgBaseSpider(NoticeClosedSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssdb_conn = get_ssdb_conn()
        # self.mongo_instance = MongoDB(MONGO_OTHER_DB, MONGO_ADDRESS_COLLECTIONS)

    def push_address_queue(self, address):
        try:
            self.ssdb_conn.qpush_back(SSDB_ADDRESS_QUEUE, address)
        except Exception as e:
            self.logger.error(str(e))
            input("push_address_queue error，输入任意内容回车后继续：")
            return

    def clear_address_queue(self):
        try:
            # self.mongo_instance.deleteMany(filter={})
            self.ssdb_conn.qclear(SSDB_ADDRESS_QUEUE)
        except Exception as e:
            self.logger.error(str(e))
            input("clear_address_queue error，输入任意内容回车后继续：")
            return

    def get_address_from_queue(self):
        try:
            return self.ssdb_conn.qpop_front(SSDB_ADDRESS_QUEUE)
        except Exception as e:
            self.logger.error(str(e))
            input("clear_address_queue error，输入任意内容回车后继续：")
            return

    def init_ssdb(self):
        # 清空地址队列
        self.clear_address_queue()
        # 将csv中的信息读取出来放入到ssdb队列中
        self.logger.info("init ssdb begin...")
        print("init ssdb begin...")
        with open(FILE_PATH, encoding="utf-8") as csvfile:
            reader = DictReader(csvfile)
            for line in reader:
                address = "%s|$|%s" % (line['\ufeff"id"'], line["addr"])
                print(address)
                self.push_address_queue(address)
        print("init ssdb done!")
        self.logger.info("init ssdb done!")

    def get_line(self, start_line, length):
        """
        读取csv文件的指定行
        :param start_line:
        :param end_line:
        :return:
        """
        end_line = start_line + length
        with open(FILE_PATH, encoding="utf-8") as csvfile:
            reader = DictReader(csvfile)
            for cur_line, line in enumerate(reader):
                if start_line <= cur_line < end_line:
                    yield "%s|$|%s" % (line['\ufeff"id"'], line["addr"])
                elif start_line > cur_line:
                    continue
                elif end_line < cur_line:
                    break

    def get_ak(self):
        """
        获取可用的ak
        :return:
        """
        # 随机打乱ak的顺序，方便取到不同的ak
        shuffle(BAIDU_AK)
        for ak_dict in BAIDU_AK:
            for key, value in ak_dict.items():
                if value:
                    return key
        return None

    def set_ak(self, ak_key=None, status=True):
        """
        设置ak状态
        :return:
        """
        for i, ak_dict in enumerate(BAIDU_AK):
            for key, value in ak_dict.items():
                if ak_key:
                    if key == ak_key:
                        BAIDU_AK[i][key] = status
                        return True
                else:
                    BAIDU_AK[i][key] = status
        return True

    # def is_address_exists(self, address):
    #     try:
    #         address = address.split("|$|")
    #         condtion = {"id": address[0], "address": address[1], }
    #         result = self.mongo_instance.getOne(filter=condtion)
    #         if result:
    #             return True
    #     except Exception as e:
    #         self.logger.error(str(e))
    #     return False


class GpsspgSpider(GpsspgBaseSpider):
    name = "gpsspg"
    allowed_domains = ["api.map.baidu.com"]

    custom_settings = {
        'DOWNLOAD_DELAY': 0.3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.init_ssdb()

    def get_request(self):
        while True:
            ak = self.get_ak()
            if ak:
                address = self.get_address_from_queue()
                # if self.is_address_exists(address):
                #     continue
                if address:
                    address = address.split("|$|")
                    if len(address[1]) < 15:
                        continue
                    item = {"id": address[0], "address": address[1], "ak": ak}
                    return Request(BAIDU_URL % (address[1][:40], ak), callback=self.parse, meta=item)
                else:
                    self.logger.error("ssdb队列为空，爬取完成！")
                    return None
            else:
                self.logger.error("所有账户的今日请求配额都已经用完，暂停3小时")
                sleep(60*60*3)
                # ak状态全部更新为可用
                self.set_ak(status=True)
                continue

    def start_requests(self):
        request = self.get_request()
        if request:
            yield request

    def parse(self, response):
        id = response.meta["id"]
        address = response.meta["address"]
        old_address = "%s|$|%s" % (id, address)
        ak = response.meta["ak"]
        try:
            data = json_loads(response.text)
            status = data["status"]
            if status == 0:
                item = GpsspgItem()
                item["id"] = id
                item["address"] = address
                item["lng"] = data["result"]["location"]["lng"]  # 纬度值
                item["lat"] = data["result"]["location"]["lat"]  # 经度值
                # item["precise"] = data["result"]["precise"]  # 是否精确查找
                # item["confidence"] = data["result"]["confidence"]  # 可信度
                # item["level"] = data["result"]["level"]  # 地址类型
                # print("id: %s, address: %s, lng: %s, lat: %s, precise: %s, confidence: %s, level: %s" %
                #       (item["id"], item["address"], item["lng"], item["lat"], item["precise"], item["confidence"], item["level"]))
                # 查询到的结果存入到mongodb
                yield item
            elif status == 4 or status >= 300:
                self.logger.error("ak:%s, 当日请求超出配额,%s,%s" % (ak, address, id))
                # ak超出当日限额，修改状态为不可用
                self.set_ak(ak_key=ak, status=False)
                self.push_address_queue(old_address)
            else:
                self.logger.error("ak:%s, 请求出错，状态码：%s,%s,%s" % (ak, status, address, id))
                self.push_address_queue(old_address)
        except Exception as e:
            self.logger.error("ak:%s, 处理出错，出错信息：%s,%s,%s" % (ak, str(e), address, id))
            self.push_address_queue(old_address)
        request = self.get_request()
        if request:
            yield request

