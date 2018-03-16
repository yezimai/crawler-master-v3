# -*- coding:utf-8 -*-

from base64 import b64encode
from email.utils import parseaddr
from random import random
from re import compile as re_compile
from urllib.parse import quote

from scrapy.http import Request, FormRequest, Response

from crawler_bqjr.spiders.emailbill_spiders.base import EmailSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import CREDIT_CARD_KEYWORD, \
    check_email_credit_card_by_address
from crawler_bqjr.spiders_settings import EMAIL_DICT
from crawler_bqjr.tools.rsa_tool import RsaUtil
from crawler_bqjr.utils import get_content_by_requests, get_headers_from_response, get_js_time
from global_utils import json_loads


class EmailSinaSpider(EmailSpider):
    name = EMAIL_DICT['sina.com']
    start_urls = ['http://mail.sina.com.cn/', ]
    allowed_domains = ['sina.com', 'sina.cn', 'sina.com.cn']
    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'HTTPERROR_ALLOWED_CODES': [301, 302],
        'REDIRECT_ENABLED': False
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_pattern = re_compile(r'CallBack\((.*?)\)')
        self.sla_url_pattern = re_compile(r'replace\("(.*?)"\)')
        self.six_month_time = int(6 * 30 * 24 * 60 * 60 * 1E3)

    def parse(self, response):
        meta = response.meta
        try:
            su = self._enb64(self._url_encode(meta['item']["username"])).decode()
            prelogin_url = "https://login.sina.com.cn/sso/prelogin.php?entry=cnmail" \
                           "&callback=sinaSSOController.preloginCallBack&su=%s&rsakt=mod" \
                           "&client=ssologin.js(v1.4.19)&_=%s" % (su, get_js_time())
            yield Request(prelogin_url, callback=self.prelogin, meta=meta,
                          dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta['item']["username"], msg="登录入口解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试")

    def prelogin(self, response):
        meta = response.meta
        try:
            su = self._enb64(self._url_encode(meta['item']["username"])).decode()
            step1_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=sso' \
                        '&callback=sinaSSOController.preloginCallBack&' \
                        'su=%s&rsakt=mod&client=ssologin.js(v1.4.19)' % su
            yield Request(step1_url, callback=self.step1, meta=meta,
                          dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta['item']["username"], msg="预登录解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试")

    def step1(self, response):
        meta = response.meta
        item = meta['item']
        try:
            captecha_code = dict()
            try:
                captecha_code = meta['captecha_code']
            except Exception:
                pass

            login_url = 'https://login.sina.com.cn/sso/login.php' \
                        '?client=ssologin.js(v1.4.19)&_=%s' % get_js_time()
            su = self._enb64(self._url_encode(item["username"])).decode()

            response_js = json_loads(self.callback_pattern.search(response.text).group(1))
            servertime = response_js.get('servertime', '')
            pcid = response_js.get('pcid', '')
            nonce = response_js.get('nonce', '')
            pubkey = response_js.get('pubkey', '')
            rsakv = response_js.get('rsakv', '')
            # retcode = response_js.get('retcode', '')
            # uid = response_js.get('uid', '')
            # exectime = response_js.get('exectime', '')

            my_rsa = RsaUtil(key_is_hex=True)
            msg = str(servertime) + '\t' + str(nonce) + '\n' + str(item["password"])
            password = my_rsa.encrypt(msg, pubkey=pubkey, get_hex=True)
            post_data = {
                'entry': 'freemail',
                'gateway': '1',
                'from': '',
                'savestate': str(response_js.get("savestate")) or '0',
                'qrcode_flag': 'false',
                'useticket': '0',
                'pagerefer': '',
                'su': su,
                'service': 'sso',
                'servertime': str(servertime),
                'nonce': nonce,
                'pwencode': 'rsa2',
                'rsakv': rsakv,
                'sp': password,
                'sr': '1366*768',
                'encoding': 'UTF-8',
                'cdult': '3',
                'domain': 'sina.com.cn',
                'prelt': '213',
                'returntype': 'TEXT',
            }
            if captecha_code:
                post_data.update(captecha_code)

            meta["pcid"] = pcid
            meta["captcha_url"] = 'https://login.sina.com.cn/cgi/pin.php' \
                                  '?r=%s&s=0&p=%s' % (int(random() * 1E8), pcid)
            yield FormRequest(url=login_url,
                              formdata=post_data,
                              callback=self.user_login,
                              meta=meta,
                              dont_filter=True,
                              errback=self.err_callback
                              )
        except Exception:
            yield from self.except_handle(item["username"], msg="登录第一步解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试")

    def user_login(self, response):
        meta = response.meta
        item = meta['item']
        username = item['username']
        try:
            login_js = json_loads(response.text)
            retcode = login_js['retcode']
            if retcode == '4049':
                # 发送验证码
                headers = get_headers_from_response(response)
                captcha_url = meta['captcha_url']
                self.set_image_captcha_headers_to_ssdb(headers, username)  # 将头信息传递给 django
                self.set_email_img_url_to_ssdb(captcha_url, username)

                captcha_body = get_content_by_requests(captcha_url, headers=headers)
                captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".png")
                meta["captecha_code"] = {'door': captcha_code, 'pcid': meta['pcid']}

                # 异地登录 需要验证码验证
                su = self._enb64(self._url_encode(username)).decode()
                step1_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=sso' \
                            '&callback=sinaSSOController.preloginCallBack' \
                            '&su=%s&rsakt=mod&client=ssologin.js(v1.4.19)' % su
                yield Request(url=step1_url,
                              callback=self.step1,
                              meta=meta,
                              dont_filter=True,
                              errback=self.err_callback
                              )
            elif retcode in ['101', '2070', '2079']:
                err_message = '登录名或密码错误!'
                yield from self.error_handle(username,
                                             msg="sina---登录失败：(username:%s, password:%s) %s"
                                                 % (username, item['password'], err_message),
                                             tell_msg=err_message)
            else:
                meta["cross"] = login_js['crossDomainUrlList'][0]
                yield Request(url=login_js['crossDomainUrlList'][1],
                              callback=self.cross_domain_one,
                              meta=meta,
                              dont_filter=True,
                              errback=self.err_callback
                              )
        except Exception:
            yield from self.except_handle(username, msg="用户登录解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试",
                                          logout_request=self.get_logout_request(meta))

    def cross_domain_one(self, response):
        meta = response.meta
        try:
            yield Request(url=meta['cross'],
                          callback=self.user_login_two,
                          meta=meta,
                          dont_filter=True,
                          errback=self.err_callback
                          )
        except Exception:
            yield from self.except_handle(meta['item']["username"], msg="cross_domain_one解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试",
                                          logout_request=self.get_logout_request(meta))

    def user_login_two(self, response):
        meta = response.meta
        try:
            login_url = 'http://mail.sina.com.cn/cgi-bin/sla.php?a={0}&b={1}&c=0' \
                        '&ssl=1'.format(get_js_time(), get_js_time())
            yield Request(login_url,
                          callback=self.find_sla,
                          meta=meta,
                          dont_filter=True,
                          errback=self.err_callback
                          )
        except Exception:
            yield from self.except_handle(response.meta['item']["username"], msg="user_login_two解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试",
                                          logout_request=self.get_logout_request(meta))

    def find_sla(self, response):
        meta = response.meta
        try:
            sla_url = self.sla_url_pattern.search(response.text).group(1)
            yield Request(url=sla_url,
                          callback=self.find_detail,
                          meta=meta,
                          dont_filter=True,
                          errback=self.err_callback
                          )
        except Exception:
            yield from self.except_handle(response.meta['item']["username"], msg="find_sla解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试",
                                          logout_request=self.get_logout_request(meta))

    def get_search_email_request(self, response, cookies=None):
        meta = response.meta
        username = meta['item']['username']
        self.crawling_login(username)

        flag = 1 if username.endswith('.cn') else 0
        search_url = 'https://m%s.mail.sina.com.cn/classic/findmail.php' % flag
        data_form = {
            'act': 'findmail',
            'fid[]': '',
            'order': 'htime',
            'sorttype': 'desc',
            'flag': '',
            'pageno': '1',
            'fol': 'allfolder',
            'phrase': CREDIT_CARD_KEYWORD,
            'attlimit': '2',
            'timelimit': '0',
            'starttime': '',
            'endtime': '',
            'contlimit[]': '1',  # 搜索位置，1代表subject
            'readflag': '2',
            'searchType': '1',
            'tag': '-1',
            'webmail': '1',
        }
        meta['data_form'] = data_form
        meta['flag'] = flag
        meta['search_url'] = search_url
        return FormRequest(url=search_url,
                           formdata=data_form,
                           callback=self.parse_search,
                           cookies=cookies,
                           meta=meta,
                           dont_filter=True,
                           errback=self.err_callback
                           )

    def find_detail(self, response):
        try:
            yield self.get_search_email_request(response)
        except Exception:
            meta = response.meta
            yield from self.except_handle(meta['item']['username'],
                                          msg="find_detail解析异常",
                                          tell_msg="邮箱登录失败，请刷新重试",
                                          logout_request=self.get_logout_request(meta))

    def _enb64(self, text):
        if isinstance(text, str):
            text = text.encode()
        return b64encode(text)

    def _url_encode(self, text):
        if isinstance(text, str):
            text = text.encode()
        return quote(text)

    def parse_search(self, response):
        meta = response.meta
        item = meta['item']
        try:
            flag = meta['flag']
            mail_list = meta.setdefault("mail_list", [])
            the_data = json_loads(response.text)['data']
            for xr in the_data['maillist']:
                url = 'http://m%s.mail.sina.com.cn/classic/readmail.php' \
                      '?webmail=1&fid=new&mid=%s&ts=17428' % (flag, xr[0])  # 拼接mid
                address = parseaddr(xr[1])[1]
                subject = xr[3]
                bankname = check_email_credit_card_by_address(subject, address)
                if bankname:
                    mail_list.append((url, bankname, subject))

            next_page = the_data['currentpage'] + 1
            if the_data['pagenum'] >= next_page:  # 如果存在多页,执行翻页操作
                data_form = meta['data_form']
                data_form['pageno'] = str(next_page)
                yield FormRequest(url=meta['search_url'],
                                  formdata=data_form,
                                  callback=self.parse_search,
                                  meta=meta,
                                  dont_filter=True,
                                  errback=self.err_callback
                                  )
            else:
                if not mail_list:
                    yield from self.crawling_done(item, logout_request=self.get_logout_request(meta))
                    return

                headers = get_headers_from_response(response)
                parse_detail = self.parse_detail
                err_callback = self.err_callback
                count = len(mail_list)
                for url, bankname, subject in mail_list:
                    yield Request(url=url,
                                  headers=headers,
                                  callback=parse_detail,
                                  meta={'item': item,
                                        'bankname': bankname,
                                        'subject': subject,
                                        'count': count
                                        },
                                  dont_filter=True,
                                  errback=err_callback
                                  )
        except Exception:
            yield from self.except_handle(item['username'], msg="查找账单异常",
                                          tell_msg="查找账单异常",
                                          logout_request=self.get_logout_request(meta))

    def parse_detail(self, response):
        meta = response.meta
        item = meta['item']
        try:
            json_result = json_loads(response.text)['data']['body']
            bill_record = self.get_bill_record(meta['bankname'], meta['subject'], json_result)
            bill_records = item['bill_records']
            bill_records.append(bill_record)
            if meta['count'] == len(bill_records):
                yield from self.crawling_done(item, logout_request=self.get_logout_request(meta))
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="账单解析异常",
                                          tell_msg="账单解析异常",
                                          logout_request=self.get_logout_request(meta))

    def get_logout_request(self, meta):
        return Request('https://m0.mail.sina.com.cn/classic/logout.php?from=mail',
                       self.logout_1, dont_filter=True, meta=meta, errback=self.logout_1)

    def logout_1(self, arg):
        if isinstance(arg, Response):
            logout_url = 'https://login.sina.com.cn/cgi/login/logout.php' \
                         '?r=http%3A%2F%2Fmail.sina.com.cn%2F%3Flogout'
            yield Request(logout_url,
                          callback=self.parse_logout,
                          dont_filter=True,
                          meta=arg.meta,
                          errback=self.parse_logout
                          )
        else:
            self.logger.error("logout: " + repr(arg))

        # logout_url = re_findall('replace\("(.*?)"\);', arg.text)[0]
        # yield Request(logout_url,
        #               callback=self.parse_logout,
        #               dont_filter=True,
        #               meta=arg.meta,
        #               errback=self.parse_logout
        #               )
