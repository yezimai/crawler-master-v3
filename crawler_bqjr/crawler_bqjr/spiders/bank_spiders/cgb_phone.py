# -*- coding: utf-8 -*-

from datetime import date, timedelta
from re import compile as re_compile

from bs4 import BeautifulSoup as bs_format
from scrapy import FormRequest, Request

from crawler_bqjr.spider_class import PhantomJSWebdriverSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes, get_content_by_requests


class CgbWapSpider(PhantomJSWebdriverSpider, BankSpider):
    """
        广发银行WAP爬虫
    """
    name = "bank_cgb_wap"
    allowed_domains = ["wap.cgbchina.com.cn"]
    start_urls = ["https://wap.cgbchina.com.cn/default.jsp"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers = {
            "Host": "wap.cgbchina.com.cn",
            "User-Agent": "Mozilla/5.0 (Linux; U; Android 4.4.4; Nexus 5 Build/KTU84P) AppleWebkit/534.30 (KHTML, like Gecko) Version4.0 Mobile Safari/534.30",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.date_delta = timedelta(days=180)

        self.reg_balance_form = re_compile(r'action="([^"]+)"[\s\S]*?name="blanceform"')
        self.reg_account_form = re_compile(r'action="([^"]+)"[\s\S]*?name="queryform"')
        self.reg_group_recode = re_compile(r"<tr><td>\d+\.</td>([\s\S]+?>账户可用余额：\s*</td>\s*<td[^>]*?>[^<]+?</td></tr>)")
        self.reg_currency = re_compile(r">币种：</td>\s*<td>([^<]+)<")
        self.reg_income = re_compile(r">收入：</td>\s*<td>([^<]+)<")
        self.reg_outcome = re_compile(r">支出：</td>\s*<td[^>]*?>([^<]+)<")
        self.reg_channel = re_compile(r">交易渠道：</td>\s*<td>([\s\S]+?)<")
        self.reg_date = re_compile(r">交易日期： </td>\s*<td>([^<]+)<")
        self.reg_acceptor_account = re_compile(r">对方账号：</td>\s*<td>([^<]+)<")
        self.reg_acceptor_name = re_compile(r">对方户名：\s*</td>\s*<td>([^<]+)<")
        self.reg_remark = re_compile(r">交易说明：</td>\s*<td>([^<]+)<")
        self.reg_trade_balance = re_compile(r">账户可用余额：</td>\s*<td[^>]*?>([^<]+)<")
        self.reg_begin_date = re_compile(r'name="(beginTime[^"]+)"')
        self.reg_end_date = re_compile(r'name="(endTime[^"]+)"')

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        username = item['username']
        password = item['password']

        driver = self.load_page_by_webdriver(response.url)
        try:
            driver.implicitly_wait(1)
            driver.execute_script('document.getElementsByClassName("menu_item")[0].click();')
            driver.implicitly_wait(1)
            driver.execute_script('document.getElementsByName("logonId")[0].value="%s";'
                                  'document.getElementsByName("getSms")[0].click();'
                                  % username)
            page = str(bs_format(driver.page_source, "lxml"))
            if "短信已发送" in page:
                self.logger.info("--->短信已发送")
                sms_code = self.ask_sms_captcha(username)
                self.logger.info("短信验证码: %s" % sms_code)

                # 输入验证码
                validation_img = driver.find_element_by_xpath('.//*[@alt="checkCode"]')
                left = validation_img.location['x']
                top = validation_img.location['y']
                right = validation_img.location['x'] + validation_img.size['width']
                bottom = validation_img.location['y'] + validation_img.size['height']
                photo_base64 = driver.get_screenshot_as_base64()
                img_bytes = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                captcha_code = self.ask_image_captcha(img_bytes, username, file_type=".png")

                self.logger.info("图片验证码: %s" % captcha_code)
                driver.execute_script('document.getElementsByName("smsPassword")[0].value="%s";'
                                      'document.getElementsByName("password")[0].value="%s";'
                                      'document.getElementsByName("checkCode")[0].value="%s";'
                                      'document.getElementsByName("login")[0].click();'
                                      % (sms_code, password, captcha_code))
                driver.implicitly_wait(1)
                res_page = str(bs_format(driver.page_source, "lxml"))
                if "登录信息输入有误" in res_page:
                    yield from self.error_handle(username, msg="广发银行---登录信息输入有误",
                                                 tell_msg="银行流水数据爬取失败，请刷新页面重试!")
                elif "accmanage" in res_page:
                    self.logger.info("登录成功")
                    cookies = driver.get_cookies()
                    tran_his_url = "https://wap.cgbchina.com.cn/tranHistoryQueryInput.do?currentMenuId=101002"
                    yield Request(
                        tran_his_url,
                        callback=self.parse_balance_info,
                        meta=meta,
                        headers=self.headers,
                        cookies=cookies,
                        dont_filter=True,
                        errback=self.err_callback
                    )
                else:
                    yield from self.error_handle(username, msg="广发银行---未知错误",
                                                 tell_msg="银行流水数据爬取失败，请刷新页面重试!")

            else:
                yield from self.error_handle(username, msg="广发银行---短信发送失败",
                                             tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        except CaptchaTimeout:
            yield from self.error_handle(username, "广发银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, msg="广发银行---登录失败",
                                          tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        finally:
            driver.quit()

    def parse_balance_info(self, response):
        meta = response.meta
        username = meta['item']['username']

        try:
            query_page = str(bs_format(response.body, "lxml"))
            s_url = self.reg_account_form.search(query_page)
            if s_url:
                his_post_url = response.urljoin(s_url.group(1))
            else:
                yield from self.error_handle(username, msg="广发银行---获取交易明细失败",
                                             tell_msg="银行流水数据爬取失败，请刷新页面重试!")
                return

            now = date.today()
            start_date = (now - self.date_delta).strftime('%Y%m%d')
            end_date = now.strftime('%Y%m%d')
            begin_time_key = self.get_value_by_reg(self.reg_begin_date, query_page)
            end_time_key = self.get_value_by_reg(self.reg_end_date, query_page)
            his_query_data = {
                "actionsDefine": self.get_value_by_name(response, "actionsDefine"),
                "turnPageBeginPos": self.get_value_by_name(response, "turnPageBeginPos"),
                "turnPageShowNum": self.get_value_by_name(response, "turnPageShowNum"),
                "operationType": self.get_value_by_name(response, "operationType"),
                "jumpAction": self.get_value_by_name(response, "jumpAction"),
                "logFieldDefine": self.get_value_by_name(response, "logFieldDefine"),
                "enterBillFlag": self.get_value_by_name(response, "enterBillFlag"),
                "currency": self.get_value_by_name(response, "currency"),
                "firstFlag": self.get_value_by_name(response, "firstFlag"),
                "accountIdx": response.xpath('//select[@id="accountIdx"]/option[1]/@value').extract_first(""),
                "queryType": "3",
                begin_time_key: start_date,
                "beginDate": "",
                end_time_key: end_date,
                "endDate": end_date,
                "largeAcctFlag": "0",
                "next": "下一步"
            }
            yield FormRequest(
                url=his_post_url,
                callback=self.parse_tran_info,
                headers=self.headers,
                meta=meta,
                formdata=his_query_data,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(username, msg="广发银行---解析账户余额信息异常",
                                          tell_msg="银行流水数据爬取失败，请刷新页面重试!")

    def parse_tran_info(self, response):
        meta = response.meta
        item = meta["item"]

        try:
            response_text = str(bs_format(response.body, "lxml"))
            if "交易明细" in response_text:
                # 解析交易信息
                trade_records = item["trade_records"]
                for recode in self.reg_group_recode.findall(response_text):
                    trade_income, trade_outcome = ("", "")
                    trade_currency = self.get_value_by_reg(self.reg_currency, recode)
                    if "收入" in recode:
                        trade_income = self.get_value_by_reg(self.reg_income, recode)
                    elif "支出" in recode:
                        trade_outcome = self.get_value_by_reg(self.reg_outcome, recode)
                    trade_channel = self.get_value_by_reg(self.reg_channel, recode).strip()
                    trade_date = self.get_value_by_reg(self.reg_date, recode)
                    trade_acceptor_account = self.get_value_by_reg(self.reg_acceptor_account, recode)
                    trade_acceptor_name = self.get_value_by_reg(self.reg_acceptor_name, recode)
                    trade_remark = self.get_value_by_reg(self.reg_remark, recode)
                    trade_balance = self.get_value_by_reg(self.reg_trade_balance, recode)
                    tmp_dict = {
                        "trade_date": trade_date,
                        "trade_remark": trade_remark,
                        "trade_acceptor_name": trade_acceptor_name,
                        "trade_acceptor_account": trade_acceptor_account,
                        "trade_currency": trade_currency,
                        "trade_channel": trade_channel,
                        "trade_outcome": trade_outcome,
                        "trade_income": trade_income,
                        "trade_balance": trade_balance,
                        "trade_amount": trade_income or ("-" + trade_outcome),
                    }
                    trade_records.append(tmp_dict)
                url = response.xpath('//a[text()="下一页"]/@href').extract_first()
                if url:
                    # 请求交易明细接口
                    next_url = response.urljoin(url)
                    self.logger.info("请求交易明细接口->%s" % next_url)
                    yield Request(
                        url=next_url,
                        callback=self.parse_tran_info,
                        headers=self.headers,
                        meta=meta,
                        dont_filter=True,
                        errback=self.err_callback
                    )
                else:
                    item["balance"] = meta.get("balance", "")
                    # 抓取完成
                    yield from self.crawling_done(item)
            else:
                yield from self.error_handle(item['username'], msg="广发银行---查询交易明细失败",
                                             tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        except Exception:
            yield from self.except_handle(item['username'], "广发银行WAP获取账户交易明细异常")

    def get_form_data(self, response):
        """
        获取表单相关字段信息
        :param response:
        :return:
        """
        try:
            username = response.meta["item"]['username']
            return {"actionsDefine": self.get_value_by_name(response, "actionsDefine"),
                    "logonLanguage": self.get_value_by_name(response, "logonLanguage"),
                    "submitCtrlActions": self.get_value_by_name(response, "submitCtrlActions"),
                    "submitTimestamp": self.get_value_by_name(response, "submitTimestamp"),
                    "s": self.get_value_by_name(response, "s"),
                    "rtnType": self.get_value_by_name(response, "rtnType"),
                    "logonType": self.get_value_by_name(response, "logonType"),
                    "timer": self.get_value_by_name(response, "timer"),
                    "logonId": username,
                    }
        except Exception:
            self.logger.exception("获取表单字段异常:")
            return

    def get_value_by_name(self, response, name):
        """
        通过属性值获取input的value值
        :param response:
        :param name:
        :return:
        """
        try:
            pattern = '//input[@name="%s"]/@value' % name
            return response.xpath(pattern).extract_first("")
        except Exception:
            self.logger.exception("获取%s失败:" % name)
            return ""

    def download_pic(self, url):
        """
        下载验证码图片
        :param url:
        :return:
        """
        try:
            return get_content_by_requests(url, headers=self.headers)
        except Exception:
            self.logger.exception("下载验证码图片失败")
            return None

    def get_value_by_reg(self, reg_compile, text):
        """
        通过正则获取值
        :param reg_compile:
        :param text:
        :return:
        """
        try:
            res = reg_compile.search(text)
            return res.group(1).strip() if res else ""
        except Exception:
            self.logger.exception("匹配[%s]异常" % reg_compile)
            return ""
