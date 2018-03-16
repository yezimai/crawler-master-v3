# -*- coding: utf-8 -*-

from datetime import datetime
from random import random as rand_0_1
from re import compile as re_compile
from time import sleep
from traceback import print_exc
from urllib.parse import parse_qs, urlsplit, urlencode

from scrapy import FormRequest, Request
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.web.client import ResponseNeverReceived

from crawler_bqjr.captcha.recognize_captcha import recognize_captcha_auto
from crawler_bqjr.items.shixin_items import ZhixingDetailItem
from crawler_bqjr.spider_class import PhantomJSWebdriverSpider
from crawler_bqjr.spiders.shixin_spiders.base import TwoWordsNameSearchSpider
from crawler_bqjr.utils import get_content_by_requests, get_headers_from_response
from data_storage.db_settings import MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS
from data_storage.mongo_db import MongoDB, MONGO_DESCENDING
from data_storage.ssdb_db import get_ssdb_conn
from global_utils import json_loads

SSDB_ZHIXING_ID_HSET_NAME = "spider_zhixing_id_hset"


def record_all_zhixing_id():
    ssdb_conn = get_ssdb_conn()
    ssdb_conn.hclear(SSDB_ZHIXING_ID_HSET_NAME)

    with MongoDB(MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"link_id": 1, "_id": 0}):
            try:
                ssdb_conn.hset(SSDB_ZHIXING_ID_HSET_NAME, item["link_id"], "")
            except Exception:
                print_exc()

    ssdb_conn.close()

    print("record_all_zhixing_id done.")


def count_zhixing_id(mongo_instance):
    id_set = set()
    company_count = 0
    for i in mongo_instance.getAll(fields={"_id": 0, "name": 1, "id": 1}):
        try:
            the_id = i.get("id", "")
            name = i["name"]
            key = name + the_id
            if key not in id_set:
                id_set.add(key)
                if len(the_id) < 19 and len(name) > 4:
                    company_count += 1
        except Exception:
            print_exc()
    total_count = len(id_set)
    print("Zhixing total_count[%d], person_count[%d], company_count[%d]"
          % (total_count, total_count - company_count, company_count))
    del id_set


def del_duplicate_zhixing():
    file_code_set = set()
    duplicate_ids = []
    with MongoDB(MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS) as mongo_instance:
        for item in mongo_instance.getAll(fields={"link_id": 1}, sort=[("_id", MONGO_DESCENDING)]):
            try:
                file_code = item["link_id"]
                if file_code not in file_code_set:
                    file_code_set.add(file_code)
                else:
                    duplicate_ids.append(item["_id"])
            except Exception:
                print_exc()
        del file_code_set

        for the_id in duplicate_ids:
            mongo_instance.deleteOne(filter={"_id": the_id})

        count_zhixing_id(mongo_instance)

    print("Del %d of duplicated item in collection[%s]"
          % (len(duplicate_ids), MONGO_ZHIXING_DETAIL_COLLECTIONS))
    del duplicate_ids


class ZhixingCourtSpider(TwoWordsNameSearchSpider, PhantomJSWebdriverSpider):
    name = "zhixing_court"
    allowed_domains = ["court.gov.cn"]
    start_urls = ["http://zhixing.court.gov.cn/search/index_form.do"]

    custom_settings = {
        'DOWNLOAD_DELAY': 0.4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'REDIRECT_ENABLED': False,  # 访问频繁会被重定向
        'HTTPERROR_ALLOWED_CODES': [302]
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, load_images=False, ssdb_hset_for_record="spider_zhixing_name_hset", **kwargs)

        self.numbers_pattern = re_compile(r'\((\d+)\)')
        self.sleep_time = 60 * 5
        self.captcha_id = ""
        self.captcha_code = ""

    def start_requests(self):
        yield Request(self.start_urls[0], self.parse, errback=self.err_callback)

    def err_callback(self, failure):
        if failure.check(HttpError) and failure.value.response.status == 500:
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            return  # 执行人的详情，有时会出现500错误，所以忽略

        self.logger.warning(repr(failure))

        if hasattr(failure, "type") and failure.type is ResponseNeverReceived:  # 被封锁了
            self.logger.warning("连接被重置")
            sleep(60 * 10)

        try:
            return failure.request
        except Exception:
            self.logger.exception("err_callback except")
            search_word = self.get_next_search_word()
            if search_word:
                return self._get_search_request(search_word)

    def _get_captcha_code(self, captcha_body):
        return recognize_captcha_auto(captcha_body)

    def get_captcha_code(self, response):
        """
        获取验证码并识别，返回识别的验证码
        """
        headers = get_headers_from_response(response)
        sleep_time = self.settings.get("DOWNLOAD_DELAY", 0.3)
        captcha_id = self.captcha_id
        _get_captcha_code = self._get_captcha_code
        while True:
            form_data = {"captchaId": captcha_id,
                         "random": str(rand_0_1()),
                         }
            try:
                captcha_body = get_content_by_requests("http://zhixing.court.gov.cn/search/captcha.do?"
                                                       + urlencode(form_data), headers=headers)
            except Exception:
                sleep(sleep_time)
                continue

            if captcha_body.startswith(b"<"):
                self.logger.error("被执行人---验证码：请开启JavaScript并刷新该页")
                sleep(self.sleep_time)
                continue

            captcha_code = _get_captcha_code(captcha_body)
            if len(captcha_code) == 4:
                return captcha_code
            sleep(sleep_time)

    def _get_search_request(self, name, page="1"):
        self.logger.info("search name(%s) page(%s)" % (name, page))

        form_data = {"searchCourtName": "全国法院（包含地方各级法院）",
                     "selectCourtId": "1",
                     "selectCourtArrange": "1",
                     "cardNum": "",
                     "pname": name,
                     "j_captcha": self.captcha_code,
                     "captchaId": self.captcha_id,
                     "currentPage": page,
                     }
        return FormRequest("http://zhixing.court.gov.cn/search/newsearch", self.parse_search,
                           dont_filter=True, formdata=form_data, errback=self.err_callback)

    def parse(self, response):
        search_word = self.get_next_search_word()
        if not search_word:
            return

        captchaImg_xpath = "//img[@id='captchaImg']"
        captcha_img = response.xpath(captchaImg_xpath)
        if captcha_img:
            src = captcha_img.xpath("@src").extract_first("")
            src = response.urljoin(src)
        else:
            while True:
                driver = self.load_page_by_webdriver(response.url, captchaImg_xpath)
                try:
                    captcha_img = driver.find_element_by_xpath(captchaImg_xpath)
                    src = captcha_img.get_attribute("src")
                    break
                except Exception:
                    sleep(self.sleep_time)
                finally:
                    driver.quit()

        form_data = parse_qs(urlsplit(src).query)
        self.captcha_id = form_data["captchaId"][0]
        self.captcha_code = self.get_captcha_code(response)

        yield self._get_search_request(search_word)

    def parse_search(self, response):
        meta = response.meta
        text = response.text

        error = False
        if response.status == 302:
            self.logger.error("被执行人---搜索：访问频繁")
            sleep(self.sleep_time)
            error = True
        elif "验证码出现错" in text:
            self.logger.warning("被执行人---搜索验证码错误。")
            error = True
        elif "请开启J" in text:
            self.logger.error("被执行人---搜索：请开启JavaScript并刷新该页")
            sleep(self.sleep_time)
            error = True

        if error:
            form_data = parse_qs(response.request.body.decode())
            name = form_data["pname"][0]
            page = form_data["currentPage"][0]

            old_captcha_code = form_data["j_captcha"][0]
            if old_captcha_code == self.captcha_code:
                self.captcha_code = self.get_captcha_code(response)

            yield self._get_search_request(name, page)
        else:
            captcha_id = self.captcha_id
            captcha_code = self.captcha_code

            sel_list = response.xpath("//table[@id='Resultlist']/tbody/tr[@style]")
            # if not sel_list:
            #     self.notice_change("No data found!!!!! " + response.url)

            parse_item = self.parse_item
            err_callback = self.err_callback
            update_time = datetime.now()
            for sel in sel_list:
                tds = sel.xpath("td//text()").extract()
                name, on_file_date, file_code = tds[1:4]
                link_id = int(sel.xpath("td[last()]/a/@id").extract_first())
                if self.ssdb_conn.hexists(SSDB_ZHIXING_ID_HSET_NAME, link_id):
                    continue

                item = ZhixingDetailItem()
                item["name"] = name
                item["on_file_date"] = on_file_date
                item["file_code"] = file_code
                item["link_id"] = link_id
                item["update_time"] = update_time

                form_data = {"id": str(link_id),
                             "j_captcha": captcha_code,
                             "captchaId": captcha_id,
                             }
                request = Request("http://zhixing.court.gov.cn/search/newdetail?"
                                  + urlencode(form_data), parse_item, meta=meta,
                                  dont_filter=True, errback=err_callback)
                request.meta["item"] = item
                yield request

            next_page = response.xpath("//a[text()='下一页']/@onclick").extract_first()
            if next_page and len(sel_list) >= 10:
                page = self.numbers_pattern.search(next_page).group(1)
                form_data = parse_qs(response.request.body.decode())
                name = form_data["pname"][0]
                yield self._get_search_request(name, page)
            else:
                search_word = self.get_next_search_word()
                if search_word:
                    yield self._get_search_request(search_word)

    def parse_item(self, response):
        text = response.text
        item = response.meta["item"]
        try:
            error = False
            if response.status == 302:
                self.logger.error("被执行人---详情：访问频繁")
                sleep(self.sleep_time)
                error = True
            elif text == "{}":
                self.logger.warning("被执行人---详情验证码错误。")
                error = True
            elif "请开启J" in text:
                self.logger.error("被执行人---详情：请开启JavaScript并刷新该页")
                sleep(self.sleep_time)
                error = True
            elif text.startswith("<!DOCTYPE"):
                yield item
                return

            if error:
                form_data = parse_qs(urlsplit(response.url).query)
                old_captcha_code = form_data["j_captcha"][0]
                if old_captcha_code == self.captcha_code:
                    self.captcha_code = self.get_captcha_code(response)

                form_data_new = {"id": form_data["id"][0],
                                 "j_captcha": self.captcha_code,
                                 "captchaId": self.captcha_id,
                                 }
                yield Request("http://zhixing.court.gov.cn/search/newdetail?"
                              + urlencode(form_data_new), self.parse_item,
                              dont_filter=True, meta=response.meta, errback=self.err_callback)
            else:
                data = json_loads(text)
                item["id"] = data.get("partyCardNum", "")
                item["execution_court"] = data.get("execCourtName")
                item["execution_money"] = data.get("execMoney")
                yield item
        except Exception:
            self.logger.exception("text(%s) url(%s)" % (text, response.url))


if __name__ == '__main__':
    with MongoDB(MONGO_SHIXIN_DB, MONGO_ZHIXING_DETAIL_COLLECTIONS) as mongo_instance:
        count_zhixing_id(mongo_instance)
