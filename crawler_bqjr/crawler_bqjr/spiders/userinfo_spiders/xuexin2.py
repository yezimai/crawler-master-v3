
from random import random
from re import compile as re_compile

from scrapy.http import Request, FormRequest

from crawler_bqjr.spiders.userinfo_spiders.base import UserInfoSpider
from crawler_bqjr.utils import get_content_by_requests, get_cookiejar_from_response


class XuexinSpider(UserInfoSpider):
    name = "xuexin"
    start_urls = ["https://account.chsi.com.cn/passport/login"
                  "?service=https%3A%2F%2Fmy.chsi.com.cn%2Farchive%2"
                  "Fj_spring_cas_security_check", ]

    custom_settings = {
        'REDIRECT_ENABLED': False,  # getArtifact会返回302重定向网页并set-cookies，Scrapy暂不支持重定向set-cookies，所以关闭重定向功能
        'HTTPERROR_ALLOWED_CODES': [302],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gdjy_xj_url = 'https://my.chsi.com.cn/archive/gdjy/xj/show.action'
        self.gdjy_xl_url = 'https://my.chsi.com.cn/archive/gdjy/xl/show.action'
        self.user_login = "user.login"
        self.my_archive_jsessionid = ''
        self.jsession_pattern = re_compile(r'=(.*)')
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/56.0.2924.87 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Origin": "https://account.chsi.com.cn"
        }

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        request.meta['dont_merge_cookies'] = True
        request.meta['proxy'] = "http://118.212.137.135:31288"
        return request

    def _get_xjxl_key(self, dict_data):
        return "_".join([dict_data.get("collegeName", ""),
                         dict_data.get("majorName", ""),
                         dict_data.get("eduLevel", "")])

    def merge_dict(self, dict_a, dict_b):
        for k, v in dict_a.items():
            new_v = dict_b.get(k, "")
            if len(new_v) > len(v):
                dict_a[k] = new_v

        for k, v in dict_b.items():
            dict_a.setdefault(k, v)

        return dict_a

    def parse(self, response):
        headers = self.headers.copy()
        meta = response.meta
        meta['headers'] = headers
        meta['captcha_retry_time'] = 5
        item = meta["item"]
        item['xueli'] = []

        if response.status == 302:
            yield from self.parse_login(response)
        else:
            try:
                self.logger.info("请求登录接口->%s" % self.user_login)
                lt = response.xpath('//input[@name="lt"]/@value').extract_first("")
                captcha_code = None
                # self.logger.debug('captcha1 ' + str(response.xpath('//input[@id="captcha"]').extract_first("")))
                # self.logger.debug('captcha2 ' + str(response.xpath('//div[@class="ct_input errors"]').extract_first("")))
                if response.xpath('//input[@id="captcha"]').extract_first() \
                        or response.xpath('//div[@class="ct_input errors"]').extract_first():
                    meta['captcha_retry_time'] -= 1
                    cookiejar = get_cookiejar_from_response(response)
                    url = "https://account.chsi.com.cn/passport/captcha.image?id=" + str(random())
                    captcha_body = get_content_by_requests(url, headers, cookie_jar=cookiejar, proxies={"https":response.meta['proxy'],
                                                                                                        "http":response.meta['proxy']})
                    captcha_code = self.ask_image_captcha(captcha_body, item['username'], file_type=".jpeg")
                req_data = self.get_req_data(self.user_login, user_name=item["username"],
                                             password=item["password"], lt=lt, captcha=captcha_code)
                self.logger.debug(req_data)
                headers['Cookie'] = response.headers.get('Set-Cookie').decode()
                headers['Referer'] = self._start_url_
                r = FormRequest(
                    headers=headers,
                    url=self._start_url_,
                    callback=self.parse_login,
                    formdata=req_data,
                    meta=meta,
                    errback=self.err_callback,
                    dont_filter=True
                )
                yield r
            except Exception:
                yield from self.except_handle(meta["item"]["username"], "学信网---爬虫解析入口异常")

    def parse_login(self, response):
        meta = response.meta
        item = meta["item"]
        # self.logger.debug(response.request.body.decode())
        # self.logger.debug('header ' + str(response.headers))
        if response.status != 302:
            if response.xpath('//div[@id="status"]/text()').extract_first():
                yield from self.error_handle(item["username"], "%s 账号或密码错误" % item["username"],
                                             tell_msg=response.xpath('//div[@id="status"]/text()').extract_first())
                return
            if response.xpath('//input[@id="captcha"]').extract_first() \
                    or response.xpath('//div[@class="ct_input errors"]').extract_first():
                meta['captcha_retry_time'] -= 1
                if meta['captcha_retry_time'] < 0:
                    yield from self.error_handle(item["username"], "%s 图片验证码请求五次，退出" % item["username"],
                                                 tell_msg='验证码已刷新五次，请重试')
                    return
                lt = response.xpath('//input[@name="lt"]/@value').extract_first("")
                cookiejar = get_cookiejar_from_response(response)
                url = "https://account.chsi.com.cn/passport/captcha.image?id=" + str(random())
                headers = meta['headers']
                captcha_body = get_content_by_requests(url, headers, cookie_jar=cookiejar)
                captcha_code = self.ask_image_captcha(captcha_body, item['username'], file_type=".jpeg")
                req_data = self.get_req_data(self.user_login, user_name=item["username"],
                                             password=item["password"], lt=lt, captcha=captcha_code)
                try:
                    headers['Cookie'] = response.headers.get('Set-Cookie').decode()
                except Exception:
                    pass
                self.logger.debug(req_data)
                self.logger.debug(headers)
                r = FormRequest(
                    headers=headers,
                    url=self._start_url_,
                    callback=self.parse_login,
                    formdata=req_data,
                    meta=meta,
                    errback=self.err_callback,
                    dont_filter=True
                )
                yield r
            else:
                yield from self.error_handle(item["username"], "%s 账号或密码错误" % item["username"],
                                             tell_msg='账号或密码错误')
                return
        else:
            try:
                get_jsession_url = response.headers.get('Location')
                if get_jsession_url:
                    get_jsession_url = get_jsession_url.decode()
                    self.logger.info("请求获取sessionid接口->%s" % get_jsession_url)
                    headers = meta['headers']
                    headers['Referer'] = response.url
                    yield Request(
                        headers=meta['headers'],
                        url=get_jsession_url,
                        callback=self.parse_getJsession,
                        meta=meta,
                        errback=self.err_callback,
                        dont_filter=True
                    )
                else:
                    yield from self.error_handle(item["username"], "%s 账号或密码错误" % item["username"],
                                                 tell_msg='账号或密码错误')
            except Exception:
                yield from self.except_handle(item["username"], "学信网---登录数据解析异常")

    def parse_getJsession(self, response):
        meta = response.meta
        set_cookie = response.headers.get('Set-Cookie')
        if set_cookie and 'JSESSIONID' in set_cookie.decode():
            set_cookie = set_cookie.decode()
            self.logger.info("获取Set-Cookie->%s" % set_cookie)
            try:
                archive_jsessionid = self.jsession_pattern.search(set_cookie).group(1)

                self.crawling_login(meta["item"]["username"])  # 通知授权成功

                meta["archive_jsessionid"] = archive_jsessionid
                meta['headers']['Cookie'] = set_cookie
                yield Request(
                    headers=meta['headers'],
                    url=self.gdjy_xj_url,
                    callback=self.parse_get_xj,
                    meta=meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
            except Exception:
                yield from self.except_handle(response.meta['item']["username"], "学信网---Set-Cookie解析异常")
        else:
            yield from self.error_handle(response.meta['item']["username"], "学信网---Set-Cookie解析异常")

    def parse_get_xj(self, response):
        """
        学籍
        """

        meta = response.meta
        item = meta["item"]
        archive_jsessionid = meta["archive_jsessionid"]
        try:
            xj_dict = {}
            for table_info in response.xpath('//div[@class="clearfix"]'):
                xj_img = table_info.xpath('.//img[@class="xjxx-img"]/@src').extract_first("")
                xj_info_pic_data = get_content_by_requests(xj_img, headers=meta['headers'],
                                                           cookie_jar={'JSESSIONID': archive_jsessionid})
                xj_info_dict = self.pic_orc(xj_info_pic_data)
                xj_dict[self._get_xjxl_key(xj_info_dict)] = xj_info_dict

            meta['xj_dict'] = xj_dict
            yield Request(
                headers=meta['headers'],
                cookies={'JSESSIONID': archive_jsessionid},
                url=self.gdjy_xl_url,
                callback=self.parse_get_xl,
                meta=meta,
                dont_filter=True,
                errback=self.err_callback
            )
        except Exception:
            yield from self.except_handle(item["username"], "学信网---提取学籍信息数据解析异常")

    def parse_get_xl(self, response):
        meta = response.meta
        item = meta["item"]
        xj_dict = meta['xj_dict']
        try:
            xueli = item['xueli']
            archive_jsessionid = meta["archive_jsessionid"]
            for table_info in response.xpath('//div[@class="clearfix"]'):
                # 学历信息中的毕业证照片链接
                url = table_info.xpath('.//div[@class="pic"]/img/@src').extract_first()
                if url and 'no-photo' not in url:
                    pic_data = get_content_by_requests('https://my.chsi.com.cn' + url, headers=meta['headers'],
                                                       cookie_jar={'JSESSIONID': archive_jsessionid})
                else:
                    pic_data = b''
                xl_img = table_info.xpath('.//img[@class="xjxx-img"]/@src').extract_first("")
                xl_info_pic_data = get_content_by_requests(xl_img, headers=meta['headers'],
                                                           cookie_jar={'JSESSIONID': archive_jsessionid})
                xl_info_dict = self.pic_orc(xl_info_pic_data)
                xl_info_dict['photo'] = pic_data
                key = self._get_xjxl_key(xl_info_dict)
                if key in xj_dict:
                    xueli.append(self.merge_dict(xj_dict.pop(key), xl_info_dict))
                else:
                    xueli.append(xl_info_dict)

            xueli.extend(xj_dict.values())

            yield from self.crawling_done(item)
        except Exception:
            yield from self.except_handle(item["username"], "学信网---提取学历信息数据解析异常")

    def get_req_data(self, method, user_name=None, password=None, lt=None, captcha=None):
        data = dict()
        if method == self.user_login:
            data["username"] = user_name
            data["password"] = password
            data['lt'] = lt
            data['_eventId'] = 'submit'
            data['submit'] = '登  录'
            if captcha:
                data['captcha'] = captcha
            return data
