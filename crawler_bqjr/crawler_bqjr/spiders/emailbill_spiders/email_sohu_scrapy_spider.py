# -*- coding:utf-8 -*-

from hashlib import md5
from re import compile as re_compile
from time import sleep
from urllib.parse import quote

from requests import get as req_get, post as req_post, Session as req_session
from scrapy.http import Request, FormRequest

from crawler_bqjr.spider_class import PhantomJSWebdriverSpider
from crawler_bqjr.spiders.emailbill_spiders.base import EmailSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import CREDIT_CARD_KEYWORD, \
    check_email_credit_card_by_address
from crawler_bqjr.spiders_settings import EMAIL_DICT
from crawler_bqjr.utils import get_js_time, get_headers_from_response
from global_utils import json_loads


class EmailSohuSpider(EmailSpider, PhantomJSWebdriverSpider):
    name = EMAIL_DICT['sohu.com']
    allowed_domains = ['sohu.com']
    start_urls = ['https://v4.passport.sohu.com/fe/', ]
    custom_settings = {
        'DOWNLOAD_DELAY': 0,  # 防封杀
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result_pattern2 = re_compile(r'\((.*?)\);')
        self.jv_pattern = re_compile(r'\("(.*?)"\)')
        self.headers = {
            'Host': 'v4.passport.sohu.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://mail.sohu.com',
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            'Referer': 'https://mail.sohu.com/fe/',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9'
        }
        self.page_step = 1000
        self.keyword = quote(CREDIT_CARD_KEYWORD.encode('utf-8'))
        self.search_url = "https://mail.sohu.com/fe/search?offset=%s&order=id&sort=0&t=%s" \
                          "&words=%s&limit=" + str(self.page_step)

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        username = item["username"]
        try:
            cookies_dict = dict()
            req_ss = req_session()
            index_res = req_ss.get(self._start_url_, headers=self.headers, verify=False)
            cookies_dict.update(index_res.cookies.get_dict())

            # 获取cookies
            index_cookie_url = 'https://v4.passport.sohu.com/i/cookie/common' \
                               '?callback=passport403_cb%s&_=%s' % (get_js_time(), get_js_time())
            index_cookie_res = req_ss.get(index_cookie_url, verify=False)

            cookies_dict.update(index_cookie_res.cookies.get_dict())
            code_callback_url = 'https://v4.passport.sohu.com/i/jf/code?callback=passport403_cb%s' \
                                '&type=0&_=%s' % (get_js_time(), get_js_time())
            code_callback_res = req_ss.get(code_callback_url, verify=False)
            cookies_dict.update(code_callback_res.cookies.get_dict())

            # 解析
            jv_val = self.js_driver(code_callback_res.text).split('=')
            jv_dict = {jv_val[0]: jv_val[1].split(';', 1)[0]}
            req_ss.cookies.update(jv_dict)
            cookies_dict.update(jv_dict)
            data = {
                'userid': username,
                'password': md5(item["password"].encode('utf-8')).hexdigest(),
                'appid': '101305',
                'callback': 'passport403_cb' + get_js_time()
            }
            login_url = 'https://v4.passport.sohu.com/i/login/101305'
            res = req_ss.post(login_url, data=data)
            result = json_loads(self.result_pattern2.search(res.text).group(1))
            status = result['status']
            if status == 404:
                yield from self.error_handle(username, "搜狐邮箱---账号密码错误",
                                             tell_msg="请刷新页面重试")
                return
            elif status == 465:
                callback_url = 'https://v4.passport.sohu.com/i/jf/code?callback=passport403_cb%s' \
                               '&type=0&_=%s' % (get_js_time(), get_js_time())
                jv_content = req_ss.get(callback_url)
                cookies_dict.update(jv_content.cookies.get_dict())
                code_callback_res = req_ss.get(code_callback_url, verify=False)
                jv = self.js_driver(code_callback_res.text).split('=')
                cookies_dict.update({jv[0]: jv[1].split(';', 1)[0]})

                pagetoken = get_js_time()
                captcha_url = 'https://v4.passport.sohu.com/i/captcha/picture?pagetoken=%s' \
                              '&random=passport403_sdk%s' % (pagetoken, get_js_time())
                self.set_image_captcha_headers_to_ssdb(cookies_dict, username)
                self.set_email_img_url_to_ssdb(captcha_url, username)
                captcha_body = req_get(captcha_url, cookies=cookies_dict).content
                captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".png")
                data.update({'captcha': captcha_code, 'pagetoken': str(pagetoken)})
                res = req_post(login_url, data=data, cookies=cookies_dict, verify=False)

                result_two = json_loads(self.result_pattern2.search(res.text).group(1))
                status_two = result_two['status']
                if status_two == 420:
                    yield from self.error_handle(username, "搜狐邮箱---输入验证错误!",
                                                 tell_msg="输入验证错误!")
                    return
                elif status_two != 200:
                    yield from self.error_handle(username, "搜狐邮箱---未知错误!",
                                                 tell_msg="抓取失败!")
                    return

            if res:
                # 登录成功之后需发送回滚请求,
                cookies_dict.update(res.cookies.get_dict())
                callback_url = 'https://mail.sohu.com/fe/login/callback'
                call_back = req_ss.post(callback_url, verify=False)

                # 更新回滚 cookie
                cookies_dict.update(call_back.cookies.get_dict())

                # 构造登出cookies
                logout_con = req_ss.get('https://v4.passport.sohu.com/i/jf/code?callback=passport403_cb%s'
                                        '&type=0&_=%s' % (get_js_time(), get_js_time()),
                                        cookies=cookies_dict, verify=False)
                ppmdig_cookies = logout_con.cookies.get_dict()
                logout_val = self.js_driver(logout_con.text).split('=')
                ppmdig_cookies.update({logout_val[0]: logout_val[1].split(';', 1)[0]})

                search_url = self.search_url % (0, get_js_time(), self.keyword)
                meta["cookies_dict"] = cookies_dict
                meta["ppmdig_cookies"] = ppmdig_cookies
                yield Request(
                    url=search_url,
                    cookies=cookies_dict,
                    callback=self.parse_search,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
                # 登录成功之后直接访问json页面,提取对应数据进行筛选
                # 登录成功后,用户用可能讲账单添加到自定义文件夹里,这里需要筛选用户自定义内容,自定的新ID为17开始
                # 首先判断是否存在自定义标签
            else:
                yield from self.error_handle(username, "搜狐邮箱---账号密码错误!",
                                             tell_msg="账号或密码错误,请刷新页面重试")
        except Exception:
            yield from self.except_handle(username, "登录入口异常",
                                          tell_msg="邮箱登录失败，请刷新页面重试")

    def parse_search(self, response):
        text = response.text
        meta = response.meta
        item = meta['item']
        try:
            if not text:
                yield item
                yield from self.error_handle(item["username"], "搜狐邮箱---搜索账单没结果",
                                             tell_msg="未找到账单")
                return

            mail_list = meta.setdefault("mail_list", [])
            the_data = json_loads(response.text)['data']
            for it in the_data['list']:
                subject = it['subject']
                bankname = check_email_credit_card_by_address(subject, it["from"])
                if bankname:
                    detail_url = 'https://mail.sohu.com/fe/getMail?id=%s&t=%s' % (it['id'], get_js_time())
                    mail_list.append((detail_url, bankname, subject))

            page_step = self.page_step
            page_num = meta.get('page_num')
            if page_num is None:
                page_num = (the_data['total'] + page_step - 1) // page_step
                meta['page_num'] = page_num

            next_page = meta.get('current_page', 0) + 1
            if page_num > next_page:
                meta["current_page"] = next_page
                search_url = self.search_url % (next_page * page_step, get_js_time(), self.keyword)
                yield Request(
                    url=search_url,
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
                                  callback=parse_detail,
                                  headers=headers,
                                  meta={'item': item,
                                        'bankname': bankname,
                                        'subject': subject,
                                        'count': count,
                                        'cookies_dict': meta["cookies_dict"],
                                        'ppmdig_cookies': meta["ppmdig_cookies"],
                                        },
                                  dont_filter=True,
                                  errback=err_callback
                                  )
        except Exception:
            yield from self.except_handle(item['username'], "查找账单异常",
                                          tell_msg="查找账单异常",
                                          logout_request=self.get_logout_request(meta))

    def parse_detail(self, response):
        meta = response.meta
        item = meta['item']
        try:
            the_data = json_loads(response.text)['data']
            bill_record = self.get_bill_record(meta['bankname'], the_data['subject'], the_data['display'])
            bill_records = item['bill_records']
            bill_records.append(bill_record)
            if len(bill_records) == meta['count']:
                # 如果匹配出来如果没有结果,说明有抓取到用户相关信息.直接返回完成.并退出
                yield from self.crawling_done(item, logout_request=self.get_logout_request(meta))
        except Exception:
            yield from self.except_handle(item['username'], "账单解析异常",
                                          tell_msg="账单解析异常",
                                          logout_request=self.get_logout_request(meta))

    def js_driver(self, content):
        for i in range(2):
            driver = self.load_page_by_webdriver('https://www.baidu.com/')
            try:
                jv = self.jv_pattern.search(content).group(1)
                return driver.execute_script('var val=%s;return val;' % jv)
            except Exception:
                self.logger.exception("百度解密异常")
                sleep(1)
            finally:
                driver.quit()

    def get_logout_request(self, meta):
        cookies_dict = meta["cookies_dict"]
        cookies_dict.update(meta["ppmdig_cookies"])
        data = {
            'appid': '101305',
            'callback': 'passport403_cb%s' % get_js_time()
        }
        return FormRequest(
            url='https://v4.passport.sohu.com/i/logout/101305',
            callback=self.parse_logout,
            headers={},
            formdata=data,
            cookies=cookies_dict,
            meta=meta,
            dont_filter=True,
            errback=self.parse_logout
        )
