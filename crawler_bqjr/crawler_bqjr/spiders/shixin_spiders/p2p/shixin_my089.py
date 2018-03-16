# -*- coding: utf-8 -*-

from scrapy import Spider
from scrapy.http import FormRequest
from global_utils import json_loads

from crawler_bqjr.items.shixin_items import P2PItem


class ShixinMy089Spider(Spider):
    name = "shixin_my089"
    allowed_domains = ["my089.com"]

    custom_settings = {
        'DOWNLOAD_DELAY': 300,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url = "https://www.my089.com/help/blackList"
        self.post_data = {
            "totalPage": "",
            "currentPage": "",
            "loginUserName": "",
            "maxOverdueDayStart": "",
            "maxOverdueDayEnd": "",
            "province": "",
            "city": "",
            "overdueTime": ""
        }

    def start_requests(self):
        yield FormRequest(self.url, self.parse, formdata=self.post_data)

    def parse(self, response):
        result = json_loads(response.text)
        user_list = result["list"]
        for user in user_list:
            item = P2PItem()
            item["from_web"] = ShixinMy089Spider.allowed_domains[0]
            item["name"] = user["realName"]
            item["id"] = user["certNumber"]

            # 获取个人详情
            personal_detail = dict()
            personal_detail["用户名"] = user.get("loginUsername", "")
            personal_detail["E-Mail"] = user.get("boundEmail", "")
            personal_detail["身份证地址"] = user.get("certAddress", "")
            personal_detail["手机"] = user.get("mobile", "")
            personal_detail["电话"] = user.get("telephone", "")
            personal_detail["应急联系人"] = user.get("secondName", "")
            personal_detail["应急手机"] = user.get("secondMobile", "")
            item["personal_detail"] = personal_detail

            # 获取账户详情
            account_detail = dict()
            account_detail["待还总额"] = user.get("totalArrears", "")
            account_detail["逾期笔数"] = user.get("unPayCount", "")
            account_detail["未逾期本息总额"] = "0.00"
            account_detail["逾期本息总额"] = user.get("totalAmount", 0) + user.get("totalInterest", 0)
            account_detail["待还违约金"] = user.get("totalLateFee", "")
            account_detail["待还催收费用"] = user.get("totalPenalty", "")
            item["account_detail"] = account_detail
            item["debt_detail"] = {
                "逾期未还款": user.get("unPayCount", ""),
                "被垫付款": user.get("payCount", ""),
                "最长逾期天数": user.get("maxOverdueDay", ""),
                "欠款总额": user.get("totalArrears", ""),
                "详情": []
            }

            post_data = {
                "totalPage": "",
                "currentPage": "",
                "blackUid": user["uid"]
            }
            url = "https://www.my089.com/help/blackRepaymentPlant"
            yield FormRequest(url, self.parse_detail, meta={"item": item}, formdata=post_data)

        currentPage = result["page"]["currentPage"]
        totalPage = result["page"]["totalPage"]
        self.post_data["currentPage"] = str(currentPage + 1)
        if currentPage < totalPage:
            yield FormRequest(self.url, self.parse, formdata=self.post_data)

    def parse_detail(self, response):
        item = response.meta["item"]
        result = json_loads(response.text)
        detail_list = result["list"]
        for detail in detail_list:
            detail_tmp = dict()
            detail_tmp["借款标题"] = detail["title"]
            detail_tmp["还款本息"] = detail["planAmount"]
            detail_tmp["应还利息"] = detail["interestAmount"]
            detail_tmp["还款日期"] = detail["planTime"]
            detail_tmp["逾期天数"] = detail["overdueDays"]
            detail_tmp["还款状态"] = "网站垫付" if detail["repaymentStatus"] == -3 else "未知"
            item["debt_detail"]["详情"].append(detail_tmp)
        yield item
