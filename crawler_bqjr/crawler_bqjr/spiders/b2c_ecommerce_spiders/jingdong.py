# -*- coding: utf-8 -*-

from random import random, randint
from re import compile as re_complie

from scrapy import Request, FormRequest

from crawler_bqjr.captcha.recognize_captcha import BadCaptchaFormat
from crawler_bqjr.items.ecommerce_items import JDItem
from crawler_bqjr.spider_class import CaptchaTimeout
from crawler_bqjr.spiders.b2c_ecommerce_spiders.base import EcommerceSpider
from crawler_bqjr.spiders_settings import JINGDONG_DICT
from crawler_bqjr.tools.rsa_tool import RsaUtil
from crawler_bqjr.utils import get_js_time
from global_utils import json_loads, json_dumps


class JingDongSpider(EcommerceSpider):
    """
    京东爬虫
    """
    name = JINGDONG_DICT["京东"]
    allowed_domains = ["jd.com"]
    start_urls = ['https://passport.jd.com/new/login.aspx']

    SEX_DICT = {
        "0": "男",
        "1": "女",
        "2": "保密"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=JDItem, **kwargs)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.91 Safari/537.36",
            "Accept": "text/plain, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        self.authcode_headers = {
            "Host": "authcode.jd.com",
            "Referer": "https://passport.jd.com/uc/login?ltype=logout"
        }

        self.__qrcode_cookies_str = '''__jdv=122270672|direct|-|none|-|1508489681945; __jda=122270672.15084896819431824300958.1508489682.1508491891.1508721524.3; __jdc=122270672; _jrda=3; 3AB9D23F7A4B3C9B=7UFNRLR3GQOEJRMHB6JHYYOHRPK43IVIH6P4Q36C5GIUPO6QXDOSJJICSSYF4T7BPMPUADIHWV2E5PCA6ZRAECZN6I; __jdu=15084896819431824300958; QRCodeKey={codekey}; wlfstk_smdl={token}'''
        self.login_try_count = 3

        self.reg_qrcode_url = re_complie('class="qrcode-img">\s*<img src="([^"]*)"')
        self.reg_appid = re_complie('appid=(\d+)')
        self.reg_score = re_complie("^([\d\.]+)$")
        self.reg_tar_str = re_complie("(\{[\s\S]+\})")
        self.reg_order_ids = re_complie("ORDER_CONFIG\['finishOrderIds'\]='([^']+)'")
        self.reg_birthday = re_complie("originalBirthday='([^']*)'")
        self.reg_sex = re_complie('if\(1==1\)\{\s*\$\("input\[name=sex\]"\).get\((\d)\)')
        self.reg_email = re_complie('infomail">\s*<div>\s*<strong>([^<]*)<')
        self.reg_mobile = re_complie('id="mobile" class="ftx-\d+">([^<]*)\s*<')
        self.reg_real_name = re_complie('>您认证的实名信息：</span>\s*<strong class="ftx-\d+">([^<]*)<')
        self.reg_id_card = re_complie('>您认证的实名信息：</span>\s*<strong class="ftx-\d+">[^<]*'
                                      '</strong>\s*<strong class="ftx-\d+">([^<]*)<')
        self.reg_order_status = re_complie('<h3 class="state-txt ftx-02">([^<]*)<')
        self.reg_settle_date = re_complie('value="([^"]*)" id="datesubmit')
        self.reg_goods_amount = re_complie('>商品总额：</span>\s*<span class="txt">([^<]*)<')
        self.reg_cashback_amount = re_complie('>返　　现：</span>\s*<span class="txt">-([^<]*)<')
        self.reg_transportation_cost = re_complie('>运　　费：</span>\s*<span class="txt">([^<]*)<')
        self.reg_settle_amount = re_complie('>应付总额：</span>\s*<span class="txt count">([^<]*)<')
        self.reg_pay_mode = re_complie('>\s*付款方式：\s*</span>\s*<div class="info-rcol">([^<]*)<')
        self.reg_receive_name = re_complie('>\s*收货人：\s*</span>\s*<div class="info-rcol">([^<]*)<')
        self.reg_receive_address = re_complie('>\s*地址：\s*</span>\s*<div class="info-rcol">([^<]*)<')
        self.reg_receive_mobile = re_complie('>\s*手机号码：\s*</span>\s*<div class="info-rcol">([^<]*)<')
        self.reg_goods_list = re_complie('<tr class=".*?product-\d+">([\s\S]*?)</tr')
        self.reg_good_name = re_complie('class="p-name">[\s\S]*?<a[\s\S]*?title="([^"]*)">')
        self.reg_good_num = re_complie('class="f-price">[^<]*</span>\s*</td>\s*<td>(\d+)<')
        self.reg_good_price = re_complie('<span class="f-price">([^<]*)</span>')
        self.reg_key_value = re_complie('id="keyValue"\s*value="([^"]*)"')

    def parse(self, response):
        meta = response.meta
        username = meta["item"]["username"]

        qrcode_login_flag = False  # 二维码登录
        try:
            if qrcode_login_flag:
                # 二维码登录
                yield from self.qrcode_login(response)
            else:
                # 账户密码登录
                yield Request(
                    url=self._start_url_,
                    headers=self.headers,
                    meta=meta,
                    callback=self._login,
                    errback=self.err_callback,
                    dont_filter=True
                )
        except Exception:
            yield from self.except_handle(username, "登录异常")

    def _login(self, response):
        """
        进行登录
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        username = item["username"]

        try:
            base_url = response.urljoin("/uc/loginService")
            uuid = self.get_value_by_name(response, "uuid")
            pubKey = self.get_value_by_name(response, "pubKey")
            seqSid = ''

            login_post_url = "%s?uuid=%s&ReturnUrl=%s&r=%s&version=2015" \
                             % (base_url, uuid, "https%3A%2F%2Fwww.jd.com%2F", str(random()))

            # 密码为rsa加密
            rsa = RsaUtil(key_is_hex=False)
            encode_pwd = rsa.encrypt(item["password"], pubkey=pubKey)

            temp_cookies = {}
            for c in response.headers.getlist('Set-Cookie', []):
                temp_cookies.update(dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv))
            meta["cookies"] = temp_cookies
            authcode = ""
            capthca_div = response.xpath('//div[@id="o-authcode"][@style="display: block;"]').extract_first()
            if capthca_div:
                need_captcha = True
            else:
                auth_url = 'https://passport.jd.com/uc/showAuthCode?r=%s&version=2015' % str(random())
                auth_page = self.http_request(auth_url, method="POST", cookies=temp_cookies,
                                              headers=self.headers, data={"loginName": username})
                need_captcha = ('verifycode":true' in auth_page)
            code_url = response.xpath('//img[@id="JD_Verification1"]/@src2').extract_first()
            if need_captcha and code_url:
                self.logger.info("需要输入验证码")
                new_headers = self.authcode_headers
                code_url = "https:" + code_url if not code_url.startswith("http") else code_url
                code_body = self.http_request(code_url, headers=new_headers, get_str=False)
                # 将请求头等数据存入ssdb，方便刷新图片验证码
                ssdb_headers_data = json_dumps({"headers": new_headers, "uuid": uuid})
                self.set_image_captcha_headers_to_ssdb(headers=ssdb_headers_data, username=username)
                authcode = self.ask_image_captcha(code_body, username)
                self.logger.info("验证码:%s" % authcode)

            login_post_data = {
                "uuid": uuid,
                "eid": self.get_value_by_name(response, "eid"),
                "fp": self.get_value_by_name(response, "fp"),
                "_t": self.get_value_by_name(response, "_t"),
                "loginType": self.get_value_by_name(response, "loginType"),
                "loginname": username,
                "nloginpwd": encode_pwd,
                "chkRememberMe": "",
                "authcode": authcode,
                "pubKey": pubKey,
                "sa_token": self.get_value_by_name(response, "sa_token"),
                "seqSid": seqSid or ''
            }
            self.logger.debug(login_post_data)

            yield FormRequest(
                url=login_post_url,
                headers=self.headers,
                cookies=meta["cookies"],
                callback=self._parse_login_status,
                meta=meta,
                formdata=login_post_data,
                dont_filter=True,
                errback=self.err_callback
            )
        except BadCaptchaFormat:
            yield from self.error_handle(username, "获取验证码图片失败")
        except Exception:
            yield from self.except_handle(username, "准备登录参数异常")

    def _parse_login_status(self, response):
        """
        解析登录结果
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        retry_count = meta.setdefault("retry_count", 0)
        isSucc = False
        try:
            msg = ""
            page = response.text
            self.logger.info(page)
            page = page.replace("(", "").replace(")", "")
            json_page = json_loads(page)
            if "success" in json_page:
                self.logger.info("登录成功")
                isSucc = True
            elif "emptyAuthcode" in json_page:
                msg = "验证码不正确或验证码已过期"
                if retry_count < self.login_try_count:
                    meta["retry_count"] += 1
                    self.logger.info(msg + ",进行重新登录")
                    yield Request(url=self._start_url_, meta=meta, callback=self._login,
                                  errback=self.err_callback, headers=self.headers, dont_filter=True)
                    return
                else:
                    msg = "验证码错误次数超过%d次" % retry_count
            elif "authcode1" in json_page or "authcode2" in json_page or "verifycode" in json_page:
                msg = "验证码错误"
            elif "venture" in json_page:
                self.logger.info("您的账户存在风险，需进一步校验您的信息以提升您的安全等级")
                ret_url = "https://safe.jd.com/dangerousVerify/index.action?username={venture}%3D" \
                          "&ReturnUrl=https://order.jd.com/center/list.action&p={p}" \
                          "".format(venture=json_page["venture"], p=json_page.get("p", ""))
                yield from self._dangerous_verify_scrapy(username, ret_url, response)
                return
            elif "pwd" in json_page:
                msg = "密码错误"
            elif "resetpwd" in json_page:
                msg = "您的账号存在被盗风险，为保障您的账户安全，请前往京东将密码重置后再登录。"
            elif "username" in json_page:
                msg = "用户名错误"
            else:
                msg = "登录失败"

            if isSucc:
                yield self._yield_order_request(response=response)
            else:
                self.logger.info(msg)
                yield from self.crawling_failed(username, msg)
        except CaptchaTimeout:
            yield from self.error_handle(username, "获取短信验证码超时,登录失败")
        except Exception:
            yield from self.except_handle(username, "解析数据失败")

    def _parse_receiver_address(self, response):
        """
        解析收货地址信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]

        try:
            address_info_list = []
            address_list_element = response.xpath('//div[starts-with(@id,"addresssDiv-")]')
            if address_list_element:
                reg_blank = self.reg_blank
                for address_info in address_list_element:
                    (receiver_name, receiver_area, receiver_location_detail, receiver_mobile, receiver_phone,
                     receiver_email) = address_info.xpath('.//div[@class="item-lcol"]'
                                                          '//div[@class="fl"]/text()').extract()
                    receiver_tag = address_info.xpath('.//div[@class="smt"]/h3/text()').extract_first()
                    receiver_is_default = bool(address_info.xpath('.//div[@class="smt"]/h3'
                                                                  '/span[text()="默认地址"]'))

                    temp_dic = {
                        "receiver_name": receiver_name,
                        "receiver_area": receiver_area,
                        "receiver_location_detail": receiver_location_detail,
                        "receiver_mobile": receiver_mobile,
                        "receiver_phone": receiver_phone,
                        "receiver_email": receiver_email,
                        "receiver_tag": receiver_tag,
                        "receiver_is_default": receiver_is_default,
                    }
                    temp_dic = {k: (reg_blank.sub(" ", v).strip() if isinstance(v, str) else v)
                                for k, v in temp_dic.items()}
                    address_info_list.append(temp_dic)
            else:
                self.logger.info("无任何地址信息")

            item["receiver_addresses"] = address_info_list

            # 地址信息抓取完成，开始抓取白条信息
            self.logger.info("地址信息抓取完成，开始抓取白条信息")
            url = "https://baitiao.jd.com/baitiao/quota"
            yield Request(
                url=url,
                headers=self.headers,
                meta=meta,
                dont_filter=True,
                callback=self._get_baitiao_amount,
                errback=self.err_callback
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析收货地址信息异常")

    def _get_baitiao_amount(self, response):
        """
        获取白条信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]

        try:
            json_page = json_loads(response.text)
            msg = json_page.get("msg")  # 获取失败，会出现msg字段
            baitiao = {}
            if msg is None:
                baitiao["avaliable_credit_line"] = json_page.get("availableAmount")
                baitiao["total_credit_line"] = json_page.get("totalAmount")
            else:
                self.logger.info("%s：您暂未开通京东白条" % msg)
            item["baitiao"] = baitiao
            self.logger.info("白条信息获取完成，开始获取打白条次数")

            # 获取打白条次数
            url = "https://baitiao.jd.com/baitiao/consumption"
            yield Request(
                url=url,
                headers=self.headers,
                meta=meta,
                dont_filter=True,
                callback=self._get_baitiao_count,
                errback=self.err_callback
            )

        except Exception:
            yield item
            yield from self.except_handle(item["username"], "解析收货地址信息异常")

    def _get_baitiao_count(self, response):
        """
        获取打白条次数
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]

        try:
            json_page = json_loads(response.text)
            baitiao = item["baitiao"]
            baitiao["baitiao_count"] = json_page["dbtCount"]

            item["baitiao"] = baitiao
            self.logger.info("打白条次数信息获取完成，开始获取白条信用分")

            # 获取白条信用分
            url = "https://baitiao.jd.com/v3/ious/score_getScoreInfo"
            yield Request(
                url=url,
                headers=self.headers,
                meta=meta,
                dont_filter=True,
                callback=self._get_baitiao_score,
                errback=self.err_callback
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取打白条次数异常")

    def _get_baitiao_score(self, response):
        """
        获取白条信用分
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        cookies = meta["cookies"]

        try:
            baitiao = item["baitiao"]
            try:
                baitiao["baitiao_score"] = self.reg_match(response.text, self.reg_score)
            except Exception:
                self.logger.error("获取白条信用分失败")

            # 还需抓取 资产信息，定期持仓，基金持仓，理财持仓 等数据
            self.logger.info("白条信用分获取完成,开始抓取资产数据中...")

            # 抓取资产数据
            assets = self._get_assets_info(cookies)
            item["assets"] = assets

            # 抓取定期理财数据
            position_fixed = self._get_position_fixed_info(cookies)
            item["position_fixed"] = position_fixed

            # 抓取基金理财数据
            position_fund = self._get_position_fund_info(cookies)
            item["position_fund"] = position_fund

            # 抓取完成
            self.logger.info("---->理财数据获取完成，爬虫抓取完成")
            yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取白条信用分异常")

    def _get_assets_info(self, cookies):
        """
        抓取资产数据
        :param cookies:
        :return:
        """
        try:
            assets_url = "http://trade.jr.jd.com/async/browseDataNew.action"
            assets_json = self.http_request(assets_url, cookies=cookies, to_json=True)
            if not assets_json:
                self.logger.error("获取资产数据失败")
                return {}
            data = assets_json.get("data", {})
            assets_info = {
                "total_assets": data.get("totalMoney"),
                "balance": data.get("balance"),
                "balance_available": data.get("balanceAvailable"),
                "finance": data.get("finance"),
                "wallet_money_available": data.get("walletMoneyAvailable"),
                "wallet_money": data.get("walletMoney"),
            }

            return assets_info
        except Exception:
            self.logger.exception("抓取资产数据出错:")
            return {}

    def _get_position_fixed_info(self, cookies):
        """
        抓取定期理财数据
        :param cookies:
        :return:
        """
        try:
            position_fixed = []
            position_url = "https://trade.jr.jd.com/ajaxFinance/financeMainDataNew.action?type=1"
            pos_headers = self.headers.copy()
            pos_headers["Host"] = "trade.jr.jd.com"
            position_json = self.http_request(position_url, headers=pos_headers, cookies=cookies, to_json=True)
            if not position_json:
                self.logger.error("抓取定期理财数据失败")
                return []

            for item in position_json.get("resultList", []):
                pos_item = {
                    "code": item.get("itemCode"),
                    "name": item.get("itemName"),
                    "status": "持有中",  # 状态暂不明确
                    "currency": "人民币",  # 字段暂不明确
                    "start_date": item.get("applyDateString"),
                    "end_date": item.get("deadline") if len(item.get("deadline", [])) == 10 else None,
                    "amount": item.get("keepAmount"),
                }
                # 还有部分字段暂不明确
                position_fixed.append(pos_item)

            return position_fixed
        except Exception:
            self.logger.exception("抓取定期理财数据出错:")
            return []

    def _get_position_fund_info(self, cookies):
        """
        抓取基金理财数据
        :param cookies:
        :return:
        """
        try:
            position_fund = []
            position_url = "https://trade.jr.jd.com/ajaxFinance/financeMainDataNew.action?type=2"
            pos_headers = self.headers.copy()
            pos_headers["Host"] = "trade.jr.jd.com"
            position_json = self.http_request(position_url, headers=pos_headers, cookies=cookies, to_json=True)
            if not position_json:
                self.logger.error("抓取基金理财数据失败")
                return []
            for item in position_json.get("resultList", []):
                pos_item = {
                    "code": item.get("itemCode"),
                    "name": item.get("itemName"),
                    "status": "持有中",  # 状态暂不明确
                    "currency": "人民币",  # 字段暂不明确
                    "capital": item.get("applyAmount"),
                    # "share": item.get("keepAmount"),
                    "usable_share": item.get("keepAmount"),
                    "net_value": item.get("pureAmount"),
                    "net_value_date": item.get("freshDateString", "").replace("年", "-").replace("月", "-").replace("日", ""),
                    "market_value": item.get("applyAmount"),
                    "income_yesterday": item.get("lastDayIncome"),
                }
                # 还有部分字段暂不明确
                position_fund.append(pos_item)

            return position_fund
        except Exception:
            self.logger.exception("抓取基金理财数据出错:")
            return {}

    def _get_order_info(self, response):
        """
        获取订单信息
        :param response:
        :return:
        """
        meta = response.meta
        text = response.text
        item = meta["item"]
        cookies = meta["cookies"]

        try:
            order_list = []
            reg_match = self.reg_match
            order_ids = reg_match(text, self.reg_order_ids)
            if not order_ids:
                self.logger.info("近三个月无任何订单数据")
            else:
                _get_order_detail = self._get_order_detail
                order_ids = order_ids.rstrip(",").split(",")
                self.logger.info("近三个月交易成功订单数为: %d" % len(order_ids))
                for order_id in order_ids:
                    url_pattern = 'href="(//details\.jd\.com/normal/item\.action\?' \
                                  'orderid={orderid}&PassKey=[^"]+)"'.format(orderid=order_id)
                    reg_detail_url = re_complie(url_pattern)
                    detail_url = reg_match(text, reg_detail_url)
                    if not detail_url:
                        self.logger.error("获取订单详情URL失败(该订单可能为话费充值订单)：%s" % order_id)
                        continue
                    order_info = _get_order_detail("https:" + detail_url, order_id, cookies)
                    if order_info is None:
                        self.logger.error("获取订单详情失败：%s" % order_id)
                    else:
                        order_list.append(order_info)

            item["orders"] = order_list
            self.logger.info("订单信息获取完成")

            # 获取用户信息
            self.logger.info("开始获取用户信息...")
            yield Request(
                url="https://i.jd.com/user/info",
                headers=self.headers,
                meta=meta,
                dont_filter=True,
                callback=self._get_user_info,
                errback=self.err_callback
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取订单信息异常")

    def _get_order_detail(self, detail_url, order_id, cookies):
        """
        获取订单详情
        :param detail_url:
        :param order_id:
        :param cookies:
        :return:
        """
        order_info = {}
        try:
            order_headers = self.headers.copy()
            order_headers["Host"] = "details.jd.com"
            page = self.http_request(detail_url, headers=order_headers, cookies=cookies, charset="gb18030")
            if page and isinstance(page, str):
                page = page.replace('&yen;', '')

                order_info["status"] = self.reg_match(page, self.reg_order_status)
                # 付款信息
                order_info["settle_date"] = self.reg_match(page, self.reg_settle_date)
                order_info["goods_amount"] = self.reg_match(page, self.reg_goods_amount)
                order_info["cashback_amount"] = self.reg_match(page, self.reg_cashback_amount)
                order_info["transportation_cost"] = self.reg_match(page, self.reg_transportation_cost)
                order_info["settle_amount"] = self.reg_match(page, self.reg_settle_amount)
                order_info["payment_mode"] = self.reg_match(page, self.reg_pay_mode)
                # 订单收货地址信息
                order_info["name"] = self.reg_match(page, self.reg_receive_name)
                order_info["mobile"] = self.reg_match(page, self.reg_receive_mobile)
                order_info["address_detail"] = self.reg_match(page, self.reg_receive_address)
                # 订单商品信息
                goods_list = self.reg_match(page, self.reg_goods_list, get_one=False)
                goods = []
                if goods_list:
                    for item_str in goods_list:
                        good_info = {
                            "good_name": self.reg_match(item_str, self.reg_good_name),
                            "good_price": self.reg_match(item_str, self.reg_good_price),
                            "good_num": self.reg_match(item_str, self.reg_good_num)
                        }
                        goods.append(good_info)
                else:
                    self.logger.error("获取订单商品信息失败")
                order_info["goods"] = goods
            else:
                self.logger.error("打开订单详情页面失败: %s" % detail_url)
                order_info = None
        except Exception:
            self.logger.exception("获取订单详情出错: %s" % detail_url)
            order_info = None
        finally:
            return order_info

    def _get_user_info(self, response):
        """
        获取用户信息
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        cookies = meta["cookies"]

        try:
            # 获取用户基本信息
            content = response.text
            accounts = {
                "account": item["username"],
                "type": "京东",
                "nick_name": response.xpath('//input[@id="nickName"]/@value').extract_first(),
                "birthday": self.reg_match(content, self.reg_birthday),
                "gender": self.SEX_DICT.get(self.reg_match(content, self.reg_sex), "保密"),
                "email": self.reg_match(content, self.reg_email),
            }
            self.logger.info("用户基本信息获取完成")

            # 获取账号安全信息(手机号,证件号等)
            safe_info = self._get_safe_info(cookies)
            accounts.update(safe_info)

            # 获取更多个人信息(月收入，教育程度等)
            # more_info = self._get_more_user_info()
            # accounts.update(more_info)

            item["accounts"] = accounts
            self.logger.info("用户信息获取完成，开始获取收货地址信息")

            # 获取收货地址信息
            address_url = "https://easybuy.jd.com/address/getEasyBuyList.action"
            yield Request(
                url=address_url,
                headers=self.headers,
                meta=meta,
                dont_filter=True,
                callback=self._parse_receiver_address,
                errback=self.err_callback
            )
        except Exception:
            yield item
            yield from self.except_handle(item["username"], "获取用户信息异常")

    def _get_safe_info(self, cookies):
        """
        获取账号安全信息
        :param cookies:
        :return:
        """
        try:
            safe_url = "https://safe.jd.com/user/paymentpassword/safetyCenter.action"
            req_header = self.headers.copy()
            req_header["Host"] = "safe.jd.com"
            page = self.http_request(safe_url, headers=req_header, cookies=cookies, charset="utf-8")
            if not page:
                self.logger.error("打开账户安全信息页面失败")
                return {}
            safe_info = {
                "mobile": self.reg_match(page, self.reg_mobile),
                "is_real_name": ('<b class="icon-id01">实名认证<' in page),
                "real_name": self.reg_match(page, self.reg_real_name),
                "identification_number": self.reg_match(page, self.reg_id_card),
            }
            self.logger.info("账号安全信息获取完成")

            return safe_info
        except Exception:
            self.logger.exception("获取账号安全信息出错:")
            return {}

    def qrcode_login(self, response):
        """
        京东扫描二维码登录
        :param response:
        :return:
        """
        meta = response.meta
        item = meta["item"]
        username = item["username"]
        try:
            qrcode_info = self._get_qrcode_info()
            if not qrcode_info:
                self.logger.error("获取二维码信息失败")
                yield from self.crawling_failed(username, "获取二维码信息失败,登录失败")

            # 扫描二维码
            status = self.ask_scan_qrcode(qrcode_info.get("content"), username)
            if status != self.SCAN_QRCODE_SUCC:
                self.logger.error("扫描二维码登录失败")
                yield from self.crawling_failed(username, "扫描二维码登录失败")

            self.logger.info("验证扫描结果中------->")
            callback = "jQuery" + str(randint(1E6, 1E7 - 1))
            check_url = ("https://qr.m.jd.com/check?callback={callback}&appid={appid}&token={token}"
                         "&_={timestamp}".format(appid=qrcode_info.get("appid"), token=qrcode_info.get("token"),
                                                 timestamp=get_js_time(), callback=callback))
            headers = qrcode_info.get("headers")
            page = self.http_request(check_url, headers=headers)
            res_json = self.str_to_json(page)
            self.logger.info(res_json)
            if res_json.get("code") == 200:
                self.logger.info("扫描成功")
                ticket = res_json.get("ticket")
                url = "https://passport.jd.com/uc/qrCodeTicketValidation?t={ticket}".format(ticket=ticket)
                headers.update({
                    "Host": "passport.jd.com",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://passport.jd.com/uc/login?ltype=logout",
                })
                yield Request(
                    url=url,
                    headers=headers,
                    meta=meta,
                    callback=self._parse_qrcode_login_result,
                    errback=self.err_callback,
                    dont_filter=True
                )
            else:
                msg = res_json.get("msg")
                yield from self.error_handle(username, msg)
        except Exception:
            yield from self.except_handle(username, "京东扫描二维码登录出错")

    def _parse_qrcode_login_result(self, response):
        """
        解析二维码登录结果
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        try:
            ret_data = json_loads(response.text)
            ret_url = ret_data.get("url", "")
            if "dangerousVerify" in ret_url:
                self.logger.info("账户存在安全风险，需要短信验证")
                yield from self._dangerous_verify_scrapy(username, ret_url, response)
            else:
                self.logger.info("扫描二维码登录成功")
                yield self._yield_order_request(response)
        except Exception:
            yield from self.except_handle(username, "解析二维码登录结果失败,登录失败")

    def _get_qrcode_info(self):
        """
        获取扫描二维码所需信息
        :return:
        """
        try:
            index_url = "https://passport.jd.com/uc/login"
            page = self.http_request(index_url, charset="gb18030")
            qrcode_url = self.reg_match(page, self.reg_qrcode_url)
            qrcode_url = "http:" + qrcode_url if not qrcode_url.startswith("http") else qrcode_url
            temp_headers = self.headers.copy()
            temp_headers["Host"] = "qr.m.jd.com"
            res_info = self.http_request(qrcode_url, headers=temp_headers, get_cookies=True, get_str=False)
            cookies = res_info.get("cookies")
            token = cookies.get("wlfstk_smdl")
            codekey = cookies.get("QRCodeKey")
            appid = self.reg_match(qrcode_url, self.reg_appid)
            cookies_str = self.__qrcode_cookies_str.format(token=token, codekey=codekey)
            qrcode_headers = self.headers.copy()
            qrcode_headers.update({
                "Host": "qr.m.jd.com",
                "Accept": "*/*",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://passport.jd.com/uc/login",
                "Cookie": cookies_str
            })
            re_data = {
                "url": qrcode_url,
                "token": token,
                "appid": appid,
                "content": res_info.get("result"),
                "headers": qrcode_headers,
            }
            return re_data
        except Exception:
            self.logger.exception("获取二维码信息出错:")
            return

    def str_to_json(self, content, pattern=None, charset="utf-8"):
        """
        将str转化为json
        :param content:
        :param pattern:
        :param charset:
        :return:
        """
        try:
            if pattern is None:
                pattern = self.reg_tar_str
            if isinstance(content, bytes):
                content = content.decode(charset)
            tar = pattern.search(content)
            if tar:
                return json_loads(tar.group(1))
            return
        except Exception:
            return

    def _dangerous_verify_scrapy(self, username, verify_url, response):
        """
        登录安全校验(先发送短信验证码，再提交校验)
        :param username:
        :param verify_url:
        :param response:
        :return:
        """
        try:
            headers_data = json_dumps({"url": verify_url})
            self.set_sms_captcha_headers_to_ssdb(headers=headers_data, username=username)
            self.logger.info("等待获取用户输入短信验证码中...")
            sms_code_data = self.ask_sms_captcha(username)

            if not sms_code_data:
                msg = "获取用户输入短信验证码失败,登录失败"
                yield from self.error_handle(username, msg)
            else:
                tmp_data = sms_code_data.split("_")
                sms_code, ret_key = tmp_data if len(tmp_data) == 2 else ("", "")
                self.logger.info("%s ---> sms_code:%s" % (username, sms_code))
                # 获取用户指纹信息eid,fp暂未实现,获取方式:https://payrisk.jd.com/js/td.js
                eid, fp = ("", "")
                valid_url = "https://safe.jd.com/dangerousVerify/checkDownLinkCode.action" \
                            "?code={code}&k={k}&t={stime}&eid={eid}" \
                            "&fp={fp}".format(code=sms_code, k=ret_key, stime=get_js_time(), eid=eid, fp=fp)
                my_headers = self.headers.copy()
                my_headers.update({
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Referer": verify_url,
                    "Host": "safe.jd.com",
                    "Connection": "keep-alive",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36"
                })
                yield Request(
                    url=valid_url,
                    headers=my_headers,
                    callback=self._parse_verify_result,
                    meta=response.meta,
                    dont_filter=True,
                    errback=self.err_callback
                )
        except CaptchaTimeout:
            yield from self.error_handle(username, "获取短信验证码超时,登录失败")
        except Exception:
            msg = "进行安全校验出错:%s" % username
            yield from self.except_handle(username, msg)

    def _parse_verify_result(self, response):
        """
        解析安全认证结果
        :param response:
        :return:
        """
        meta = response.meta
        username = meta["item"]["username"]
        msg = "安全校验失败,登录失败"
        status = False
        try:
            ret_data = json_loads(response.text)
            if ret_data:
                if ret_data.get("resultCode") == "0":
                    self.logger.info("安全校验成功，登录成功")
                    msg = "安全校验成功，登录成功"
                    status = True
                elif ret_data.get("resultCode") == "502":
                    msg = "短信校验码错误，请稍后重新获取"
                    self.logger.info(msg)
                elif ret_data.get("resultMessage") != "":
                    msg = "安全校验失败:%s" % ret_data.get("resultMessage", "")
                    self.logger.info(msg)
                else:
                    msg = "网络连接超时，请您稍后重试"
                    self.logger.info(msg)
            else:
                msg = "请求校验结果失败,安全校验失败"
                self.logger.error(msg)
            if status:
                yield self._yield_order_request(response=response)
            else:
                yield from self.crawling_failed(username, msg)
        except Exception:
            yield from self.except_handle(username, msg)

    def _yield_order_request(self, response):
        """
        生成获取订单请求
        :param response:
        :return:
        """
        meta = response.meta

        # 通知授权成功
        self.crawling_login(username=meta["item"]["username"])

        temp_cookies = {}
        for c in response.headers.getlist('Set-Cookie', []):
            temp_cookies.update(dict(kv.strip().split("=", 1) for kv in c.decode().split(";") if "=" in kv))
        meta["cookies"] = temp_cookies
        # 获取近三个月订单
        query_order_url = "https://order.jd.com/center/list.action?search=0&d=1&s=4096"
        return Request(
            url=query_order_url,
            headers=self.headers,
            callback=self._get_order_info,
            meta=meta,
            errback=self.err_callback,
            dont_filter=True
        )
