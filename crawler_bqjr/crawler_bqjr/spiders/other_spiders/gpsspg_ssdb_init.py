# -*- coding: utf-8 -*-

from data_storage.ssdb_db import get_ssdb_conn
from data_storage.db_settings import SSDB_ADDRESS_QUEUE
from csv import DictReader


FILE_PATH = "E:/address/address.csv"

class GpsspgTool:
    def __init__(self):
        self.ssdb_conn = get_ssdb_conn()

    def push_address_queue(self, address):
        try:
            self.ssdb_conn.qpush_back(SSDB_ADDRESS_QUEUE, address)
        except Exception as e:
            print(str(e))
            input("push_address_queue error，输入任意内容回车后继续：")
            return

    def clear_address_queue(self):
        try:
            self.ssdb_conn.qclear(SSDB_ADDRESS_QUEUE)
        except Exception as e:
            print(str(e))
            input("clear_address_queue error，输入任意内容回车后继续：")
            return

    def init_ssdb(self):
        # 清空地址队列
        self.clear_address_queue()
        # 将csv中的信息读取出来放入到ssdb队列中
        print("init ssdb begin...")
        with open(FILE_PATH, encoding="utf-8") as csvfile:
            reader = DictReader(csvfile)
            for line in reader:
                address = "%s|$|%s" % (line['\ufeff"id"'], line["addr"])
                print(address)
                self.push_address_queue(address)
        print("init ssdb done!")


if __name__ == "__main__":
    tool = GpsspgTool()
    tool.init_ssdb()