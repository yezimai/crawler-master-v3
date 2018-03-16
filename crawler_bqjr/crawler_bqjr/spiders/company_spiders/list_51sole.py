# -*- coding: utf-8 -*-

from scrapy import Request

from crawler_bqjr.items.company_items import CompanyItem
from crawler_bqjr.spiders.company_spiders.base import CompanySpider


class List51SoleSpider(CompanySpider):
    name = "51sole"
    allowed_domains = ["51sole.com"]
    start_urls = ["http://www.51sole.com/shenzhen/"]

    custom_settings = {
        'DOWNLOAD_DELAY': 15,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def parse(self, response):
        parse_company_name = self.parse_company_name
        urljoin = response.urljoin

        sel_list = response.xpath("//div[@class='hy_include']/ul/li/a/@href").extract()
        if not sel_list:
            self.notice_change("No href found!!!!! " + response.url)

        for href in sel_list:
            url = urljoin(href)
            yield Request(url, callback=parse_company_name, dont_filter=True)

    def parse_company_name(self, response):
        name_exists_func = self.is_search_name_exists
        record_name_func = self.record_search_name
        parse_company = self.parse_company
        parse_company_contact = self.parse_company_contact
        text_strip = self.text_strip

        sel_list = response.xpath("//div[@class='hy_companylist']/ul/li/span[@class='fl']/a")
        if not sel_list:
            self.notice_change("No company_name found!!!!! " + response.url)

        for sel in sel_list:
            try:
                name = text_strip(sel.xpath("text()").extract_first())
            except Exception:
                continue
            if name_exists_func(name):
                continue
            record_name_func(name)

            url = sel.xpath("@href").extract_first("")
            if url.startswith("http://www.51sole.com/company/detail_"):
                yield Request(url, callback=parse_company)
            else:
                yield Request(url + "/companycontact.htm", callback=parse_company_contact)

        href = response.xpath("//div[@class='list-page']/ul/li"
                              "/a[text()='下一页']/@href").extract_first()
        if href:
            url = response.urljoin(href)
            yield Request(url, self.parse_company_name, dont_filter=True)

    def parse_company(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_strip = self.text_strip
        text_join = self.text_join

        item["name"] = response.xpath("//div[@class='profile-name']/h1/span/a/text()").extract_first()
        item["summary"] = text_join(response.xpath("//div[@class='article']/p/text()").extract(), "\n")

        info_dict = {}
        try:
            info_dict.update(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract()).replace("\xa0", "")
                                 for sel in response.xpath("//div[@class='contact-info']/ul/li/span")))
            item["address"] = info_dict.get("地址")
            item["telephone"] = info_dict.get("电话", "").strip("-")
            item["mobile"] = info_dict.get("移动电话", "").strip("-")
        except Exception:
            self.logger.exception("")

        sel_list = response.xpath("//div[@class='company-info']/table/tbody/tr")
        if not sel_list:
            self.notice_change("No data found!!!!! " + response.url)

        for sel in sel_list:
            info = [i for i in sel.xpath("td//text()").extract() if text_strip(i)]
            if info:
                try:
                    info_dict[info[0]] = info[1]
                except Exception:
                    pass

        item["name"] = info_dict.get("公司名称") or item["name"]
        item["found_date"] = info_dict.get("注册时间")
        item["registered_capital"] = info_dict.get("注册资本")
        item["employee_scale"] = info_dict.get("公司规模")
        item["legal_person"] = info_dict.get("法定代表人")
        item["main_area"] = info_dict.get("年营业额")
        item["main_products"] = info_dict.get("主营产品")
        item["company_form"] = info_dict.get("企业类型")
        item["address"] = info_dict.get("详细地址") or item.get("address")

        yield item

    def parse_company_contact(self, response):
        item = CompanyItem()
        item["from_web"] = self.name
        item["from_url"] = response.url
        item["area"] = "shenzhen"

        text_join = self.text_join

        item["name"] = response.xpath("//div[@id='namelogo']/p/text()").extract_first()

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract()).replace("\xa0", "")
                                 for sel in response.xpath("//div[@id='contact']/ul/li")))
            item["name"] = info_dict.get("公司") or item["name"]
            item["address"] = info_dict.get("地址")
            item["telephone"] = info_dict.get("电话", "").strip("-") or info_dict.get("传真", "").strip("-")
            item["mobile"] = info_dict.get("手机")
        except Exception:
            self.logger.exception("")

        request = Request(response.url.replace("/companycontact.htm", "/companyabout.htm"),
                          self.parse_company_introduce)
        request.meta["item"] = item
        yield request

    def parse_company_introduce(self, response):
        meta = response.meta
        item = meta["item"]
        item["summary"] = self.text_join(response.xpath("//div[@class='companyintro']/p/text()").extract(),
                                         "\n")

        text_join = self.text_join

        try:
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract()).replace("\xa0", "")
                                 for sel in response.xpath("//div[@id='companyinfo']/ul/li")))
            item["name"] = info_dict.get("公司名称") or item["name"]
            item["company_form"] = info_dict.get("企业类型")
            item["legal_person"] = info_dict.get("法人代表")
            item["found_date"] = info_dict.get("公司成立时间")
            item["main_products"] = info_dict.get("主营产品或服务")
        except Exception:
            self.logger.exception("")

        yield item
