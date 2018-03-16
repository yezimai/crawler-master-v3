# -*- coding: utf-8 -*-

from itertools import islice
from time import sleep

from scrapy import FormRequest, Request

from crawler_bqjr.items.company_items import CompanyDetailItem
from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spiders.company_spiders.base import get_one_company, CompanySpider
from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS, MONGO_COMPANY_DETAIL_COLLECTIONS
from data_storage.mongo_db import MongoDB
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads


class DetailSzmqsSpider(CompanySpider):
    name = "szmqs"
    allowed_domains = ["szmqs.gov.cn"]
    start_urls = ["http://app03.szmqs.gov.cn/xyjggs.webui/xyjggs/List.aspx"]
    sleep_time = 8

    custom_settings = {
        'DOWNLOAD_DELAY': 6,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.proxy_api = ProxyApi()
        self.WEBSITE_BUSY_STR = "过于频繁，请稍"
        with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL_COLLECTIONS) as mongo_instance:
            self.name_set = set(item["name"] for item in
                                mongo_instance.getAll(fields={"name": 1, "_id": 0}))

    def _add_proxy(self, request):
        # proxy = self.proxy_api.get_proxy_one()
        # request.meta["proxy"] = "http://" + proxy
        pass

    def get_search_request(self):
        ssdb_conn = get_ssdb_conn()
        mongo_instance = MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS)
        _add_proxy = self._add_proxy
        parse_search = self.parse_search
        name_set = self.name_set
        while True:
            company = get_one_company(mongo_instance, ssdb_conn)
            if company is not None:
                company_name = company["name"]
                if company_name in name_set:
                    continue

                form_data = {"action": "getSSDJBList",
                             "keyword": company_name,
                             "PageIndex": "1",
                             }
                request = FormRequest("http://app03.szmqs.gov.cn/xyjggs.webui/xyjggs/Ajax/Ajax.ashx",
                                      parse_search, dont_filter=True, formdata=form_data)
                request.meta["company_other_info"] = company
                _add_proxy(request)
                yield request
            else:
                yield Request(DO_NOTHING_URL, self.do_nothing,
                              errback=self.do_nothing, dont_filter=True)

    def get_page_requests(self, action):
        _add_proxy = self._add_proxy
        parse_search = self.parse_search
        for i in range(1, 21):
            form_data = {"action": action,
                         "keyword": "",
                         "PageIndex": str(i),
                         }
            request = FormRequest("http://app03.szmqs.gov.cn/xyjggs.webui/xyjggs/Ajax/Ajax.ashx",
                                  parse_search, dont_filter=True, formdata=form_data)
            _add_proxy(request)
            yield request

    def start_requests(self):
        yield from self.get_page_requests("getNBList")  # 年报公示信息
        yield from self.get_page_requests("getSSDJBList")  # 商事登记薄
        yield from self.get_page_requests("getYCMLList")  # 经营异常名单
        yield from self.get_page_requests("getXZCFList")  # 行政处罚信息
        # yield from self.get_page_requests("getYZWFList")  # 严重违法失信企业名单
        # yield from self.get_page_requests("getCCJCGSList")  # 抽查检查结果
        yield from self.get_search_request()

    def parse_search(self, response):
        try:
            text = response.text

            if '"IsSuccessed":true' in text:  # 成功
                datas = json_loads(text)
                name_set = self.name_set
                for i in datas["Data"]["Items"]:
                    name = i.get("EntName") or i["entname"]
                    if name in name_set:
                        continue
                    name_set.add(name)

                    the_id = i.get("RecordID") or i["recordid"]
                    request = Request("http://app03.szmqs.gov.cn/xyjggs.webui/xyjggs/Detail.aspx?id="
                                      + the_id, self.parse_detail, meta=response.meta, dont_filter=True)
                    self._add_proxy(request)
                    yield request
            elif self.WEBSITE_BUSY_STR in text:
                self.logger.warning("深圳szmqs---查询过于频繁")
                sleep(self.sleep_time)
                yield response.request
            elif '"rtn":108545' in text:
                self.logger.error("深圳szmqs---返回108545")
                sleep(self.sleep_time)
                yield response.request
            else:
                self.logger.error("深圳szmqs---搜索公司失败")
        except Exception:
            self.logger.exception("深圳szmqs---搜索公司异常")

    def _get_basic_info_from_table(self, tr_list):
        data_dict = {}
        for tr in islice(tr_list, 1, None):
            k1, v1, k2, v2 = tr.xpath("td/text()").extract()
            data_dict[k1.strip()] = v1
            data_dict[k2.strip()] = v2

        return data_dict

    def _get_list_info_from_table(self, tr_list):
        ret_list = []
        for tr in islice(tr_list, 2, None):
            ret_list.append([i.strip() for i in tr.xpath("td/text()").extract()])
        return ret_list

    def parse_detail(self, response):
        text = response.text
        if self.WEBSITE_BUSY_STR in text:
            self.logger.warning("深圳szmqs---访问过于频繁")
            sleep(self.sleep_time)
            yield response.request
        elif '"rtn":108545' in text:
            self.logger.error("深圳szmqs---返回108545")
            sleep(self.sleep_time)
            yield response.request
        else:
            item = {"search_url": response.url}

            basic_info = None
            for table in response.xpath("//li[@data='info']/div[@id='rig11']/table"):
                tr_list = table.xpath("tr")
                title = tr_list[0].xpath("td/text()").extract_first()
                if "基本信息" == title:
                    basic_info = self._get_basic_info_from_table(tr_list)
                elif "股东信息" == title:
                    item["shareholder_info"] = self._get_list_info_from_table(tr_list)
                elif "成员信息" == title:
                    item["member_info"] = self._get_list_info_from_table(tr_list)
                else:
                    self.logger.error("深圳szmqs---未知title：" + title)

            if basic_info:
                item["name"] = basic_info.get("企业名称") or basic_info.get("名称") \
                               or response.xpath("//h2/text()").extract_first()
                item["registration_code"] = basic_info.get("注册号")
                item["uniform_social_credit_code"] = basic_info.get("统一社会信用代码")
                item["legal_person"] = (basic_info.get("法定代表人") or basic_info.get("经营者")
                                        or basic_info.get("投资人") or basic_info.get("负责人")
                                        or basic_info.get("执行合伙人") or basic_info.get("母公司名称")
                                        or basic_info.get("隶属企业名称"))
                item["registered_address"] = (basic_info.get("住所") or basic_info.get("营业场所")
                                              or basic_info.get("经营场所"))
                item["found_date"] = basic_info.get("成立日期") or basic_info.get("集团成立日期")
                item["business_period"] = basic_info.get("营业期限") or basic_info.get("经营期限")
                item["check_date"] = basic_info.get("核准日期")
                item["registered_capital"] = (basic_info.get("认缴注册资本总额") or basic_info.get("注册资金")
                                              or basic_info.get("注册资本") or basic_info.get("出资额")
                                              or basic_info.get("注册资本（金）总和（万元）"))
                item["type"] = (basic_info.get("企业类型") or basic_info.get("组成形式")
                                or basic_info.get("经济性质") or basic_info.get("经营性质"))
                item["general_business"] = basic_info.get("一般经营项目")
                item["licensed_business"] = basic_info.get("许可经营项目")
                item["status"] = basic_info.get("企业登记状态")

            for k, v in item.items():
                if v is None:
                    self.logger.warning("深圳szmqs---URL(%s)表格异常：(%s)" % (response.url, k))
                    break

            yield_item = CompanyDetailItem()
            meta = response.meta
            if "company_other_info" in meta:
                yield_item.update(meta["company_other_info"])
            yield_item.update(item)
            yield_item["html"] = text

            yield yield_item
