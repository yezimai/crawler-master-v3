# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from math import ceil
from time import sleep

from requests import Session, adapters
from requests.exceptions import ProxyError

from crawler_bqjr.spiders.wenshu_spiders.base import WenshuSpider
from data_storage.db_settings import MONGO_WENSHU_DB, MONGO_CHINACOURT_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_ASCENDING
from global_utils import json_loads, json_dumps


class ConditionSpider(WenshuSpider):
    """
    查询条件生成爬虫
    生成记录：
    1、2017-03-01至2017-03-31
    2、2017-02-01至2017-02-28
    3、2017-01-01至2017-01-31
    4、2016-12-01至2016-12-31
    5、2016-11-01至2016-11-30
    6、2016-10-01至2016-10-31
    7、2016-09-01至2016-09-30
    """

    name = "condition_spider"
    allowed_domains = ["wenshu.court.gov.cn"]

    custom_settings = {
        "DOWNLOAD_DELAY": 0.2,
        # "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "HTTPERROR_ALLOWED_CODES": [400, 401, 403, 404, 500, 501, 502, 503],
        # "RETRY_ENABLED": True,
        # "RETRY_TIMES": 1000,
        # "DOWNLOAD_TIMEOUT": 180,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.start_date = "2016-09-01"  # 查询起始日期
        # self.end_date = "2016-09-30"  # 查询截止日期
        self.start_date = kwargs["start_date"]  # 查询起始日期
        self.end_date = kwargs["end_date"]  # 查询截止日期
        self.count_url = "http://wenshu.court.gov.cn/List/ListContent"  # 获取查询的数量（文书网站url）
        self.generate_query()
        self.logger.info("%s TO %s query condition compelete!" % (self.start_date, self.end_date))
        self.one_day = timedelta(days=1)
        self.headers = {
            "Origin": "http://wenshu.court.gov.cn",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "http://wenshu.court.gov.cn",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "close",
        }

    def generate_query(self):
        """
        生成查询条件并存入到查询队列
        :return:
        """
        self.logger.info("query condition init begin!")

        # 查询法院（查询条件）
        mongo_instance = MongoDB(MONGO_WENSHU_DB, MONGO_CHINACOURT_COLLECTIONS)
        # 设置游标不超时
        cursor = mongo_instance.getAll(fields={"_id": 1, "name": 1},
                                       sort=[("province", MONGO_ASCENDING)], no_cursor_timeout=True)
        court_list = [court["name"] for court in cursor]
        # 案件类型
        case_type_list = ["1", "2", "3", "4", "5"]
        for court in court_list:
            count = 1
            avg_interval = 0  # 当数量很大的时候直接使用总数/220的数字来代替间隔天数
            avg_interval_first = 0
            start_date = datetime.strptime(self.start_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date, "%Y-%m-%d")
            while True:
                divisor = (count ** 2) if count != 2 else 2
                # 平均间隔天数
                interval_day = avg_interval if avg_interval > 0 else ceil((end_date - start_date).days / divisor)
                if avg_interval_first > 0:
                    avg_interval = avg_interval_first
                    avg_interval_first = 0
                self.logger.info("interval_day->%s" % interval_day)

                # 生成查询时间段
                end_date_temp = min(start_date + timedelta(days=interval_day), end_date)
                query_date = "%s TO %s" % (start_date.strftime("%Y-%m-%d"), end_date_temp.strftime("%Y-%m-%d"))
                self.logger.info("query_date->%s!" % query_date)
                query_condition = dict()
                query_condition["case_type"] = "0"  # 所有类型
                query_condition["court"] = court
                query_condition["date"] = query_date
                if self.is_query_condition_exists(query_condition):
                    if end_date == end_date_temp:
                        self.logger.info("%s query_condition exists!break!" % court)
                        break
                    else:
                        start_date = end_date_temp + self.one_day
                        self.logger.info("%s query_condition exists!continue!"
                                         % json_dumps(query_condition))
                        continue
                # 查询到数量小于等于220的加到小于220的列表中,并跳出该循环
                query_count = self.get_count_by_condition(court=court, date=query_date)
                if 0 <= query_count <= 220:
                    if query_count > 0:
                        self.record_query_condition(query_condition)
                        self.push_query_condition_queue(query_condition)
                    # 查询结果为0，只保存到mongo并且状态为-1
                    if query_count == 0:
                        self.record_query_condition(query_condition, -1)
                    if end_date == end_date_temp:
                        if count > 1:
                            # 每个法院轮询生成查询条件的日期也放到mongodb，状态为-1
                            init_date = "%s TO %s" % (self.start_date, self.end_date)
                            query_condition["date"] = init_date
                            self.record_query_condition(query_condition, -1)
                        self.logger.info("%s query condition end!" % court)
                        break
                    else:
                        start_date = end_date_temp + self.one_day
                else:
                    if count > 1:
                        avg_interval_first = avg_interval
                    temp_days = (end_date_temp - start_date).days
                    try:
                        avg_interval = int(180 / (int(query_count) / temp_days))
                    except ZeroDivisionError:
                        self.logger.exception("爬取出错，出错原因：")
                        break
                    # 如果间隔时间都为1天查询到的结果还大于220的话，则在保存条件的时候再增加案件类型进行保存
                    if temp_days == 1:
                        for case_type in case_type_list:
                            query_condition["case_type"] = case_type
                            if not self.is_query_condition_exists(query_condition):
                                self.record_query_condition(query_condition)
                                self.push_query_condition_queue(query_condition)
                        if end_date == end_date_temp:
                            if count > 1:
                                # 每个法院轮询生成查询条件的日期也放到mongodb，状态为-1
                                init_date = "%s TO %s" % (self.start_date, self.end_date)
                                query_condition["date"] = init_date
                                self.record_query_condition(query_condition, -1)
                            self.logger.info("%s query condition end!" % court)
                            break
                        else:
                            start_date = end_date_temp + self.one_day
                count += 1
        self.logger.info("query condition init end!")

    def get_count_by_condition(self, court, date):
        """
        根据查询条件得到要查询条件对应的结果数量
        :param court:
        :param date:
        :return:
        """
        adapters.DEFAULT_RETRIES = 5
        while True:
            sleep(0.5)  # 每次请求至少间隔0.5秒
            try:
                self.logger.info("current proxy->%s" % self.proxy)
                self.logger.info("get_count_by_condition->%s,%s" % (court, date))
                data = {
                    "Param": "法院名称:%s,裁判日期:%s" % (court, date),
                    "Index": "1",
                    "Page": "5",
                    "Order": "法院层级",
                    "Direction": "asc",
                }
                proxies = {"http": "http://%s" % self.proxy, }
                s = Session()
                s.keep_alive = False
                r = s.post(self.count_url, data=data, headers=self.headers, proxies=proxies, timeout=60)
                text = r.text.replace("\\", "").strip("\"")
                self.logger.info("response text->%s" % r.text)
                result = json_loads(text)
                count = result[0]["Count"]
                self.logger.info("get_count_by_condition,count->%s" % count)
                return int(count)
            except Exception as e:
                self.logger.info("get_count_by_condition,error->%s" % str(e))
                if not isinstance(e, ProxyError):
                    self.logger.info("sleep start!")
                    sleep(5)  # 不是代理出错的话间隔5秒重试
                    self.logger.info("sleep end!")
                self.proxy = self.proxy_api.get_proxy_one()  # 更换代理


class ConditionSpider_201609(ConditionSpider):
    name = "condition_spider_201609"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-09-01", end_date="2016-09-30")


class ConditionSpider_201608(ConditionSpider):
    name = "condition_spider_201608"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-08-01", end_date="2016-08-31")


class ConditionSpider_201607(ConditionSpider):
    name = "condition_spider_201607"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-07-01", end_date="2016-07-31")


class ConditionSpider_201606(ConditionSpider):
    name = "condition_spider_201606"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-06-01", end_date="2016-06-30")


class ConditionSpider_201605(ConditionSpider):
    name = "condition_spider_201605"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-05-01", end_date="2016-05-31")


class ConditionSpider_201604(ConditionSpider):
    name = "condition_spider_201604"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-04-01", end_date="2016-04-30")


class ConditionSpider_201603(ConditionSpider):
    name = "condition_spider_201603"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-03-01", end_date="2016-03-31")


class ConditionSpider_201602(ConditionSpider):
    name = "condition_spider_201602"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-02-01", end_date="2016-02-29")


class ConditionSpider_201601(ConditionSpider):
    name = "condition_spider_201601"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2016-01-01", end_date="2016-01-31")


class ConditionSpider_201512(ConditionSpider):
    name = "condition_spider_201512"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-12-01", end_date="2015-12-31")


class ConditionSpider_201511(ConditionSpider):
    name = "condition_spider_201511"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-11-01", end_date="2015-11-30")


class ConditionSpider_201510(ConditionSpider):
    name = "condition_spider_201510"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-10-01", end_date="2015-10-31")


class ConditionSpider_201509(ConditionSpider):
    name = "condition_spider_201509"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-09-01", end_date="2015-09-30")


class ConditionSpider_201508(ConditionSpider):
    name = "condition_spider_201508"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-08-01", end_date="2015-08-31")


class ConditionSpider_201507(ConditionSpider):
    name = "condition_spider_201507"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-07-01", end_date="2015-07-31")


class ConditionSpider_201506(ConditionSpider):
    name = "condition_spider_201506"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-06-01", end_date="2015-06-30")


class ConditionSpider_201505(ConditionSpider):
    name = "condition_spider_201505"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-05-01", end_date="2015-05-31")


class ConditionSpider_201504(ConditionSpider):
    name = "condition_spider_201504"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-04-01", end_date="2015-04-30")


class ConditionSpider_201503(ConditionSpider):
    name = "condition_spider_201503"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-03-01", end_date="2015-03-31")


class ConditionSpider_201502(ConditionSpider):
    name = "condition_spider_201502"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-02-01", end_date="2015-02-28")


class ConditionSpider_201501(ConditionSpider):
    name = "condition_spider_201501"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2015-01-01", end_date="2015-01-31")


class ConditionSpider_201412(ConditionSpider):
    name = "condition_spider_201412"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-12-01", end_date="2014-12-31")


class ConditionSpider_201411(ConditionSpider):
    name = "condition_spider_201411"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-11-01", end_date="2014-11-30")


class ConditionSpider_201410(ConditionSpider):
    name = "condition_spider_201410"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-10-01", end_date="2014-10-31")


class ConditionSpider_201409(ConditionSpider):
    name = "condition_spider_201409"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-09-01", end_date="2014-09-30")


class ConditionSpider_201408(ConditionSpider):
    name = "condition_spider_201408"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-08-01", end_date="2014-08-31")


class ConditionSpider_201407(ConditionSpider):
    name = "condition_spider_201407"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-07-01", end_date="2014-07-31")


class ConditionSpider_201406(ConditionSpider):
    name = "condition_spider_201406"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-06-01", end_date="2014-06-30")


class ConditionSpider_201405(ConditionSpider):
    name = "condition_spider_201405"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-05-01", end_date="2014-05-31")


class ConditionSpider_201404(ConditionSpider):
    name = "condition_spider_201404"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-04-01", end_date="2014-04-30")


class ConditionSpider_201403(ConditionSpider):
    name = "condition_spider_201403"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-03-01", end_date="2014-03-31")


class ConditionSpider_201402(ConditionSpider):
    name = "condition_spider_201402"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-02-01", end_date="2014-02-28")


class ConditionSpider_201401(ConditionSpider):
    name = "condition_spider_201401"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2014-01-01", end_date="2014-01-31")


class ConditionSpider_201312(ConditionSpider):
    name = "condition_spider_201312"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-12-01", end_date="2013-12-31")


class ConditionSpider_201311(ConditionSpider):
    name = "condition_spider_201311"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-11-01", end_date="2013-11-30")


class ConditionSpider_201310(ConditionSpider):
    name = "condition_spider_201310"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-10-01", end_date="2013-10-31")


class ConditionSpider_201309(ConditionSpider):
    name = "condition_spider_201309"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-09-01", end_date="2013-09-30")


class ConditionSpider_201308(ConditionSpider):
    name = "condition_spider_201308"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-08-01", end_date="2013-08-31")


class ConditionSpider_201307(ConditionSpider):
    name = "condition_spider_201307"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-07-01", end_date="2013-07-31")


class ConditionSpider_201306(ConditionSpider):
    name = "condition_spider_201306"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-06-01", end_date="2013-06-30")


class ConditionSpider_201305(ConditionSpider):
    name = "condition_spider_201305"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-05-01", end_date="2013-05-31")


class ConditionSpider_201304(ConditionSpider):
    name = "condition_spider_201304"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-04-01", end_date="2013-04-30")


class ConditionSpider_201303(ConditionSpider):
    name = "condition_spider_201303"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-03-01", end_date="2013-03-31")


class ConditionSpider_201302(ConditionSpider):
    name = "condition_spider_201302"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-02-01", end_date="2013-02-28")


class ConditionSpider_201301(ConditionSpider):
    name = "condition_spider_201301"

    def __init__(self, *args, **kwargs):
        super().__init__(start_date="2013-01-01", end_date="2013-01-31")
