# -*- coding: utf-8 -*-

from calendar import monthrange
from datetime import datetime, timedelta
from io import BytesIO
from string import digits, ascii_letters
from time import sleep

from PIL import Image
from piltesseract import get_text_from_image
from requests import Session
from scrapy.http import Request, FormRequest

from crawler_bqjr.spiders.shebao_spiders.base import ShebaoSpider
from crawler_bqjr.spiders_settings import SHEBAO_CITY_DICT


class ShebaoGuangzhouSpider(ShebaoSpider):
    name = SHEBAO_CITY_DICT["广州"]
    allowed_domains = ["gzlss.hrssgz.gov.cn"]
    start_urls = ["http://gzlss.hrssgz.gov.cn/gzlss_web/weixin/index.xhtml", ]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        "HTTPERROR_ALLOWED_CODES": [400, 401, 403, 404, 500, 501, 502, 503],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_url = "http://gzlss.hrssgz.gov.cn/gzlss_web/weixin/loginVerify.xhtml"  # 登录地址
        self.login_code_url = "http://gzlss.hrssgz.gov.cn/gzlss_web/validateCode/front.xhtml"
        self.personinfo_url = "http://gzlss.hrssgz.gov.cn/gzlss_web/weixin/teac/getZyjnjdQuery.xhtml"  # 个人基本信息
        self.ybk_url = "http://gzlss.hrssgz.gov.cn/gzlss_web/weixin/insb/toPersonYbkffView.xhtml"  # 医疗保险卡明细
        self.personpay_url = "http://gzlss.hrssgz.gov.cn/gzlss_web/weixin/fouc/getPersonalPayListSB.xhtml"  # 社保明细
        self.cookies = None
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1 wechatdevtools/0.7.0 MicroMessenger/6.3.9 Language/zh_CN webview/0",
        }
        self.captcha_char_whitelist = digits + ascii_letters

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        # TODO 这里while True的逻辑有问题
        while True:
            try:
                sleep(1)
                self.logger.info("请求登录验证码接口->%s" % self.login_code_url)
                req_session = Session()
                pic_content = req_session.get(self.login_code_url, headers=self.headers, timeout=15).content
                captcha_code = self.img2str(pic_content)
                self.logger.info("猜测的验证码是->%s" % captcha_code)
                if len(captcha_code) == 4:
                    self.logger.info("请求登录接口->%s" % self.login_url)
                    req_data = {
                        "idCard": item["username"],
                        "password": item["password"],
                        "validateCode": captcha_code,
                    }
                    text = req_session.post(self.login_url, headers=self.headers, data=req_data, timeout=15).text
                    if "验证码不正确" not in text:
                        self.logger.info("验证码正确")
                        # 验证码正确，再判断是否能访问登录的页面
                        self.logger.info("请求个人信息接口验证是否登录成功->%s" % self.personinfo_url)
                        sub_text = req_session.get(self.personinfo_url, headers=self.headers, timeout=15).text
                        if "<title>登录</title>" not in sub_text:
                            self.logger.info("登录成功")
                            # 找不到登录的字样，说明已经成功登录，记录session。并让scrapy进行后续内容的抓取
                            # 字典格式方便scrapy进行爬取
                            self.cookies = req_session.cookies.get_dict()
                            # 请求个人信息接口
                            self.logger.info("请求个人信息接口->%s" % self.personinfo_url)
                            yield Request(
                                url=self.personinfo_url,
                                callback=self.parse_personinfo,
                                headers=self.headers,
                                cookies=self.cookies,
                                meta=meta,
                                dont_filter=True,
                                errback=self.err_callback
                            )
                        else:
                            self.logger.info("账号或密码错误，请重试！")
                            msg = "账号或密码错误，请重试！"
                            yield from self.error_handle(item["username"], msg, tell_msg=msg)
                            return
                        break
                    else:
                        self.logger.info("验证码不正确")
            except Exception:
                self.logger.exception("爬虫解析入口异常：")

    def parse_personinfo(self, response):
        """
        个人信息解析
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            item["identification_number"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                                           '/tr[1]/td[2]/text()').extract_first("").strip()
            item["real_name"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                               '/tr[2]/td[2]/text()').extract_first("").strip()
            item["birthday"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                              '/tr[3]/td[2]/text()').extract_first("").strip()
            item["sex"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                         '/tr[4]/td[2]/text()').extract_first("").strip()

            # 请求医保卡信息
            self.logger.info("请求医保卡信息接口->%s" % self.ybk_url)
            yield Request(
                url=self.ybk_url,
                callback=self.parse_ybk,
                headers=self.headers,
                cookies=self.cookies,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州社保中心---个人信息解析异常")

    def parse_ybk(self, response):
        """
        医保卡信息解析
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        try:
            item["private_no"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                                '/tr[5]/td[2]/text()').extract_first("").strip()
            item["status"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                            '/tr[3]/td[2]/text()').extract_first("").strip()
            item["agency"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                            '/tr[7]/td[2]/text()').extract_first("").strip()
            item["date_of_recruitment"] = response.xpath('//div[@class="list_tab"]/table/tr[2]/td/table'
                                                         '/tr[2]/td[2]/text()').extract_first("").strip()

            # 请求社保明细信息，取最近6个月的社保明细
            month_list = []
            detail_list = []
            now = datetime.now()
            for i in range(1, 7):
                month_list.append(now.strftime("%Y%m"))
                now = now - timedelta(days=monthrange(now.year, now.month)[1])
            req_data = {
                "aae003": month_list.pop(),
            }
            meta["month_list"] = month_list
            meta["detail_list"] = detail_list

            yield FormRequest(
                url=self.personpay_url,
                callback=self.parse_personpay,
                headers=self.headers,
                cookies=self.cookies,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "广州社保中心---医保卡信息解析异常")

    def parse_personpay(self, response):
        """
        社保明细
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        month_list = meta["month_list"]
        detail_list = meta["detail_list"]
        try:
            insurance_detail = dict()
            insurance_detail["month"] = response.xpath('//*[@id="dateid"]/@value').extract_first("").strip()
            detail_selector = response.xpath('//div[@class="two"]/dl[not(@class="dl")]')
            detail_list_temp = []
            for detail in detail_selector:
                detail_list_dict = dict()
                detail_list_dict["stype"] = detail.xpath("dt[1]/text()").extract_first("").strip()  # 险种
                detail_list_dict["person_fee"] = detail.xpath("dd[1]/text()").extract_first("").strip()  # 个人缴费
                detail_list_dict["company_fee"] = detail.xpath("dd[2]/text()").extract_first("").strip()  # 单位缴费
                detail_list_temp.append(detail_list_dict)
            insurance_detail["detail"] = detail_list_temp
            detail_list.append(insurance_detail)

            if month_list:
                req_data = {
                    "aae003": month_list.pop(),
                }
                meta["month_list"] = month_list
                meta["detail_list"] = detail_list

                yield FormRequest(
                    url=self.personpay_url,
                    callback=self.parse_personpay,
                    headers=self.headers,
                    cookies=self.cookies,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                item["insurance_detail"] = detail_list

                # 抓取完成
                yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "广州社保中心---社保明细解析异常")

    def img2str(self, captcha_body):
        with BytesIO(captcha_body) as captcha_filelike, Image.open(captcha_filelike) as img:
            new_img = img.convert('L')  # 转换为RGBA
            pix = new_img.load()  # 转换为像素

            # 处理上下黑边框，size[0]即图片长度
            for x in range(new_img.size[0]):
                pix[x, 0] = pix[x, new_img.size[1] - 1] = 255

            # 处理左右黑边框，size[1]即图片高度
            for y in range(new_img.size[1]):
                pix[0, y] = pix[new_img.size[0] - 1, y] = 255

            # 二值化处理，这个阈值为140比较合适
            threshold = 140  # 阈值
            table = []
            for i in range(256):
                if i < threshold:
                    table.append(0)
                else:
                    table.append(1)

            new_img = new_img.point(table, '1')

            # 识别图片上的值
            text = get_text_from_image(new_img, psm=7,
                                       tessedit_char_whitelist=self.captcha_char_whitelist).replace(' ', '')
            new_img.close()

            return text
