# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyDetail2Item
from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spiders.company_spiders.base import get_one_company, CompanySpider
from data_storage.db_settings import MONGO_COMPANY_DB, \
    MONGO_COMPANY_COLLECTIONS, MONGO_COMPANY_DETAIL2_COLLECTIONS
from data_storage.mongo_db import MongoDB
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads


class Detail58Spider(CompanySpider):
    name = "detail_58"
    allowed_domains = ["qy.58.com"]
    start_urls = ["http://qy.58.com/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_DETAIL2_COLLECTIONS) as mongo_instance:
            self.name_set = set(item["name"] for item in
                                mongo_instance.getAll(fields={"name": 1, "_id": 0}))

    def start_requests(self):
        ssdb_conn = get_ssdb_conn()
        mongo_instance = MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS)
        parse_search = self.parse_search
        name_set = self.name_set
        while True:
            company = get_one_company(mongo_instance, ssdb_conn)
            if company is not None:
                company_name = company["name"]
                if company_name in name_set:
                    continue

                # form_data = {"userName": company_name
                #              }
                # request = FormRequest("http://qy.58.com/ajax/getBusinessInfo",
                #                       parse_search, dont_filter=True, formdata=form_data)
                request = Request("http://qy.58.com/ajax/getBusinessInfo?userName="
                                  + company_name, parse_search, dont_filter=True)
                request.meta["company_other_info"] = company
                yield request
            else:
                yield Request(DO_NOTHING_URL, self.do_nothing,
                              errback=self.do_nothing, dont_filter=True)

    def parse_search(self, response):
        try:
            text = response.text

            if '"status":0' in text:  # 成功
                company_other_info = response.meta["company_other_info"]
                name = company_other_info["name"]
                self.name_set.add(name)

                data = json_loads(text)
                item = CompanyDetail2Item()
                item.update(company_other_info)
                item["search_url"] = data.get("entUrl")
                item["general_business"] = data.get("businessScope", "").rstrip("^；")
                item["type"] = data.get("companyType")
                item["uniform_social_credit_code"] = data.get("creditCode")
                item["organization_code"] = data.get("orgNumber")
                item["found_date"] = data.get("estiblishDate")
                item["status"] = data.get("operatingStatus")
                item["registered_address"] = data.get("regAddress")
                item["registered_authority"] = data.get("regAuthority")
                item["registered_capital"] = data.get("regCapital")
                yield item
            else:
                self.logger.warning("58_AJAX---搜索公司失败")
        except Exception:
            self.logger.exception("58_AJAX---搜索公司异常")
