# coding:utf-8

from base64 import b64encode
from random import sample
from re import compile as re_compile

from requests import Session as req_session
from scrapy import Request

from crawler_bqjr.items.ecommerce_items import YhdItem
from crawler_bqjr.spiders.b2c_ecommerce_spiders.base import EcommerceSpider
from crawler_bqjr.spiders_settings import YHD_DICT
from crawler_bqjr.tools.aes import AesUtil
from crawler_bqjr.tools.rsa_tool import RsaUtil
from crawler_bqjr.utils import get_js_time


class YhdSpider(EcommerceSpider):
    """
    一号店爬虫
    """

    name = YHD_DICT["一号店"]
    allowed_domains = ["yhd.com"]
    start_urls = ['https://passport.yhd.com/passport/login_input.do']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=YhdItem, **kwargs)
        self.headers = {
            "Host": "passport.yhd.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        self.__cookies = None
        self.max_try_count = 3

        self.reg_pubkey = re_compile(r'var pubkey = \s*"([^"]*)"')
        self.reg_returnurl = re_compile(r'var returnUrl = "([^"]*)"')

    def parse(self, response):
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        try:
            if self.login(username, item["password"]):
                # 通知授权成功
                self.crawling_login(username)

                # 登录成功，开始获取用户信息
                user_info_url = "http://home.yhd.com/myinfo/index.do"
                yield Request(
                    url=user_info_url,
                    headers=self.headers,
                    cookies=self.__cookies,
                    callback=self._get_user_info,
                    meta=meta,
                    errback=self.err_callback,
                    dont_filter=True
                )
            else:
                self.logger.error("通过账号密码登录一号店失败")
                yield from self.crawling_failed(username, "通过账号密码登录一号店失败")
        except Exception:
            yield from self.except_handle(username, "登录异常")

    def login(self, username, password):
        """
        登录
        :param username:
        :param password:
        :return:
        """
        isSucc = False
        try:
            session = req_session()
            post_url = "https://passport.yhd.com/publicPassport/login.do"
            post_data = self.__get_post_data(session, username, password)
            try_count = 0
            msg = ""
            while not isSucc:
                page = session.post(post_url, data=post_data, headers=self.headers, verify=False).json()
                self.logger.info("post返回信息:{0}".format(page))
                err_code = page.get("errorCode", 0)
                isSucc = (err_code == 0)
                if isSucc:
                    msg = "登录成功"
                    return_url = page.get("returnUrl", "")
                    self.logger.info("returnUrl:%s" % return_url)
                    break

                if page.get("ShowValidCode", 0):
                    self.logger.info("验证码为空或验证码错误")
                    get_cap_url = "https://passport.yhd.com/publicPassport/getCaptcha.do"
                    cap_data = {"username": username, "source": "1"}
                    captcha_info = session.post(get_cap_url, data=cap_data, headers=self.headers, verify=False).json()
                    self.logger.debug(captcha_info)
                    captcha_url = captcha_info.get("url") if captcha_info.get("errorCode") == 0 else ''
                    sig = captcha_info.get("sig")
                    vcd_headers = self.headers.copy()
                    vcd_headers["Host"] = "captcha.yhd.com"
                    vcd_body = session.get(captcha_url, headers=vcd_headers, verify=False).content
                    self.logger.info("需要输入验证码")
                    captcha_code = self.ask_image_captcha(vcd_body, username)
                    self.logger.info("验证码为：%s" % captcha_code)
                    post_data.update({"validCode": captcha_code, "sig": sig})

                    try_count += 1
                    if try_count == self.max_try_count:
                        msg = "登录失败次数超过%d次" % self.max_try_count
                        break
                else:
                    msg = "登录失败,error_code:%s" % str(err_code)
                    break

            self.logger.info(msg)
            if isSucc:
                # 获取cookies
                self.__cookies = session.cookies.get_dict()
                return True
            else:
                return False
        except Exception:
            self.logger.exception("一号店登录出错")
            return False

    def _get_user_info(self, response):
        """
        获取用户信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]

        try:
            pass
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取用户信息异常")

    def __get_post_data(self, session, username, password):
        """
        获取登录post参数
        :param session:
        :param username:
        :param password:
        :return:
        """
        try:
            index_url = "https://passport.yhd.com/passport/login_input.do"
            page = session.get(index_url, headers=self.headers, verify=False).text
            pubkey = self.reg_match(page, self.reg_pubkey)
            returnUrl = self.reg_match(page, self.reg_returnurl)

            # 用户名密码均为rsa加密
            rsa = RsaUtil(key_is_hex=False)
            en_user = rsa.encrypt(username, pubkey=pubkey)
            en_pwd = rsa.encrypt(password, pubkey=pubkey)

            # char_length = len(username) + len(password)
            # captchaToken = self.__get_captcha_token(session, char_length=char_length)
            post_data = {
                "credentials.username": en_user,
                "credentials.password": en_pwd,
                "validCode": "验证码",
                "sig": "",
                "captchaToken": None,  # 该参数可省略
                "loginSource": "1",
                "returnUrl": returnUrl,
                "isAutoLogin": "0"
            }
            return post_data
        except Exception:
            self.logger.exception("获取登录参数出错")
            return

    def convert_parm(self, chars, offset):
        return "".join(chr(ord(c) + offset) for c in chars)

    def __get_captcha_token(self, session, char_length):
        """
        获取captcha参数(用户指纹信息)
        :param session:
        :param char_length:
        :return:
        """
        try:
            getenv_url = 'https://captcha.yhd.com/public/getenv.do'
            cap_headers = self.headers.copy()
            cap_headers.update({"Host": "captcha.yhd.com", "Upgrade-Insecure-Requests": "1"})
            env_json = session.get(getenv_url, headers=cap_headers, verify=False).json()
            self.logger.debug(env_json)

            aes_key = env_json.get("k")
            aes_tool = AesUtil(key=aes_key)
            offset = int(aes_tool.decrypt(env_json.get("o"), is_hex=False))
            # ti:(len(ti)=34-->random_a_16+random_b_16+2)
            ti = self.__generate_random_str(length=34)

            # kdc:keydown次数,一般为用户名密码的长度和
            kdc = str(char_length)
            # mdc:mousedown次数(>=4)
            mdc = "4"
            # mpt:mouseover次数(>190)
            mpt = "195"
            # mp:3次mousedown坐标位置(点击用户名框、密码和登录)
            mp = "721,268;916,236;909,377"
            # bds:reversal(base64(random_x_32|kdc|mdc|mpt))
            bds_ori = "%s|%s|%s|%s" % (self.__generate_random_str(32), kdc, mdc, mpt)
            bds = b64encode(bds_ori.encode()).decode()[::-1]

            # kdc, mdc, mpt, mp 参数需要加上偏移量转化
            convert_parm = self.convert_parm
            ori_data = {
                "ti": ti,
                "cc": "j3",
                "js_version": "1.2.1",
                "mpt": convert_parm(mpt, offset=offset),
                "mp": convert_parm(mp, offset=offset),
                "bds": bds,
                "kdc": convert_parm(kdc, offset=offset),
                "mdc": convert_parm(mdc, offset=offset),
                "crt": get_js_time(),
            }
            if env_json.get("f"):
                ori_data["fp"] = env_json.get("f")
            if env_json.get("h"):
                ori_data["h"] = env_json.get("h")
            # 参数为aes加密
            encrypt_data = aes_tool.encrypt(str(ori_data), get_hex=False)
            return encrypt_data
        except Exception:
            self.logger.exception("获取captcha_token出错")
            return

    def __generate_random_str(self, length=32, char_set=None):
        """
        生成随机字符串
        :param length:
        :param char_set:
        :return:
        """
        try:
            if char_set is None:
                char_set = '0123456789abcdef'
            return "".join(sample(char_set, length))
        except Exception:
            self.logger.exception("生成随机字符串出错")
            return
