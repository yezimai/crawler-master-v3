# coding: utf-8

from datetime import datetime
from io import BytesIO
from re import compile as re_compile
from string import digits
from time import sleep
from urllib.parse import quote

from PIL import Image
from piltesseract import get_text_from_image
from scrapy.http import Request, FormRequest
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.web.client import ResponseNeverReceived

from crawler_bqjr.items.shixin_items import ShixinDetailItem
from crawler_bqjr.spiders.shixin_spiders.base import TwoWordsNameSearchSpider
from crawler_bqjr.spiders.shixin_spiders.shixin_baidu import SSDB_SHIXIN_ID_HSET_NAME
from crawler_bqjr.utils import get_js_time
from global_utils import json_loads

SSDB_DLM_NAME_HSET_NAME = "spider_dlm_name_hset"


class ShixinDLMSpider(TwoWordsNameSearchSpider):
    name = 'dlm'
    allowed_domains = ["dailianmeng.com"]
    start_urls = ['http://www.dailianmeng.com']

    custom_settings = {
        'DOWNLOAD_DELAY': 0.4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, ssdb_hset_for_record=SSDB_DLM_NAME_HSET_NAME, **kwargs)

        self.start_url = self.start_urls[0]
        self.captcha_url = 'http://www.dailianmeng.com/xinyong/captcha.html' \
                           '?refresh=1&_=%s' % get_js_time()
        self.data = {
            'SearchForm[verifyCode]': '',
            'yt0': '',
        }
        self.headers = {
            'Referer': '',  # %E7%8E%8B%E6%9E%97
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
        }
        self.numbers_pattern = re_compile(r'\((\d+)\)')
        self.link_id_pattern = re_compile(r"/(\w+?).html$")
        self.from_web = "2"

    def start_requests(self):
        yield Request(url=self.start_url, headers=self.headers, callback=self.parse, dont_filter=True,
                      errback=self.err_callback)

    def parse(self, response):
        search_word = self.get_next_search_word()
        if not search_word:
            self.logger.info('姓名已经抓取完成!')
            return
        else:
            url = 'http://www.dailianmeng.com/xinyong/q/%s.html' % quote(search_word)
            self.headers['Referer'] = url
            yield Request(url=self.captcha_url, headers=self.headers,
                          callback=self.parse_vcode_url, dont_filter=True, errback=self.err_callback)

    def parse_vcode_url(self, response):
        try:
            # 得到验证码请求
            json_url = json_loads(response.body)['url']
            yield Request(url=self.start_url + json_url, headers=self.headers,
                          callback=self.parse_vcode, dont_filter=True, errback=self.err_callback)
        except Exception:
            self.logger.error("贷款盟---得到验证码请求访问失败!")
            url = self.headers.get('Referer', '')
            if url:
                yield Request(url=url, headers=self.headers, callback=self.parse, dont_filter=True,
                              errback=self.err_callback)

    def parse_vcode(self, response):
        url = self.headers.get('Referer', '')
        # 得到验证,存储验证码
        try:
            captcha_code = self.img2str(response.body)
            self.data['SearchForm[verifyCode]'] = captcha_code
            yield FormRequest(url=url, formdata=self.data, headers=self.headers,
                              callback=self.parse_detail, dont_filter=True, errback=self.err_callback)
        except Exception:
            self.logger.error("贷款盟---验证码请求访问失败!")
            url = self.headers.get('Referer', '')
            if url:
                yield Request(url=url, headers=self.headers, callback=self.parse, dont_filter=True,
                              errback=self.err_callback)

    def parse_detail(self, response):
        try:
            trs = response.xpath('//table/tbody/tr')
            if not trs:
                # 如果未匹配到里面内容, 则说明 未找到用户相关信息, 执行下一页跳转
                error = []
                try:
                    error = response.xpath('//label[@class="col-sm-3 control-label error"]/text()')
                except Exception:
                    self.logger.error("贷款盟---验证码请求访问失败! ,当前url:%s" % response.url)

                if not error:
                    yield Request(url=self.captcha_url, headers=self.headers, callback=self.parse_vcode_url,
                                  dont_filter=True, errback=self.err_callback)
                else:
                    search_word = self.get_next_search_word()
                    if not search_word:
                        self.logger.info('姓名已经抓取完成!')
                        return
                    else:
                        # 这里为手动构造数据, 上线时候可稍作修改
                        url = 'http://www.dailianmeng.com/xinyong/q/%s.html' % quote(search_word)
                        self.headers['Referer'] = url
                        yield Request(url=url, headers=self.headers, callback=self.parse_detail, dont_filter=True,
                                      errback=self.err_callback)
            else:
                urljoin = response.urljoin
                from_web = self.from_web
                link_id_pattern = self.link_id_pattern
                update_time = datetime.now()
                for tr in trs:
                    name = tr.xpath('td[2]/text()').extract_first("")
                    if "*" in name:
                        continue

                    url = tr.xpath('td[8]/a/@href').extract_first("")
                    try:
                        link_id = link_id_pattern.search(url).group(1)
                    except Exception:
                        continue

                    link_name = from_web + "_" + link_id
                    if self.ssdb_conn.hexists(SSDB_SHIXIN_ID_HSET_NAME, link_name):
                        continue
                    self.ssdb_conn.hset(SSDB_SHIXIN_ID_HSET_NAME, link_name, "")

                    item = ShixinDetailItem()
                    item["from_web"] = from_web
                    item["link_id"] = link_id
                    item['update_time'] = update_time
                    item['name'] = name

                    yield Request(urljoin(url), headers=self.headers, meta={'item': item},
                                  callback=self.parse_cont, dont_filter=True, errback=self.err_callback)

                # 执行完成后 返回下一个姓名继续执行 ,直到生成器 遍历完成为止
                search_word = self.get_next_search_word()
                if not search_word:
                    self.logger.info('姓名已经抓取完成!')
                    return
                else:
                    url = 'http://www.dailianmeng.com/xinyong/q/%s.html' % quote(search_word)
                    self.headers['Referer'] = url
                    yield FormRequest(url=url, formdata=self.data, headers=self.headers,
                                      callback=self.parse_detail, dont_filter=True, errback=self.err_callback)
        except Exception:
            url = self.headers.get('Referer', '')
            yield Request(url=url, headers=self.headers, callback=self.parse_vcode_url, dont_filter=True,
                          errback=self.err_callback)

    def parse_cont(self, response):
        item = response.meta['item']
        try:
            info_dict = {tr.xpath('th/text()').extract_first(): tr.xpath('td/text()').extract_first()
                         for tr in response.xpath('//table/tr')}
            item["id"] = info_dict["身份证号/组织机构代码"]
            item["name"] = info_dict.get("被执行人姓名/名称", item["name"])
            item["province"] = info_dict.get("省份")
            item["file_code"] = info_dict.get("案号")
            item["execution_court"] = info_dict.get("执行法院")
            item["execution_file_code"] = info_dict.get("执行依据文号")
            item["fulfill_situation"] = info_dict.get("失信被执行人行为情形")
            item["duty"] = info_dict.get("生效法律文书确定的义务")
            item["adjudge_court"] = info_dict.get("做出执行依据单位")
            item["fulfill_status"] = info_dict.get("被执行人的履行情况")
            item["publish_date"] = info_dict.get("发布时间")
            item["on_file_date"] = info_dict.get("立案时间")
            item["legal_person"] = info_dict.get("法定代表人或者负责人")
            item["age"] = info_dict.get("年龄")
            item["sex"] = info_dict.get("性别")

            yield item
        except Exception:
            self.logger.error("贷款盟---个人详情页面返回失败! url:%s" % response.url)

    def err_callback(self, failure):
        if failure.check(HttpError) and failure.value.response.status == 500:
            # these exceptions come from HttpError spider middleware
            # you can get the non-200 response
            return  # 有时会出现500错误，所以忽略

        self.logger.warning(repr(failure))

        if hasattr(failure, "type") and failure.type is ResponseNeverReceived:  # 被封锁了
            self.logger.warning("连接被重置")
            sleep(60 * 10)
        if '10061' in str(failure.value):  # 有时候访问可能被拒绝. 需等待提交
            self.logger.warning("访问连接被拒绝")
            sleep(60 * 10)
        try:
            return failure.request
        except Exception:
            self.logger.exception("err_callback except")
            search_word = self.get_next_search_word()
            if search_word:
                url = self.headers.get('Referer', '')
                if not url:
                    return [FormRequest(url=url, formdata=self.data, headers=self.headers,
                                        callback=self.parse_detail, dont_filter=True)]

    def img2str(self, captcha_body):
        with BytesIO(captcha_body) as captcha_filelike, Image.open(captcha_filelike) as img:
            new_img = img.convert('L')  # 转换为RGBA

            # pix = new_img.load()  # 转换为像素
            # # 处理上下黑边框，size[0]即图片长度
            # for x in range(new_img.size[0]):
            #     pix[x, 0] = pix[x, new_img.size[1] - 1] = 255

            # # 处理左右黑边框，size[1]即图片高度
            # for y in range(new_img.size[1]):
            #     pix[0, y] = pix[new_img.size[0] - 1, y] = 255

            # 二值化处理，这个阈值为201比较合适
            threshold = 201  # 阈值  # 201
            table = []
            for i in range(256):
                if i < threshold:
                    table.append(0)
                else:
                    table.append(1)

            new_img = new_img.point(table, '1')

            # 识别图片上的值
            text = get_text_from_image(new_img, psm=7, tessedit_char_whitelist=digits).replace(' ', '')

            new_img.close()

            return text
