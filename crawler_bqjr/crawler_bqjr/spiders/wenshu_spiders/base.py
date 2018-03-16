# -*- coding: utf-8 -*-

from multiprocessing import Lock
from os import system as os_system, getpid
from time import sleep

from scrapy.http import Request

from crawler_bqjr.spider_class import NoticeClosedSpider
from data_storage.db_settings import MONGO_WENSHU_DB, MONGO_WENSHU_CONDITION_COLLECTIONS, \
    SSDB_WENSHU_CONDITION_QUEUE, SSDB_WENSHU_ID_HSET, SSDB_WENSHU_ID_ERROR_HSET
from data_storage.mongo_db import MongoDB
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_dumps
from proxy_api.proxy_utils import ProxyApi


class WenshuSpider(NoticeClosedSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssdb_conn = get_ssdb_conn()
        self.mongo_instance = MongoDB(MONGO_WENSHU_DB, MONGO_WENSHU_CONDITION_COLLECTIONS)
        self.proxy_api = ProxyApi()
        self.proxy = self.proxy_api.get_proxy_one()
        self.pid = getpid()
        self.lock = Lock()
        self.logger.info("init pid->%d" % self.pid)

    def is_query_condition_exists(self, condition):
        try:
            condition = json_dumps(self.dict_sorted(condition), ensure_ascii=False)
            result = self.mongo_instance.getOne(filter={"condition": condition},
                                                fields={"condition": 1, "status": 1, "_id": 0})
            if result:
                return True
        except Exception:
            pass
        return False

    def record_query_condition(self, condition, status=0):
        try:
            condition = json_dumps(self.dict_sorted(condition), ensure_ascii=False)
            item = {
                "condition": condition,
                "status": status,
            }
            self.mongo_instance.insertOne(item)
        except Exception:
            return

    def push_query_condition_queue(self, condition):
        try:
            condition = json_dumps(self.dict_sorted(condition), ensure_ascii=False)
            self.ssdb_conn.qpush_back(SSDB_WENSHU_CONDITION_QUEUE, condition)
        except Exception:
            return

    def clear_query_condition(self):
        try:
            self.mongo_instance.deleteMany(filter={})
            self.ssdb_conn.qclear(SSDB_WENSHU_CONDITION_QUEUE)
        except Exception:
            return

    def get_wenshu_condition(self):
        try:
            return self.ssdb_conn.qpop_front(SSDB_WENSHU_CONDITION_QUEUE)
        except Exception:
            pass
        return {}

    def push_wenshu_condition(self, condition):
        try:
            self.ssdb_conn.qpush_back(SSDB_WENSHU_CONDITION_QUEUE, condition)
        except Exception:
            return

    def is_wenshu_id_exists(self, file_id):
        try:
            return self.ssdb_conn.hexists(SSDB_WENSHU_ID_HSET, file_id)
        except Exception:
            return True

    def record_wenshu_id_error(self, file_id):
        try:
            self.ssdb_conn.hset(SSDB_WENSHU_ID_ERROR_HSET, file_id, "")
        except Exception:
            return

    def reset_wenshu_condition(self):
        try:
            # 清空队列列表
            self.ssdb_conn.qclear(SSDB_WENSHU_CONDITION_QUEUE)
            # 将hset里面状态为0的插入到队列
            cursor = self.mongo_instance.getAll(filter={"status": 0},
                                                fields={"condition": 1, "status": 1, "_id": 0})
            for item in cursor:
                self.push_query_condition_queue(item["condition"])
        except Exception:
            pass
        return

    def exception_handle(self, condition, error_info):
        try:
            if self.name != "condition_spider":
                # script_name = "start_pc.sh" if self.name == "wenshu_pc_spider" else "start_app.sh"
                # 出现任何异常，再把出错的查询条件重新再加入到查询队列
                self.push_wenshu_condition(condition)
                self.logger.info("parse or parse_doc error->%s" % str(error_info))
                # 判断接收到的内容是否为空，或者包含rtn等字样，如果有的话，则说明已经被服务器屏蔽了，暂停三分钟，继续尝试
                self.logger.info("sleep start!")
                sleep(5)  # 暂停5秒钟
                self.logger.info("sleep end!")
                # 更换代理
                self.proxy = self.proxy_api.get_proxy_one()  # 更换代理
                self.logger.error("request retry")
                # 重新请求当前条件
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
            self.exception_handle(condition, "change proxy error!")

            # os_system("kill -9 %d" % pid)
            # os_system("kill -9 %d && nohup /opt/test_wenshu/crawler/crawler_bqjr/%s >/dev/null 2>&1 &" % (pid, script_name))
            # def start_wenshu_crawler(spider):
            #     self.logger.info("begin new process")
            #     process = CrawlerProcess(get_project_settings())
            #     process.crawl(spider)
            #     process.start()
            # p = Process(target=start_wenshu_crawler, args=(self,))
            # p.start()
            # # 获取pid并杀死进程，通过nohup再重启下爬虫
            # pid = getpid()
            # self.logger.info("kill pid->%d" % pid)
            # kill(pid, 9)

    def exception_response(self, condition, response):
        if response.status != 200 \
                or "/Html_Pages/VisitRemind.html" in response.text \
                or response.text == "atZtw/muLK3OdYWrljShpg==":
            # 抓取文章出现任何异常，则把出错的信息加入到未抓取到的列表中方便以后查看或者重新采集
            self.exception_handle(condition, "status code:" + str(response.status))

    def dict_sorted(self, data):
        return sorted(data.items(), key=lambda t: len(t[0]), reverse=True)

    def closed(self, reason):
        if self.name != "condition_spider":
            self.lock.acquire()
            try:
                msg = super().closed(reason)
                self.logger.error("spider closed, pid->%d, reason->%s" % (self.pid, msg))
                with open("count.txt", "r") as f:
                    count = int(f.read())
                count += 1
                if count >= 20:
                    with open("pid.txt", "r") as f:
                        parent_pid = int(f.read())
                    self.logger.error("kill pid->%d, parent pid->%d, restart now!"
                                      % (self.pid, parent_pid))
                    os_system("nohup /opt/test_wenshu/crawler/crawler_bqjr/start_app.sh "
                              ">/dev/null 2>&1 &")
                    os_system("kill -9 %d" % self.pid)
                else:
                    with open("count.txt", "w") as f:
                        f.write(str(count))
                    self.logger.error("kill pid->%d" % self.pid)
                    os_system("kill -9 %d" % self.pid)
            except Exception:
                self.logger.error("kill pid or restart error!")
            self.lock.release()

    def err_callback(self, failure):
        self.logger.error("request error->%s" % repr(failure))
        if self.name in ["wenshu_pc_spider", "wenshu_app_spider"]:
            self.exception_handle(self.condition, "request failure, change proxy!")

    # @classmethod
    # def from_crawler(cls, crawler, *args, **kwargs):
    #     spider = super(WenshuSpider, cls).from_crawler(crawler, *args, **kwargs)
    #     crawler.signals.connect(spider.spider_closed, signals.spider_closed)
    #     return spider
