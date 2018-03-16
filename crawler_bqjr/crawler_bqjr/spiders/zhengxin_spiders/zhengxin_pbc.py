# -*- coding: utf-8 -*-

from io import BytesIO
from itertools import islice
from re import compile as re_compile, S as re_S
from string import digits, ascii_letters

import cv2
import numpy
from PIL import Image
from piltesseract import get_text_from_image
from scrapy import FormRequest, Request

from crawler_bqjr.items.zhengxin_items import ZhengxinPbcItem
from crawler_bqjr.mail import send_mail_2_admin
from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.spiders_settings import ZHENANGXIN_DICT
from crawler_bqjr.utils import get_headers_from_response, get_cookiejar_from_response, \
    get_content_by_requests_post, get_js_time


class ZhengxinPbcSpider(AccountSpider):
    name = ZHENANGXIN_DICT['人行征信']
    allowed_domains = ["pbccrc.org.cn"]
    start_urls = ['https://ipcrs.pbccrc.org.cn/page/login/loginreg.jsp']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=ZhengxinPbcItem, **kwargs)
        self.login_url = self._start_url_
        self.captcha_char_whitelist = digits + ascii_letters
        self.space_pattern = re_compile(r"[\xa0\s]+")
        self.report_time_pattern = re_compile(r'<strong class="p">报告时间：\s*?([\d\.: ]+?)\s*?<')
        self.name_pattern = re_compile(r'<strong class="p">姓名：\s*?(\S+?)\s*?<')
        self.id_pattern = re_compile(r'<strong class="p">证件号码：\s*?([\d\*]+?)\s*?<')
        self.credit_card_info = re_compile(r'(\d{4}年\d+月\d+日)(\S+?银行\S*?)发放的(\S+?)（(\S+?)）')
        self.credit_card_quota = re_compile(r'截至(\d{4}年\d+月)\S*?信用额度(\S+?)，已使用额度([\d,]+)。(.*)$')
        self.credit_card_not_active = re_compile(r'截至(\d{4}年\d+月)\S*?信用额度(\S+?)\S*?未激活')
        self.credit_card_over = re_compile(r'截至(\d{4}年\d+月)(\S+?)。(.*)$')
        self.loan_info = re_compile(r'(\d{4}年\d+月\d+日)(\S+?)发放的([\d,]+)元（(\S+?)）(\S+?贷款)')
        self.loan_quota = re_compile(r'，(\d{4}年\d+月\d+日)到期\S*?截至(\d{4}年\d+月)\S*?余额([\d,]+)。(.*)$')
        self.loan_over = re_compile(r'，(\d{4}年\d+月)(\S+?)。(.*)$')
        self.chm_error = re_compile(r'<span class="erro_div1"  >(.*?)<', re_S)
        self.count = 0  # 计算密码输入错误次数

        self.headers = {
            'User-Agent': 'Mozilla / 5.0(Windows NT 6.1;Win64;x64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 60.0.3112.90Safari / 537.36',
        }

        self.credit_type_dict = {"其他贷款": "other_loan",
                                 "购房贷款": "house_loan",
                                 "信用卡": "credit_card",
                                 }
        self.credit_title_dict = {"账户数": "account_number",
                                  "未结清/未销户账户数": "active_number",
                                  "发生过逾期的账户数": "overdue_number",
                                  "发生过90天以上逾期的账户数": "overdue_90days_number",
                                  "为他人担保笔数": "guarantee_number",
                                  }
        self.inquiry_type_dict = {"机构查询记录明细": "institutional_inquiry",
                                  "个人查询记录明细": "personal_inquiry",
                                  }
        self.inquiry_title_dict = {"查询日期": "date",
                                   "查询操作员": "operator",
                                   "查询原因": "reason",
                                   }
        self.summary_title_dict = {"信贷记录": "credit_record",
                                   "公共记录": "public_record",
                                   "查询记录": "inquiry_record",
                                   }

    def _parse_credit_card_info(self, info):
        ret_data = {"raw_data": info}
        try:
            card_info = self.credit_card_info.search(info).groups()
            ret_data.update(dict(zip(["issuing_date", "issuer", "card_type", "account_type"], card_info)))
            if "已使用额度" in info:
                quota_info = self.credit_card_quota.search(info).groups()
                ret_data.update(dict(zip(["end_date", "credit_limit", "credit_used", "overdue_behavior"], quota_info)))
                ret_data["status"] = "激活"
            elif "未激活" in info:
                quota_info = self.credit_card_not_active.search(info).groups()
                ret_data.update(dict(zip(["end_date", "credit_limit"], quota_info)))
                ret_data["status"] = "未激活"
            else:
                status_info = self.credit_card_over.search(info).groups()
                ret_data.update(dict(zip(["end_date", "status", "overdue_behavior"], status_info)))
        except Exception:
            self.logger.exception("解析信用卡信息出错:")

        return ret_data

    def _parse_loan_info(self, info):
        ret_data = {"raw_data": info}
        try:
            loan_info = self.loan_info.search(info).groups()
            ret_data.update(dict(zip(["issuing_date", "issuer", "loan_amount",
                                      "account_type", "loan_type"], loan_info)))
            if "余额" in info:
                quota_info = self.loan_quota.search(info).groups()
                ret_data.update(dict(zip(["maturity_date", "end_date", "balance", "overdue_behavior"], quota_info)))
                ret_data["status"] = "未结清"
            else:
                status_info = self.loan_over.search(info).groups()
                ret_data.update(dict(zip(["end_date", "status", "overdue_behavior"], status_info)))
        except Exception:
            self.logger.exception("解析信用卡信息出错:")

        return ret_data

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        request.meta["item"]['code'] = account_info["code"]
        return request

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        password = item["password"]

        try:
            cookiejar = get_cookiejar_from_response(response)
            headers = get_headers_from_response(response)
            headers['Referer'] = response.url
            url = "https://ipcrs.pbccrc.org.cn/imgrc.do?" + get_js_time()
            captcha_body = get_content_by_requests_post(url, headers=headers, cookie_jar=cookiejar)
            captcha_code = self.parse_capatcha(captcha_body)
            self.logger.info("验证码识别结果：%s" % captcha_code)

            token = response.xpath("//input[@name='org.apache.struts.taglib.html.TOKEN']/@value").extract_first("")
            date = response.xpath("//input[@name='date']/@value").extract_first("")
            datas = {"org.apache.struts.taglib.html.TOKEN": token,
                     "method": "login",
                     "date": date,
                     "loginname": username,
                     "password": password,
                     "_@IMGRC@_": captcha_code
                     }

            yield FormRequest("https://ipcrs.pbccrc.org.cn/login.do", headers=self.headers,
                              formdata=datas, callback=self.parse_login, meta=meta, dont_filter=True)
        except Exception:
            yield from self.except_handle(username, msg="人行征信---登录入口解析失败",
                                          tell_msg="个人信息报告数据爬取失败，请刷新页面重试!")

    def parse_login(self, response):
        text = response.text
        meta = response.meta
        item = meta["item"]
        if "登录名或" in text:  # 密码错误
            yield from self.error_handle(item["username"], msg="征信---错误信息：账号密码错误",
                                         tell_msg="征信账号密码错误,请确认账号密码")
        elif "验证码输" in text:  # 验证码错误
            if self.count < 10:
                yield Request(self.login_url, self.parse, meta=meta, headers=self.headers,
                              dont_filter=True, errback=self.err_callback)
                self.count += 1
            else:
                yield from self.error_handle(item["username"], msg="征信---网络抓取异常：网络抓取异常,请刷新重试",
                                             tell_msg="网络抓取异常,请刷新重试")
        else:  # 登录成功
            url = 'https://ipcrs.pbccrc.org.cn/reportAction.do?method=applicationReport'  # 查询当前用户状态
            yield Request(url, headers=self.headers, callback=self.parse_user,
                          meta=meta, dont_filter=True, errback=self.err_callback)

    def parse_user(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            status = response.xpath('//font[@class="span-red span-12"]/text()').extract_first()
            if status:
                if '成功' in status or '已通过' in status:
                    datas = {"tradeCode": item["code"],
                             "reportformat": "21",
                             }
                    yield FormRequest("https://ipcrs.pbccrc.org.cn/simpleReport.do?method=viewReport",
                                      formdata=datas, callback=self.parse_report, meta=meta, dont_filter=True)
                elif '未通过' in status:
                    yield from self.error_handle(item['username'], msg='人行征信--错误信息',
                                                 tell_msg='你提交的问题信息未通过.<br/>可点击这里'
                                                          '<a href="/account_spider/zhengxin/user_login">'
                                                          '重新申请验证</a>')
                else:
                    yield from self.error_handle(item['username'], msg='人行征信--错误信息',
                                                 tell_msg='处理中,请等候人行24小时之内发送的验证码!<br/>点击这里'
                                                          '<a href="/account_spider/zhengxin">重新返回首页</a>')
            else:
                yield from self.error_handle(item['username'], msg='人行征信--错误信息',
                                             tell_msg='你还未申请验证身份识别码!<br/>点击这里'
                                                      '<a href="/account_spider/zhengxin/user_login">'
                                                      '申请验证</a>')
        except Exception:
            yield from self.except_handle(item['username'], msg="人行征信---错误信息",
                                          tell_msg="个人信息报告数据爬取失败，请刷新页面重试!")

    # 解析个人信息报告
    def parse_report(self, response):
        meta = response.meta
        text = response.text
        item = meta["item"]
        item['report_html'] = text

        try:
            error_cxm = self.chm_error.search(text)
            if error_cxm:
                yield item
                msg = error_cxm.group(1)
                yield from self.error_handle(item['username'], msg=msg, tell_msg=msg)
                return

            self.crawling_login(item["username"])  # 通知授权成功

            try:
                item["real_name"] = self.name_pattern.search(text).group(1)
                item["identification_number"] = self.id_pattern.search(text).group(1)
                item["report_time"] = self.report_time_pattern.search(text).group(1)
            except Exception:
                self.logger.error("姓名、身份证、报告时间解析失败: "
                                  "(username:%s, password:%s, code:%s)"
                                  % (item["username"], item["password"], item["code"]))

            space_pattern = self.space_pattern
            credit_type_dict = self.credit_type_dict
            report_detail_dict = {}
            xinxi = response.xpath('//table[@height="155"]/tbody/tr')
            if xinxi:
                account_detail_dict = {}
                credit_title_dict = self.credit_title_dict
                infos_list = [tr.xpath('td/text()').extract() for tr in islice(xinxi, 1, None)]
                for i, name in enumerate(islice(xinxi[0].xpath('td/text()').extract(), 1, None), 1):
                    title = name.strip()
                    account_detail_dict[credit_type_dict.get(title, "unknown")] \
                        = dict((credit_title_dict.get(space_pattern.sub('', info[0]), "unknown"),
                                info[i].strip()) for info in infos_list)

                report_detail_dict["credit_summary"] = account_detail_dict
            else:
                self.logger.error("无信息概要: (username:%s, password:%s, code:%s)"
                                  % (item["username"], item["password"], item["code"]))

            # 拆分信用卡详细,贷款账户详细
            other1 = response.xpath('//table[1]/tr[2]/td/span')
            other2 = response.xpath('//table[1]/tr[2]/td/ol[@class="p olstyle"]')
            for span, ul in zip(other1, other2):
                title = span.xpath('strong/text()').extract_first("").strip()
                key = credit_type_dict.get(title, "unknown")
                if "信用卡" == title:
                    report_detail_dict[key] = [self._parse_credit_card_info(j.strip())
                                               for j in ul.xpath('li/text()').extract()]
                elif "贷款" in title:
                    report_detail_dict[key] = [self._parse_loan_info(j.strip())
                                               for j in ul.xpath('li/text()').extract()]
                else:
                    report_detail_dict[key] = [j.strip() for j in ul.xpath('li/text()').extract()]

                if title not in credit_type_dict:
                    msg = "人行征信---未知详情: " + title
                    self.logger.critical(msg)
                    send_mail_2_admin("人行征信---未知详情", msg)

            # 公共记录
            public_record = response.xpath('//td[contains(text(),"公共记录")]'
                                           '/../../tr[2]//strong/text()').extract_first("")
            report_detail_dict["public_record"] = space_pattern.sub('', public_record)

            # 为他人担保预留字段
            report_detail_dict['guarantee_for_others'] = ''
            # 代偿人信息字段预留
            report_detail_dict['gompensatory'] = ''

            # 查询记录
            inquiry_type_dict = self.inquiry_type_dict
            for t in ["机构查询记录明细", "个人查询记录明细"]:
                institution_query_table = response.xpath('//strong[text()="' + t + '"]/../../..')
                titles = [self.inquiry_title_dict.get(i, "unknown") for i in
                          institution_query_table.xpath('tr[3]/td[position()>1]/strong/text()').extract()]
                report_detail_dict[inquiry_type_dict[t]] = [
                    dict(zip(titles, (i.strip() for i in tr.xpath('td[position()>1]/text()').extract())))
                    for tr in institution_query_table.xpath('tr[position()>3 and position()<last()]')
                ]

            item['detail'] = {'personal_info_report': report_detail_dict}

            datas = {"tradeCode": item["code"],
                     "reportformat": "24",
                     }
            yield FormRequest("https://ipcrs.pbccrc.org.cn/summaryReport.do?method=viewReport",
                              formdata=datas, callback=self.parse_summary, meta=meta, dont_filter=True)

            if "资产处置" in text:
                self.logger.exception("人行征信---发现资产处置: (username:%s, password:%s, code:%s)"
                                      % (item["username"], item["password"], item["code"]))
            if "包含您" in public_record:
                self.logger.exception("人行征信---发现公共记录: (username:%s, password:%s, code:%s)"
                                      % (item["username"], item["password"], item["code"]))
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="人行征信---错误信息",
                                          tell_msg="个人信息报告数据爬取失败，请刷新页面重试!")

    def parse_summary(self, response):
        meta = response.meta
        item = meta["item"]
        item['summary_html'] = response.text

        try:
            the_data = {}
            summary_title_dict = self.summary_title_dict
            for table in response.xpath('//table[@border=1]'):
                infos = table.xpath(".//td//text()").extract()
                the_data[summary_title_dict.get(infos[0], "unknown")] = "\n".join(i.strip() for i
                                                                                  in islice(infos, 1, None))
            item['detail']['personal_info_summary'] = the_data

            if not the_data:
                self.logger.error("无个人信息摘要: (username:%s, password:%s, code:%s)"
                                  % (item["username"], item["password"], item["code"]))

            datas = {"tradeCode": item["code"],
                     "reportformat": "25",
                     }
            yield FormRequest("https://ipcrs.pbccrc.org.cn/reportAction.do?method=viewReport",
                              formdata=datas, callback=self.parse_tips, meta=meta, dont_filter=True)
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="人行征信---错误信息",
                                          tell_msg="征信个人摘要数据爬取失败，请刷新页面重试!")

    def parse_tips(self, response):
        meta = response.meta
        item = meta["item"]
        item['tips_html'] = response.text

        try:
            the_data = "\n".join(i.strip() for i in response.xpath('//p[@class="span-grey3  p2"]/text()').extract())
            item['detail']['personal_info_tips'] = the_data

            if not the_data:
                self.logger.error("无个人信息提示: (username:%s, password:%s, code:%s)"
                                  % (item["username"], item["password"], item["code"]))

            # 页面抓取完成
            yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="人行征信---错误信息",
                                          tell_msg="个人信息提示数据爬取失败，请刷新页面重试!")

    def parse_capatcha(self, captcha_body):
        with BytesIO(captcha_body) as captcha_filelike, Image.open(captcha_filelike) as img:
            # img.show()

            # 构造算子为32位浮点三维矩阵kernel：[(1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
            #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
            #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
            #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)
            #                      (1 / 20, 1 / 20, 1 / 20, 1 / 20, 1 / 20)]
            # kernel = numpy.ones((5, 5), numpy.float32) / 19
            # sobelX = numpy.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
            # sobelY = numpy.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]])
            # kernel = numpy.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])

            # 做卷积去噪点
            eroded = numpy.array(img)
            eroded = cv2.fastNlMeansDenoisingColored(eroded)

            mask_img_arr = numpy.zeros((eroded.shape[0], eroded.shape[1]), numpy.uint8)
            dst_img = numpy.array(img)
            cv2.inpaint(eroded, mask_img_arr, 10, cv2.INPAINT_TELEA, dst=dst_img)

            # 图像灰度化处理
            eroded = cv2.cvtColor(eroded, cv2.COLOR_BGR2GRAY)

            # 图像二值化处理
            ret, eroded = cv2.threshold(eroded, 125, 255, cv2.THRESH_BINARY)

            dest_img = Image.fromarray(eroded)
            code = get_text_from_image(dest_img,
                                       tessedit_char_whitelist=self.captcha_char_whitelist).replace(' ', '')
            dest_img.close()

            return code
