# -*- coding: utf-8 -*-

from scrapy.utils.project import get_project_settings

from crawler_bqjr.items.communications_items import UserCommunicationInfoItem
from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.spiders_settings import COMMUNICATIONS_BRAND_DICT

test_dict = {
    COMMUNICATIONS_BRAND_DICT["联通"]: {"username": "13988888888",
                                      "password": "",
                                      "province": "四川"},
    COMMUNICATIONS_BRAND_DICT["移动"]: {"username": "13988888888",
                                      "password": "",
                                      "province": "四川"},
    COMMUNICATIONS_BRAND_DICT["电信"]: {"username": "13988888888",
                                      "password": "",
                                      "province": "广东"}
}

scrapy_settings = get_project_settings()
DEBUG = scrapy_settings["DEBUG_COMMUNICATIONS_SPIDERS"]


######################################
# 验证码错误异常
######################################
class CaptchaError(Exception):
    pass


class CommunicationsSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=UserCommunicationInfoItem, **kwargs)
        self.CAPTCHA_RETRY_TIMES = 3
        self.BILL_COUNT_LIMIT = self.CALL_COUNT_LIMIT = 6
        self.CALL_PAGE_SIZE_LIMIT = 1000

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        province = account_info["province"]
        self.logger.critical("The province is: %s" % province)
        item = request.meta["item"]
        item["brand"] = account_info["brand"]
        item["province"] = account_info["province"]
        item["city"] = account_info["city"]
        return request

    # def start_requests(self):
    #     if not DEBUG:
    #         yield self.get_next_request()
    #     else:
    #         yield self.get_account_request(test_dict[self.name])
