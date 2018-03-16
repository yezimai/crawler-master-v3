# coding : utf-8

from random import random
from re import compile as re_compile
from urllib.parse import unquote, quote

from requests import get as http_get
from scrapy import Selector
from scrapy.http import Request, FormRequest

from crawler_bqjr.spiders.emailbill_spiders.base import EmailSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import CREDIT_CARD_KEYWORD, \
    check_email_credit_card_by_address
from crawler_bqjr.spiders_settings import EMAIL_DICT
from crawler_bqjr.utils import get_js_time, get_response_by_requests, get_headers_from_response
from global_utils import json_loads


class EmailqqSpider(EmailSpider):
    name = EMAIL_DICT['qq.com']
    start_urls = ['https://mail.qq.com/', ]
    custom_settings = {
        'REDIRECT_ENABLED': False,
        'HTTPERROR_ALLOWED_CODES': [302],
        'DOWNLOAD_DELAY': 0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PAGE_PER_COUNT = 25
        self.headers = {
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.8',
        }
        self.search_url = 'https://mail.qq.com/cgi-bin/mail_list?s=search&searchmode=advance' \
                          '&topmails=0&advancesearch=2&flagnew=&attach=&position=2&folderid=all' \
                          '&daterange=&resp_charset=UTF8&sid={0}&page={1}&subject={2}&sender=&receiver='
        self.keyword = quote(CREDIT_CARD_KEYWORD.encode('gbk'))
        self.detail_url = 'https://mail.qq.com/cgi-bin/readmail?folderid=1&folderkey=&t=readmail' \
                          '&mailid={mailid}&mode=pre&maxage=3600&base=12.34&ver=19591&sid={sid}'
        self.appid_pattern = re_compile(r"appid=(\d+)&")
        self.daid_pattern = re_compile(r"daid=(\d+)&")
        self.qr_result_list_pattern = re_compile(r"ptuiCB\((.*)\)")
        self.qr_result_info_pattern = re_compile(r"'(.*)'")
        self.login_url_pattern = re_compile(r'(https://mail\.qq\.com/cgi-bin/login.*?)"')
        self.sid_pattern = re_compile(r'sid=(\S{16})&')
        self.page_num_pattern = re_compile(r'document.write\(([\-\d]+) \+ 1\);')

    def __hash_33(self, t):
        e = 0
        for char in t:
            e += (e << 5) + ord(char)
        return 2147483647 & e

    def __get_qr(self):
        index_url = 'https://mail.qq.com/cgi-bin/loginpage'
        index_r = get_response_by_requests(index_url, self.headers)
        index_text = index_r.text
        iframe_url = Selector(text=index_text).xpath("//iframe/@src").extract_first("")
        iframe_r = get_response_by_requests(iframe_url, self.headers)
        cookies = iframe_r.cookies.get_dict()
        appid = self.appid_pattern.search(iframe_url).group(1)
        daid = self.daid_pattern.search(iframe_url).group(1)
        qr_url = "https://ssl.ptlogin2.qq.com/ptqrshow?" \
                 "appid={0}&e=2&l=M&s=3&d=72&v=4&t={1}&" \
                 "daid={2}&pt_3rd_aid=0".format(appid, random(), daid)

        qr = http_get(qr_url, self.headers, cookies=cookies)
        cookies.update(qr.cookies.get_dict())
        return qr.content, cookies, appid, daid

    def scan_qr_status(self, response):
        try:
            qr_result_list = self.qr_result_list_pattern.search(response.text).group(1).split(',')
            qr_result_code = self.qr_result_info_pattern.search(qr_result_list[0]).group(1)
            qr_result_status = self.qr_result_info_pattern.search(qr_result_list[4]).group(1)
            if int(qr_result_code) == 0 and '成功' in qr_result_status:
                # 登录成功 发ssdb
                qr_result_url = self.qr_result_info_pattern.search(qr_result_list[2]).group(1)
                # qr_result_nick_name = self.qr_result_info_pattern.search(qr_result_list[5]).group(1)
                yield Request(qr_result_url, callback=self.check_sig, meta=response.meta,
                              dont_filter=True, errback=self.err_callback)
            else:
                yield self.crawling_failed(response.meta['item']['username'], '二维码过期，请重试')
        except Exception:
            yield from self.except_handle(response.meta['item']['username'], '二维码过期解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def check_sig(self, response):
        try:
            location_url = response.headers.get('Location')
            yield Request(location_url.decode(), callback=self.read_template, meta=response.meta,
                          dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(response.meta['item']['username'], '签名解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def read_template(self, response):
        try:
            login_url = self.login_url_pattern.search(response.text).group(1)
            yield Request(login_url, callback=self.get_login, meta=response.meta,
                          dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(response.meta['item']['username'], 'template解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def get_login(self, response):
        try:
            location_url = response.headers.get('Location').decode()
            if "cgi-bin/frame_html" in location_url:
                yield Request(location_url, callback=self.login_succ, meta=response.meta,
                              dont_filter=True, errback=self.err_callback)
            elif "cgi-bin/loginpage" in location_url:
                yield Request(location_url, callback=self.post_login, meta=response.meta,
                              dont_filter=True, errback=self.err_callback)
            else:
                self.logger.error("出现未知跳转情况\nlocation_url --> {0}\n response -->  "
                                  "{1}".format(location_url, response.text))
                yield from self.crawling_failed(response.meta['item']["username"], "独立密码错误")
        except Exception:
            yield from self.except_handle(response.meta['item']['username'], '登录解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def post_login(self, response):
        meta = response.meta
        try:
            pp = self.ask_extra_captcha(meta['item']['username'])
            data = {
                'org_errtype': '6',
                'tfcont': '',
                'delegate_url': '',
                'f': 'html',
                'starttime': '',
                'chg': '0',
                'ept': '0',
                'ppp': '',
                'ts': get_js_time(),
                'vt': 'secondpwd',
                'clientaddr': '',
                'ignore_me': 'ignore_me',
                'pp': pp,  # 独立密码
                'p': pp,
                'btlogin': unquote('%204%20%B5%C7%C2%BC')
            }
            yield FormRequest('https://mail.qq.com/cgi-bin/login?sid=,2,zh_CN', callback=self.login,
                              formdata=data, meta=meta, dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta['item']['username'], '登录解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def login(self, response):
        try:
            location_url = response.headers.get('Location')
            yield Request(location_url.decode(), callback=self.check_dulimima, meta=response.meta,
                          dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(response.meta['item']['username'], '登录解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def check_dulimima(self, response):
        meta = response.meta
        try:
            if response.xpath('//div[@id="msgContainer"]/text()').extract_first():
                meta['retry_time'] += 1
                if meta['retry_time'] <= 2:
                    yield from self.post_login(response)
                else:
                    yield from self.crawling_failed(meta['item']["username"], "独立密码错误")
            else:
                yield from self.login_succ(response)
        except Exception:
            yield from self.except_handle(meta['item']['username'], 'check_dulimima解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def login_succ(self, response):
        meta = response.meta
        try:
            self.crawling_login(username=meta["item"]["username"])

            # 搜索列表
            sid = self.sid_pattern.search(response.text).group(1)
            search_url = self.search_url.format(sid, 0, self.keyword)
            meta['sid'] = sid
            yield Request(search_url,
                          meta=meta,
                          dont_filter=True,
                          callback=self.parse_search,
                          errback=self.err_callback
                          )
        except Exception:
            yield from self.except_handle(meta['item']['username'], 'check_dulimima解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def qr_login(self, response):
        meta = response.meta
        try:
            meta['retry_time'] = 0
            qr_cotent, cookies, appid, daid = self.__get_qr()
            status = self.ask_scan_qrcode(qr_cotent, meta['item']['username'])
            if status != "ok":
                self.logger.error("扫描二维码登录失败")
                yield from self.crawling_failed(meta['item']["username"], "扫描二维码登录失败")
                return

            ptqrtoken = self.__hash_33(cookies.get('qrsig'))
            scan_url = "https://ssl.ptlogin2.qq.com/ptqrlogin?u1=https%3A%2F%2Fmail.qq.com%2Fcgi-bin" \
                       "%2Freadtemplate%3Fcheck%3Dfalse%26t%3Dloginpage_new_jump%26vt%3Dpassport%26vm" \
                       "%3Dwpt%26ft%3Dloginpage%26target%3D&ptqrtoken={0}&ptredirect=0&h=1&t=1&g=1" \
                       "&from_ui=1&ptlang=2052&action=1-1-1513651703600&js_ver=10232&js_type=1&login_s" \
                       "ig=&pt_uistyle=25&aid={1}&daid={2}&".format(ptqrtoken, appid, daid)
            yield Request(scan_url,
                          callback=self.scan_qr_status,
                          meta=meta,
                          cookies=cookies,
                          dont_filter=True,
                          errback=self.err_callback
                          )
        except Exception:
            yield from self.except_handle(meta['item']['username'], 'qr_login解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        try:
            info = item['password'].split("|", 1)
            item['password'] = ''
            qr_result_url = info[0]
            cookies = json_loads(info[1])
            meta['retry_time'] = 0
            yield Request(qr_result_url, callback=self.check_sig, meta=meta, cookies=cookies,
                          dont_filter=True, errback=self.err_callback)
            # yield from self.qr_login(response)
        except Exception:
            yield from self.except_handle(item['username'], '登录入口解析失败',
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def parse_search(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            sid = meta['sid']
            mail_list = meta.setdefault('mail_list', [])
            detail_url = self.detail_url
            for email_table in response.xpath('//div[@class="toarea"]/table'):
                address = email_table.xpath(".//span[@e]/@e").extract_first()
                subject = email_table.xpath('.//td[contains(@class,"gt")]'
                                            '/div/u/text()').extract_first("").strip()
                bankname = check_email_credit_card_by_address(subject, address)
                if bankname:
                    mail_id = email_table.xpath('.//td/nobr/@mailid').extract_first()
                    tmp_detail_url = detail_url.format(mailid=mail_id, sid=sid)
                    mail_list.append((tmp_detail_url, bankname, subject))

            page_num = meta.get('page_num')
            if page_num is None:
                nextpage_script = response.xpath('//div[@class="right"]/script/text()').extract_first("")
                page_num = self.page_num_pattern.search(nextpage_script)
                if page_num:
                    page_num = int(page_num.group(1))
                else:
                    page_num = int(self.page_num_pattern.search(response.text).group(1))
                meta["page_num"] = page_num

            next_page = meta.get('current_page', 0) + 1
            if page_num >= next_page:
                meta["current_page"] = next_page
                search_url = self.search_url.format(sid, next_page, self.keyword)
                yield Request(search_url,
                              meta=meta,
                              dont_filter=True,
                              callback=self.parse_search,
                              errback=self.err_callback
                              )
            else:
                if not mail_list:
                    yield from self.crawling_done(item)
                    return

                headers = get_headers_from_response(response)
                parse_detail = self.parse_detail
                err_callback = self.err_callback
                count = len(mail_list)
                for url, bankname, subject in mail_list:
                    yield Request(url,
                                  headers=headers,
                                  dont_filter=True,
                                  callback=parse_detail,
                                  errback=err_callback,
                                  meta={'bankname': bankname,
                                        'item': item,
                                        'subject': subject,
                                        'count': count
                                        }
                                  )
        except Exception:
            yield item
            yield from self.except_handle(response.meta['username'], msg="查找账单异常",
                                          tell_msg="查找账单异常")

    def parse_detail(self, response):
        meta = response.meta
        item = meta['item']
        try:
            content_html = response.xpath('//div[@id="mailContentContainer"]').extract_first("")
            bill_record = self.get_bill_record(meta['bankname'], meta['subject'], content_html)
            bill_records = item['bill_records']
            bill_records.append(bill_record)
            if len(bill_records) == meta['count']:
                yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="账单解析异常", tell_msg="账单解析异常")
