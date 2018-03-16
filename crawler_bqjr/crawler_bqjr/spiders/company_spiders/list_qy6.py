# -*- coding: utf-8 -*-

from itertools import islice
from re import compile as re_compile
from urllib.parse import parse_qs

from scrapy import FormRequest, Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class ListQy6Spider(CompanySpider):
    name = "qy6"
    allowed_domains = ["qy6.com"]
    start_urls = ["http://www.qy6.com/qyml/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 600,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_pattern = re_compile(r"/qyml/qy(\w+)\.html")

    def parse(self, response):
        type_pattern = self.type_pattern
        parse_company_name = self.parse_company_name

        sel_list = response.xpath("//a[starts-with(@href,'/qyml/qyC')]/@href").extract()
        if not sel_list:
            self.notice_change("No href found!!!!! " + response.url)

        for url in islice(sel_list, 0, 1):
            the_type = type_pattern.search(url).group(1)
            form_data = {"province": "CN05",
                         "capital": "CN0515",
                         "comp_kindsel": the_type,
                         "page_size": "100",
                         "ordertype": "2",
                         }
            yield FormRequest("http://www.qy6.com/qyml/glist.php?cat=" + the_type,
                              parse_company_name, dont_filter=True, formdata=form_data)

    def parse_company_name(self, response):
        urljoin = response.urljoin
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        text_strip = self.text_strip

        sel_list = response.xpath("//td[@class='f3']/a[1]")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("strong/text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            url = urljoin(url)

            item = CompanyItem()
            item["from_web"] = self.name
            item["area"] = "shenzhen"
            item["name"] = name

            request = Request(url, callback=parse_company)
            request.meta["item"] = item
            yield request

        url = response.xpath("//a[text()='下一页']/@href").extract_first()
        if url:
            form_data = parse_qs(response.request.body.decode())
            form_data = {k: v[0] for k, v in form_data.items()}
            form_data["page_change"] = "100"
            form_data["page_num"] = str(int(form_data.get("page_num", 1)) + 1)
            yield FormRequest(response.url, self.parse_company_name, dont_filter=True, formdata=form_data)

    def _get_data_from_info_table(self, response, item):
        text_join = self.text_join

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//table[@cellspacing='2']/tbody/tr/td")))
            item["main_products"] = info_dict.get("主营产品或服务")
            item["employee_scale"] = info_dict.get("员工人数")
            item["main_area"] = info_dict.get("主营市场")
            item["industry"] = info_dict.get("主营行业")
            item["annual_turnover"] = info_dict.get("年营业额")
            item["legal_person"] = info_dict.get("法人代表/负责人")
            item["found_date"] = info_dict.get("成立时间")
            item["registered_capital"] = info_dict.get("注册资金")
            item["company_form"] = info_dict.get("企业经济性质", "").rstrip(';')
        except Exception:
            self.logger.exception("")

    def _get_data_from_contact_table(self, response, item):
        text_join = self.text_join

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//td[@background='http://img.qy6.com/images/card.gif']"
                                                           "/table/tbody/tr"))
                             if "：" in info)
            item["telephone"] = info_dict.get("电　　话") or info_dict.get("传　　真")
            item["mobile"] = info_dict.get("移动电话")
            item["address"] = info_dict.get("公司地址")
        except Exception:
            self.logger.exception("")

    def _parse_old_company(self, response):
        item = response.meta["item"]
        item["from_url"] = response.url

        item["summary"] = self.text_join(response.xpath("//td[@style='word-break:break-all']"
                                                        "//text()").extract())

        self._get_data_from_info_table(response, item)
        self._get_data_from_contact_table(response, item)

        yield item

    def _parse_new_company_about(self, response):
        meta = response.meta
        item = meta["item"]
        item["from_url"] = response.url

        item["summary"] = self.text_join(response.xpath("(//td[@class='bady'])[1]//text()").extract())

        self._get_data_from_info_table(response, item)

        url = response.url.replace("http://www.qy6.com/qyml/about", "http://www.qy6.com/qyml/con")
        yield Request(url, callback=self._parse_new_company_contact, meta=meta)

    def _parse_new_company_contact(self, response):
        item = response.meta["item"]
        self._get_data_from_contact_table(response, item)
        yield item

    def parse_company(self, response):
        if response.xpath("//td[@class='logo']"):
            url = response.url.replace("http://www.qy6.com/qyml/comp", "http://www.qy6.com/qyml/about")
            yield Request(url, callback=self._parse_new_company_about, meta=response.meta)
        else:
            yield from self._parse_old_company(response)
