# -*- coding: utf-8 -*-

from datetime import date, timedelta
from io import BytesIO
from re import compile as re_compile, S as re_S
from time import sleep

from PIL import Image
from pytesseract import image_to_string
from requests import Session
from scrapy.http import Request, FormRequest

from crawler_bqjr.spiders.bank_spiders.base import BankSpider


class BocWapSpider(BankSpider):
    name = "bank_boc_wap"
    allowed_domains = ["mbs.boc.cn"]
    start_urls = ["https://mbs.boc.cn/BOCWapBank/LOGNWelcomeResult.do", ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_code_url = "https://mbs.boc.cn/BOCWapBank/ImageValidation/validation1386401611.gif"
        self.account_info_step1_url = "https://mbs.boc.cn/BOCWapBank/ACCTInfoList.do?_MenuId=mbsmenu.accountquery.balance"
        self.account_info_step2_url = "https://mbs.boc.cn/BOCWapBank/ACCTInfoResult.do"
        self.account_info_step3_url = "https://mbs.boc.cn/BOCWapBank/ACCTTradResult.do"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 4.4.4; MI 5 Build/KTU84P) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/33.0.0.0 Mobile Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://mbs.boc.cn",
            "Referer": "https://mbs.boc.cn/BOCWapBank/WEBSPortalMenuNew.do",
            "X-Requested-With": "com.android.browser",
        }
        self.pattern1 = re_compile(r'<div class="nav">.*?</div>(.*?)<br', re_S)
        self.pattern2 = re_compile(r'<span class="pl">(.*?)<br', re_S)
        self.date_delta = timedelta(days=180)

    def parse(self, response):
        meta = response.meta
        item = meta["item"]

        pattern1 = self.pattern1
        pattern2 = self.pattern2
        while True:
            try:
                sleep(1)
                self.logger.info("请求登录验证码接口->%s" % self.login_code_url)
                req_session = Session()
                pic_content = req_session.get(self.login_code_url, headers=self.headers, timeout=15,
                                              verify=False).content
                captcha_code = self.img2str(pic_content)
                self.logger.info("猜测的验证码是->%s" % captcha_code)
                if len(captcha_code) == 4:
                    self.logger.info("请求登录接口->%s" % response.url)
                    req_data = {
                        "LoginName": item["username"],
                        "Password": item["password"],
                        "ValidationChar": captcha_code,
                        "Submit": "登录手机银行",
                    }
                    text = req_session.post(response.url, headers=self.headers, data=req_data,
                                            timeout=15, verify=False).text
                    if "验证码" not in text:
                        self.logger.info("验证码正确")
                        # 验证码正确，再判断是否能访问登录的页面
                        if "请确认您的预留信息" in text:
                            self.logger.info("登录成功")
                            # 找不到登录的字样，说明已经成功登录，记录session。并让scrapy进行后续内容的抓取
                            # 字典格式方便scrapy进行爬取
                            cookies = req_session.cookies.get_dict()
                            # 请求账户信息接口
                            self.logger.info("请求账户信息接口->%s" % self.account_info_step1_url)
                            yield Request(
                                url=self.account_info_step1_url,
                                callback=self.parse_account_info_step1,
                                headers=self.headers,
                                cookies=cookies,
                                meta=meta,
                                dont_filter=True,
                                errback=self.err_callback
                            )
                        else:
                            msg1 = pattern1.search(text)
                            if msg1:
                                msg = msg1.group(1).strip()
                            else:
                                msg2 = pattern2.search(text)
                                if msg2:
                                    msg = msg2.group(1).strip()
                            self.logger.info("登录失败！->%s" % msg)
                            yield from self.error_handle(item["username"], msg, tell_msg=msg)
                            return
                        break
                    else:
                        self.logger.info("验证码不正确。")
            except Exception:
                self.logger.exception("爬虫解析入口异常")

    def parse_account_info_step1(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            accounts = response.xpath('//input[@name="AccountId"]')
            for account in accounts:
                account_no = account.xpath('@value').extract_first("")
                req_data = {
                    "AccountId": account_no,
                    "Submit": "确定"
                }
                # 请求特定账户接口
                self.logger.info("请求特定账户接口->%s" % self.account_info_step2_url)
                yield FormRequest(
                    url=self.account_info_step2_url,
                    callback=self.parse_account_info_step2,
                    formdata=req_data,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except Exception:
            yield from self.except_handle(item["username"], "中国银行---特定账户接口解析异常(第一步)")

    def parse_account_info_step2(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            CurTyp = "001"
            CashRemit = "20"
            now = date.today()
            StartDate = (now - self.date_delta).strftime('%Y%m%d')
            EndDate = now.strftime('%Y%m%d')
            req_data = {
                "CurTyp": CurTyp,
                "CashRemit": CashRemit,
                "StartDate": StartDate,
                "EndDate": EndDate,
                "Submit": "确定",
            }

            # 请求交易记录接口
            self.logger.info("请求交易记录接口->%s" % self.account_info_step3_url)
            yield FormRequest(
                url=self.account_info_step3_url,
                callback=self.parse_account_info_step3,
                formdata=req_data,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "中国银行---交易记录接口解析异常(第二步)")

    def parse_account_info_step3(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            trade_records = item["trade_records"]
            trade_list = response.xpath('//div[@class="lr"]|//div[@class="lt"]')
            for trade in trade_list:
                tmp_dict = {
                    "trade_date": trade.xpath('span[1]/text()').extract_first("").strip(),  # 交易日期
                    "trade_remark": trade.xpath('span[2]/text()').extract_first("").strip(),  # 交易概要
                    "trade_acceptor_name": trade.xpath('span[4]/text()').extract_first("").strip(),  # 对方账号名称
                    "trade_acceptor_account": trade.xpath('span[5]/text()').extract_first("").strip(),  # 对方账号号码
                    "trade_currency": trade.xpath('span[6]/text()').extract_first("").strip(),  # 币种
                    "trade_amount": trade.xpath('span[8]/text()').extract_first("").strip(),  # 金额
                    "trade_balance": trade.xpath('span[9]/text()').extract_first("").strip(),  # 余额，有bug（页面分为"支出金额"和"收入金额"）
                }
                trade_records.append(tmp_dict)
            url = response.xpath("//a[@class='help'][1]/@href").extract_first()
            url_text = response.xpath("//a[@class='help'][1]/text()").extract_first()
            if url and url_text == "下一页":
                url = response.urljoin(url)
                # 请求交易记录接口
                self.logger.info("请求交易记录接口->%s" % url)
                yield Request(
                    url=url,
                    callback=self.parse_account_info_step3,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            else:
                # 抓取完成
                yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"],
                                          "中国银行---交易记录接口解析异常(第三步)")

    def img2str(self, captcha_body):
        with BytesIO(captcha_body) as captcha_filelike, Image.open(captcha_filelike) as img:
            new_img = img.convert('L')  # 转换为RGBA

            # 二值化处理
            threshold = 127  # 阈值
            table = []
            for i in range(256):
                if i < threshold:
                    table.append(0)
                else:
                    table.append(1)

            new_img = new_img.point(table, '1')

            # 识别图片上的值（只识别数字）
            text = image_to_string(new_img, lang="eng", config="-psm 7 digits").replace(' ', '')
            new_img.close()

            return text
