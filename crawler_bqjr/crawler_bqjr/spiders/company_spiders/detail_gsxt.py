# -*- coding: utf-8 -*-

from re import compile as re_compile
from time import sleep

from bs4 import BeautifulSoup
from scrapy import Request
from scrapy.http import HtmlResponse
from selenium.webdriver.support import ui

from crawler_bqjr.captcha.geetest.hack import GeetestHack
from crawler_bqjr.items.company_items import CompanyGXSTDetailItem
from crawler_bqjr.settings import DO_NOTHING_URL
from crawler_bqjr.spiders.company_spiders.base import get_one_company
from crawler_bqjr.spiders.company_spiders.chrome_webdriver_spider import AbstractWebdriverSpider
from data_storage.db_settings import MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS
from data_storage.mongo_db import MongoDB
from data_storage.ssdb_db import get_ssdb_conn


class DetailGSXTSpider(AbstractWebdriverSpider):
    name = "gsxt"
    allowed_domains = ["gsxt.gov.cn"]
    start_urls = ["http://www.gsxt.gov.cn/index.html"]

    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 8,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pattern = re_compile(r"[a-zA-Z\d]+")

    def closed(self, reason):
        super().closed(reason)
        if hasattr(self, 'driver') and self.driver is not None:
            self.driver.quit()

    def __getwebdriver__(self):
        # self.driver = PhantomJSUtils.get_webdriver(self.settings)
        # self.wait = ui.WebDriverWait(self.driver, 20)
        # self.driver.start_session(webdriver.DesiredCapabilities.PHANTOMJS)
        # dcap = webdriver.DesiredCapabilities.CHROME
        # dcap["phantomjs.page.settings.userAgent"] = PhantomJSUtils.randomUA()
        if not hasattr(self, 'driver') or self.driver is None:
            # self.driver = chromedriver.WebDriver(
            #     executable_path="F:\\software\\pycharm\\workspace\\CrawlerHack\\browser\\chromedriver.exe",
            #     desired_capabilities=dcap)
            # self.driver = WebDriverProxy(self.settings,implicitly_wait=0,page_load_timeout=5,script_timeout=5).driver
            # dcap = webdriver.DesiredCapabilities.CHROME
            # dcap["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11"
            # self.driver.start_session(dcap)
            self.driver = self.spider.getdriver(executable_path=self.settings["PHANTOMJS_EXECUTABLE_PATH"],
                                                use_proxy=True)
        return self.driver

    def __getwait_20__(self):
        if not hasattr(self, 'wait_20'):
            self.wait_20 = ui.WebDriverWait(self.__getwebdriver__(), timeout=20)
        return self.wait_20

    def __getwait_10__(self):
        if not hasattr(self, 'wait_10'):
            self.wait_10 = ui.WebDriverWait(self.__getwebdriver__(), timeout=10)
        return self.wait_10

    def parse(self, response):
        ssdb_conn = get_ssdb_conn()
        mongo_instance = MongoDB(MONGO_COMPANY_DB, MONGO_COMPANY_COLLECTIONS)
        company = ""
        # time_start = time()
        while True:
            try:
                company = get_one_company(mongo_instance, ssdb_conn)
                if company is not None:
                    # DetailGSXTSpider.scrapy_count += 1
                    company_name = company["name"]
                    driver = self.__getwebdriver__()
                    self.driver = driver
                    self.logger.info("正在爬取公司：%s" % company_name)
                    self.wait_20 = self.__getwait_20__()
                    self.wait_10 = self.__getwait_10__()
                    driver.get(response.url)
                    # with open("webpage.html", "w",encoding='utf-8') as file:
                    #     file.write(driver.page_source)

                    self.wait_20.until(lambda d: d.find_element_by_xpath("//input[@id='keyword']").is_displayed())

                    # 关键词输入框
                    keyword_input = driver.find_element_by_id("keyword")
                    keyword_input.send_keys(company_name)

                    # 点击查询按钮
                    submit_btn = driver.find_element_by_id("btn_query")
                    submit_btn.click()

                    # 如果重试3次依然抛出TimeoutException则跳过此次查询
                    try_counts = 3
                    while True:
                        try:
                            self.wait_20.until(lambda d: d.find_element_by_xpath("//div[@class='gt_cut_bg gt_show']").is_displayed())
                            break
                        except Exception:
                            submit_btn.click()
                            try_counts -= 1
                            if try_counts == 0:
                                break
                    if try_counts == 0:
                        continue
                    hack = GeetestHack(driver, self.wait_10, self.logger)
                    is_successful = hack.drag_and_move_slider("//div[@class='gt_cut_bg gt_show']",
                                                              "//div[@class='gt_cut_fullbg gt_show']",
                                                              "//div[@class='gt_cut_bg gt_show']"
                                                              "/div[@class='gt_cut_bg_slice']",
                                                              "//div[@class='gt_cut_fullbg gt_show']"
                                                              "/div[@class='gt_cut_fullbg_slice']",
                                                              "//div[@class='gt_slider_knob gt_show']",
                                                              "//a[@class='search_list_item db']")
                    tries = 5
                    if not is_successful:
                        sleep(2)
                        try:
                            while True:
                                self.wait_20.until(
                                    lambda the_driver: the_driver.find_element_by_xpath(
                                        "//div[@class='gt_cut_bg gt_show']").is_displayed())
                                hack.drag_and_move_slider("//div[@class='gt_cut_bg gt_show']",
                                                          "//div[@class='gt_cut_fullbg gt_show']",
                                                          "//div[@class='gt_cut_bg gt_show']"
                                                          "/div[@class='gt_cut_bg_slice']",
                                                          "//div[@class='gt_cut_fullbg gt_show']"
                                                          "/div[@class='gt_cut_fullbg_slice']",
                                                          "//div[@class='gt_slider_knob gt_show']",
                                                          "//a[@class='search_list_item db']")
                                if tries == 0:
                                    break
                                tries -= 1
                                sleep(0.8)
                        except Exception as e:
                            self.logger.warning("爬取异常：{message:%s}" % str(e))
                    if tries == 0:
                        # 查询公司失败，继续查下一个公司
                        self.logger.debug("验证码破解失败，公司名：%s" % company_name)
                        continue
                    try:
                        # 查询公司成功，返回公司信息数据
                        company_list = driver.find_elements_by_xpath("//a[@class='search_list_item db']")
                        if company_list:
                            company_link = company_list[0].get_attribute("href")
                            driver.get(company_link)
                            self.wait_10.until(lambda d: d.find_element_by_xpath("//div[@id='primaryInfo']"
                                                                                 "/div[@class='details "
                                                                                 "clearfix']").is_displayed())

                            response = HtmlResponse(driver.current_url, encoding="utf-8", body=driver.page_source)
                            yield self.parse_search(company_name, response)
                    except Exception:
                        self.logger.info("爬取异常：国家企业信用信息公示系统没有%s的相关信息" % company_name)
                else:
                    yield Request(DO_NOTHING_URL, self.do_nothing,
                                  errback=self.do_nothing, dont_filter=True)
            except Exception as e:
                self.logger.warning("爬取异常：{company: %s,message:%s}" % (company, str(e)))
            finally:
                if hasattr(self, 'driver') and self.driver is not None:
                    self.driver.quit()
            # if DetailGSXTSpider.scrapy_count == 3:
            #     time_end = time()
            #     self.logger.debug("爬取10条数据共使用时间%s秒"%((time_end-time_start)))
            #     exit(0)

    def parse_search(self, company_name, response):
        try:
            html_text = response.text
            text_join = self.text_join
            info_dict = dict(info.split("：", maxsplit=1) for info
                             in (text_join(sel.xpath(".//text()").extract())
                                 for sel in response.xpath("//div[@class='overview']/dl")))

            item = CompanyGXSTDetailItem()
            item["from_web"] = self.name  # 来源网站
            item["from_url"] = "http://www.gsxt.gov.cn"  # 来源url
            item["name"] = (info_dict.get("企业名称") or info_dict.get("名称")
                            or self.text_strip(response.xpath("//h1[@class='fullName']"
                                                              "/text()").extract_first("")))  # 公司名称
            item["type"] = (info_dict.get("类型") or info_dict.get("企业类型") or info_dict.get("组成形式")
                            or info_dict.get("经济性质") or info_dict.get("经营性质"))  # 类型
            item["uniform_social_credit_code"] = info_dict.get("统一社会信用代码")  # 统一社会信用代码
            item["legal_person"] = (info_dict.get("法定代表人") or info_dict.get("执行事务合伙人")
                                    or info_dict.get("投资人") or info_dict.get("经营者")
                                    or info_dict.get("负责人") or info_dict.get("执行合伙人")
                                    or info_dict.get("母公司名称") or info_dict.get("隶属企业名称"))  # 企业法人
            item["found_date"] = info_dict.get("成立日期") or info_dict.get("集团成立日期")  # 成立日期
            item["check_date"] = info_dict.get("核准日期")  # 核准日期
            item["registered_capital"] = (info_dict.get("注册资本") or info_dict.get("认缴注册资本总额")
                                          or info_dict.get("注册资金") or info_dict.get("出资额")
                                          or info_dict.get("注册资本（金）总和（万元）"))  # 注册资本
            item["business_period"] = info_dict.get("营业期限至")  # 经营期限
            item["registered_address"] = (info_dict.get("住所") or info_dict.get("主要经营场所")
                                          or info_dict.get("营业场所") or info_dict.get("经营场所"))  # 注册地址
            item["licensed_business"] = info_dict.get("经营范围")  # 一般经营项目范围，许可经营项目范围
            item["status"] = info_dict.get("登记状态")  # 登记状态
            item["registered_authority"] = info_dict.get("登记状态")  # 登记机关
            item["search_url"] = response.url  # 查询url
            item["html"] = html_text  # 网页

            soup = BeautifulSoup(html_text, 'lxml')

            # 股东信息
            shareholder_info = []
            try:
                for shareholder_item in soup.find('table', attrs={"id": "shareholderInfo"}).tbody.find_all("tr"):
                    try:
                        item_info = [shareholder_item.contents[1].text.strip()]
                        shareholder_info.append(item_info)
                    except Exception:
                        pass
            except Exception:
                pass
            item["shareholder_info"] = shareholder_info

            # 主要成员
            member_info = []
            try:
                pattern = self.pattern
                for member_info_item in soup.find('div', attrs={"id": "personInfo"}).find_all("li"):
                    try:
                        member_info_txt = member_info_item.a.contents[0].text.strip()
                        old_str = pattern.search(member_info_txt)

                        member_info_txt = member_info_txt.replace(old_str.group(0), "")
                        item_info = [member_info_txt]
                        member_info.append(item_info)
                    except Exception:
                        pass
            except Exception:
                pass
            item["member_info"] = member_info
            return item
        except Exception as e:
            self.logger.warning("爬取异常：{url:%s, company: %s,message:%s}"
                                % (response.url, company_name, str(e)))
