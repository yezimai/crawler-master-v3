# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider
from crawler_bqjr.spider_class import ProxySpider


class ListCnlinfo88Spider(CompanySpider, ProxySpider):
    name = "cnlinfo"
    allowed_domains = ["cnlinfo.net"]
    start_urls = ["http://shenzhen.cnlinfo.net/gongsi/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        parse_company_name = self.parse_company_name
        err_callback = self.err_callback

        sel_list = response.xpath("//a[@class='linesbg']/@href").extract()
        if not sel_list:
            self.notice_change("No href found!!!!! " + response.url)

        for url in sel_list:
            request = Request(url, callback=parse_company_name, errback=err_callback)
            self.add_proxy(request)
            yield request

    def _too_often_handler(self, response):
        self.logger.warning("访问过于频繁")
        self.change_proxy()
        request = response.request.copy()
        self.add_proxy(request)
        return request

    def parse_company_name(self, response):
        text = response.text
        if "过于频繁" in text or "<p>验证码:<input" in text:
            return self._too_often_handler(response)

        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        parse_shop = self.parse_shop
        err_callback = self.err_callback
        text_strip = self.text_strip

        sel_list = response.xpath("//ul[@class='ul_body_list']/li/div[1]/p[1]/a")
        # if not sel_list:
        #     self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            if url.startswith("http://www.cnlinfo."):
                request = Request(url, callback=parse_company, errback=err_callback)
            else:
                request = Request(url, callback=parse_shop, errback=err_callback)
            self.add_proxy(request)
            yield request

        url = response.xpath("//div[contains(@class,'box_page')]/a/span[text()='下一页']/../@href").extract_first()
        if url:
            request = Request(url, self.parse_company_name, dont_filter=True, errback=err_callback)
            self.add_proxy(request)
            yield request

    def parse_company(self, response):
        text = response.text
        if "过于频繁" in text or "<p>验证码:<input" in text:
            return self._too_often_handler(response)

        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        item["name"] = self.text_strip(response.xpath("//div[@class='headcont']//h1/text()").extract_first())

        text_join = self.text_join
        try:
            item["summary"] = text_join(response.xpath("//div[@class='hyinfo_detail_txt_files']"
                                                       "//text()").extract())

            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//li[@class='hyinfo_d_job_list_li']")))
            item["found_date"] = info_dict.get("成立日期")
            item["main_products"] = info_dict.get("主营产品")
            item["address"] = info_dict.get("公司注册地址")
            item["telephone"] = info_dict.get("电话") or info_dict.get("传真")
            item["mobile"] = info_dict.get("业务经理手机")
            item["registered_capital"] = info_dict.get("注册资金")
            item["employee_scale"] = info_dict.get("员工数量")
            item["legal_person"] = info_dict.get("法人")
            item["company_form"] = info_dict.get("公司类型")
        except Exception:
            self.logger.exception("")

        yield item

    def parse_shop(self, response):
        text = response.text
        if "过于频繁" in text or "<p>验证码:<input" in text:
            return self._too_often_handler(response)

        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join
        try:
            item["summary"] = text_join(response.xpath("//label[@id='ctl00_lab_com_Content']"
                                                       "//text()").extract())

            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[contains(@class,'com_files')]/ul/li")))

            item["name"] = self.text_strip(info_dict.get("公司简称")
                                           or response.xpath("//h1[@class='com_n']/text()[1]").extract_first(""))
            item["registered_capital"] = info_dict.get("注册资金")
            item["found_date"] = info_dict.get("建立时间")
            item["main_products"] = info_dict.get("主营产品")
            item["employee_scale"] = info_dict.get("员工人数")
            item["company_form"] = info_dict.get("经营模式")

            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//ul[@class='c_l_contact']/li"))
                             if "：" in info)

            item["address"] = info_dict.get("公司地址")
            item["telephone"] = info_dict.get("联系电话")
            item["mobile"] = info_dict.get("移动电话")
        except Exception:
            self.logger.exception("")

        yield item
