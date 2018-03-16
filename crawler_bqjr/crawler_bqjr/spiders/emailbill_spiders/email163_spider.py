# coding : utf-8

from email.utils import parseaddr
from re import compile as re_compile
from time import sleep
from urllib.parse import parse_qs, urlsplit

from scrapy.http import Request, FormRequest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC, ui

from crawler_bqjr.captcha.pic_3click.pic_3_click import E_3click
from crawler_bqjr.spider_class import HeadlessChromeWebdriverSpider
from crawler_bqjr.spiders.emailbill_spiders.base import EmailSpider
from crawler_bqjr.spiders.emailbill_spiders.email_utils import CREDIT_CARD_KEYWORD, \
    check_email_credit_card_by_address
from crawler_bqjr.spiders_settings import EMAIL_DICT
from crawler_bqjr.utils import driver_screenshot_2_bytes, get_content_by_requests, \
    get_cookies_dict_from_webdriver, get_headers_from_response


class Email163Spider(EmailSpider, HeadlessChromeWebdriverSpider):
    name = EMAIL_DICT['163.com']
    allowed_domains = ['163.com', '126.com', 'yeah.net']
    start_urls = ['http://email.163.com/']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.PAGE_PER_COUNT = 1000
        self.captcha_retry_time = 4
        self.headers = {
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'Host': 'nisp-captcha.nosdn.127.net',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36'
        }
        self.folders_pattern = re_compile(r'folders:\[(.*?)\]')
        self.folder_id_pattern = re_compile(r"'id':(\d+)")
        self.other_mail_ids_list_pattern = re_compile(r'<string>.*?:.*?</string>')

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        username = account_info["username"]
        meta = request.meta
        try:
            meta['mail_type'] = username.rsplit("@", 1)[-1]
        except Exception:
            meta['mail_type'] = "163.com"
        return request

    def parse(self, response):
        meta = response.meta
        item = meta['item']
        mail_type = meta['mail_type']
        username = item["username"]
        password = item["password"]
        url = self._start_url_
        driver = self.load_page_by_webdriver(url, '//iframe')
        try:
            if mail_type == '163.com':
                host = 'http://mail.163.com/'
                iframe = driver.find_element_by_tag_name('iframe')
            elif mail_type == '126.com':
                host = 'http://mail.126.com/'
                tab_126 = driver.find_element_by_class_name('item-126')
                tab_126.click()
                driver.implicitly_wait(1)
                iframe = driver.find_elements_by_tag_name('iframe')[1]
            elif mail_type == 'yeah.net':
                host = 'http://mail.yeah.net/'
                tab_yeah = driver.find_element_by_class_name('item-yeah')
                tab_yeah.click()
                driver.implicitly_wait(1)
                iframe = driver.find_elements_by_tag_name('iframe')[1]
            else:
                err_message = '不支持非163、126、yeah邮箱系统'
                yield from self.error_handle(username,
                                             msg="163---不支持此邮箱：(username:%s, password:%s) %s"
                                                 % (username, password, err_message),
                                             tell_msg=err_message)
                return

            driver.execute_script('''document.querySelector("a[data-style='7']").click();''')
            driver.switch_to.frame(iframe)
            self.wait_xpath(driver, "//a[@id='dologin']")
            driver.execute_script('document.getElementsByName("email")[0].value="%s";'
                                  'document.getElementsByName("password")[0].value="%s";'
                                  'document.getElementById("dologin").click();'
                                  % (username.split('@', 1)[0], password))
            driver.implicitly_wait(1)

            # 切换到表单
            try:
                if driver.find_element_by_id('ScapTcha'):
                    sleep(1)
                    validat_img = False
                    for i in range(self.captcha_retry_time):
                        img_desc = driver.find_element_by_xpath('//div[@class="ncpt_panel"]'
                                                                '/div[@class="ncpt_hint_txt"]').text
                        sleep(0.5)
                        img_url = driver.find_element_by_xpath('//div[@class="ncpt_pzzClick"]'
                                                               '/img').get_attribute('src')
                        x1, y1, x2, y2, x3, y3 = self.send_pic_get_ponint6_to_ssdb(img_url, img_desc, username)
                        driver.find_element_by_id('ScapTcha').click()
                        e163 = E_3click(driver)
                        e163.click_3_char('//div[@class="ncpt_pzzClick"]/img', x1, y1, x2, y2, x3, y3)
                        driver.execute_script("document.getElementById('dologin').click();")

                        sleep(1)
                        if "帐号或密码" in driver.find_element_by_class_name("ferrorhead").text:
                            err_message = '账号或密码错误'
                            yield from self.error_handle(username,
                                                         msg="163---登录失败：(username:%s, password:%s) %s"
                                                             % (username, password, err_message),
                                                         tell_msg=err_message)
                            return

                        if "成功" in driver.find_element_by_xpath('//div[@class="ncpt_panel"]'
                                                                '/div[@class="ncpt_hint_txt"]').text:
                            validat_img = True
                            break
                        elif "点击" in driver.find_element_by_xpath('//div[@class="ncpt_panel"]'
                                                                  '/div[@class="ncpt_hint_txt"]').text \
                                or "失败" in driver.find_element_by_xpath('//div[@class="ncpt_panel"]'
                                                                        '/div[@class="ncpt_hint_txt"]').text:
                            self.wait_xpath(driver, '//div[@class="ncpt_panel"]/div[contains(text(),"点击")]')
                        else:
                            validat_img = True
                            break

                    if not validat_img:
                        err_message = "点击验证错误四次，请重试！"
                        yield from self.error_handle(username,
                                                     msg="163---登录失败：(username:%s, password:%s) %s"
                                                         % (username, password, err_message),
                                                     tell_msg=err_message)
                        return
            except NoSuchElementException:
                pass

            try:
                if 'errorAlert-show' in driver.find_element_by_id('errorAlert').get_attribute('class'):
                    err_message = '账号或密码错误'
                    yield from self.error_handle(username,
                                                 msg="163---登录失败：(username:%s, password:%s) %s"
                                                     % (username, password, err_message),
                                                 tell_msg=err_message)
                    return
            except NoSuchElementException:
                pass

            try:
                if driver.find_element_by_name("phonecode"):
                    click_btn = driver.find_element_by_class_name('getsmscode')
                    click_btn.click()
                    sms_code = self.ask_sms_captcha(username)
                    driver.find_element_by_name("phonecode").send_keys(sms_code)
                    driver.find_element_by_class_name("u-loginbtn").click()
                    sleep(1)
            except NoSuchElementException:
                pass

            curr_url = driver.current_url
            # self.logger.debug('++++\ncurrent_url :{0}\n+++++'.format(curr_url))
            # 跳转多种页面。
            if url == curr_url or 'errorType' in curr_url:
                # 说明未登录成功
                err_message = '账号或密码错误'
                yield from self.error_handle(username,
                                             msg="163---登录失败：(username:%s, password:%s) %s"
                                                 % (username, password, err_message),
                                             tell_msg=err_message)
                return

            if 'clearlimit' in curr_url:
                # 说明未登录成功跳转到检查网站
                phone = self.ask_extra_captcha(username)
                # self.logger.debug('输入电话:{0}'.format(phone))
                driver.execute_script("document.getElementById('password').value='{0}';"
                                      "document.getElementById('mobile').value='{1}';".format(password, phone))
                driver.find_element_by_class_name('yzm_btn').click()
                driver.implicitly_wait(0.5)
                try:
                    if driver.find_element_by_id('dg-usercheckcode').is_displayed():
                        # cookies = get_cookies_dict_from_webdriver(driver)
                        # self.logger.debug('cookies:{0}'.format(cookies))
                        # headers = {
                        #     'Accept': '*/*',
                        #     'Accept-Encoding': 'gzip, deflate',
                        #     'Accept-Language': 'zh-CN,zh;q=0.9',
                        #     'Connection': 'keep-alive',
                        #     'Host': 'reg.163.com',
                        #     'Referer': 'http://reg.163.com/clearlimit/check.jsp?username={0}'
                        #                '&url=http%3A%2F%2Fentry.mail.163.com%2Fcoremail%2Ffcg%2Fntesdoor2'
                        #                '%3Fdf%3Dwebmail163%26from%3Dweb%26style%3D-1%26product%3Dmail163'
                        #                '%26uid%3D{1}'.format(username, url_parse.quote(username)),
                        #     'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.75 Safari/537.36',
                        #     'X-Requested-With': 'XMLHttpRequest',
                        # }
                        # get_id = get_content_by_requests('http://reg.163.com/services/getid',headers=headers,cookie_jar=cookies).decode()
                        # self.logger.debug('get_id:{0}'.format(get_id))
                        # capcha_body = get_content_by_requests('http://reg.163.com/services/getimg?v={0}&num=6&type=2&id={1}'.format(get_js_time(),get_id),cookie_jar=cookies,headers=headers)
                        # self.logger.debug('capcha_body:{0}'.format(capcha_body))
                        wait = ui.WebDriverWait(driver, 20)
                        validation_img = wait.until(EC.visibility_of_element_located((By.ID, 'dg-checkCode')))
                        left = validation_img.location['x']
                        top = validation_img.location['y']
                        right = validation_img.location['x'] + validation_img.size['width']
                        bottom = validation_img.location['y'] + validation_img.size['height']

                        photo_base64 = driver.get_screenshot_as_base64()
                        capcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                        captcha_code = self.ask_image_captcha(capcha_body, username)
                        driver.find_element_by_id('dg-usercheckcode').send_keys(captcha_code)
                        driver.find_element_by_class_name('iDialogBtn').click()
                        driver.implicitly_wait(0.5)
                        try:
                            # self.logger.debug('err?:{0}'.format(driver.find_element_by_id('dg-err')
                            #                                     .get_attribute('class')))
                            if 'err' in driver.find_element_by_id('dg-err').get_attribute('class'):
                                yield from self.error_handle(username, msg="验证码输入错误",
                                                             tell_msg="验证码输入错误")
                                return
                            # self.logger.debug('p {0}'.format(driver.find_element_by_tag_name('p')))
                            if driver.find_element_by_tag_name('p'):
                                yield from self.error_handle(username, msg=driver.find_element_by_tag_name('p').text,
                                                             tell_msg=driver.find_element_by_tag_name('p').text)
                                return
                        except Exception:
                            alert = driver.switch_to.alert
                            self.logger.debug("Alert:%s" % alert.text)
                            if '请查收' not in alert.text:
                                yield from self.error_handle(username, msg=alert.text,
                                                             tell_msg=alert.text)
                                return
                            alert.accept()
                            driver.switch_to.default_content()
                except Exception:
                    pass
                # driver.get_screenshot_as_file("/logs/phone.jpg")
                sms_code = self.ask_sms_captcha(username)
                # self.logger.debug('输入验证码:{0}'.format(sms_code))
                # self.logger.debug('page_source:{0}'.format(driver.page_source))
                driver.find_element_by_id('mobcheckcode').send_keys(sms_code)
                # driver.execute_script("document.getElementById('mobcheckcode').value='{0}';".format(sms_code))
                driver.find_element_by_id('loginBtn').click()
                driver.implicitly_wait(2)
                if len(driver.find_element_by_id('eHint').text) > 6:
                    yield from self.error_handle(username, msg=driver.find_element_by_id('eHint').text,
                                                 tell_msg=driver.find_element_by_id('eHint').text)
                    return
                # driver.get_screenshot_as_file("/logs/sms.jpg")
                driver.implicitly_wait(1)

            folder_str = self.folders_pattern.search(driver.page_source)
            if not folder_str:
                yield from self.error_handle(username, msg="没有文件夹",
                                             tell_msg="出现未知异常")
                return
            else:
                folder_str = folder_str.group(1)

            folder_list = self.folder_id_pattern.findall(folder_str)
            folder_list.remove('2')  # 草稿箱
            folder_list.remove('3')  # 已发送
            folder_list.remove('6')  # 病毒邮件
            folder_str = ''.join('<int>' + str(x) + '</int>' for x in folder_list)

            # self.logger.debug('driver_current_url: %s' % driver.current_url)
            # sid = driver.current_url.split('?', 1)[-1].split('&', 1)[0]
            sid = parse_qs(urlsplit(driver.current_url).query)["sid"][0]
            headers = {
                'Connection': 'keep-alive',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'zh-CN,zh;q=0.8',
                'Content-type': 'application/x-www-form-urlencoded',
                'Host': 'mail.%s' % mail_type,
                'Origin': 'http://mail.%s' % mail_type,
                'Referer': 'http://mail.%s/js6/main.jsp?sid=%s&df=mail163_letter' % (mail_type, sid),
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3050.3 Safari/537.36',
            }
            meta['sid'] = sid
            meta['host'] = host
            cookie = driver.get_cookies()

            # meta['folder_str'] = folder_str
            # mbox_url =  '{0}js6/main.jsp?sid={1}&df=mail{2}_letter#module=mbox.ListModule' \
            #             '%7C%7B%22fid%22%3A1%2C%22order%22%3A%22date%22%2C%22' \
            #             'desc%22%3Atrue%7D'.format(host, sid, mail_type[mail_type.index(".")])
            # yield Request(url=mbox_url,
            #               headers=headers,
            #               cookies=cookie,
            #               meta=meta,
            #               callback=self.parse_mbox,
            #               dont_filter=True,
            #               errback=self.err_callback)

            search_url = host + 'js6/s?sid=' + sid + '&func=mbox:searchMessages'
            data = {
                'var': '<?xml version="1.0"?><object><array name="conditions"><object>'
                       '<array name="conditions"><object><string name="field">subject</string>'
                       '<string name="operator">contains</string><string name="operand">{0}</string>'
                       '<boolean name="ignoreCase">true</boolean></object></array><string name="operator">or'
                       '</string></object></array><int name="windowSize">{1}</int><string name="order">date'
                       '</string><boolean name="desc">true</boolean><boolean name="returnTag">true</boolean>'
                       '<boolean name="recursive">true</boolean><array name="fids">{2}</array>'
                       '</object>'.format(CREDIT_CARD_KEYWORD, self.PAGE_PER_COUNT, folder_str),
            }
            yield FormRequest(url=search_url, callback=self.parse_search, formdata=data, meta=meta,
                              headers=headers, cookies=cookie, dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(username, msg="邮箱登录异常", tell_msg="邮箱登录异常")
        finally:
            driver.quit()

    def parse_search(self, response):
        meta = response.meta
        item = meta["item"]
        try:
            host = meta['host']
            mail_list = meta.setdefault("mail_list", [])
            ids = response.xpath('//string[@name="id"]/text()').extract()
            address_list = (parseaddr(address)[1] for address in
                            response.xpath('//string[@name="from"]/text()').extract())
            text_url = host + 'js6/read/readhtml.jsp?mid=%s&font=15&color=064977'  # 最终详情页面信息
            for i, (subject, address) in enumerate(zip(response.xpath('//string[@name="subject"]/text()').extract(),
                                                       address_list)):
                bankname = check_email_credit_card_by_address(subject, address)
                if bankname:
                    mail_list.append((text_url % ids[i], bankname, subject))

            other_mail_ids_list = self.other_mail_ids_list_pattern.findall(response.text)
            if other_mail_ids_list and len(mail_list) == self.PAGE_PER_COUNT:
                page_num = meta.setdefault("page_num", 1)
                search_url = host + 'js6/s?sid={0}&func=mbox:getMessageInfos' \
                                    '&mbox_pager_next={1}'.format(meta['sid'], page_num)
                meta['page_num'] += 1

                other_mail_ids_str = ''.join(other_mail_ids_list)
                data = {'var': '<?xml version="1.0"?><object><array name="ids">{0}</array>'
                               '<int name="windowSize">{1}</int><boolean name="returnTag">true'
                               '</boolean></object>'.format(other_mail_ids_str, self.PAGE_PER_COUNT)
                        }
                yield FormRequest(url=search_url, callback=self.parse_search, formdata=data,
                                  meta=meta, dont_filter=True, errback=self.err_callback)
            else:
                if not mail_list:
                    yield from self.crawling_done(meta['item'])
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
            yield from self.except_handle(meta["item"]["username"], msg="查找账单异常",
                                          tell_msg="查找账单异常")

    def parse_detail(self, response):
        meta = response.meta
        item = meta['item']
        try:
            bill_record = self.get_bill_record(meta['bankname'], meta['subject'], response.text)
            bill_records = item['bill_records']
            bill_records.append(bill_record)
            if len(bill_records) == meta['count']:
                yield from self.crawling_done(item)
        except Exception:
            yield item
            yield from self.except_handle(item['username'], msg="账单解析异常", tell_msg="账单解析异常")

    def send_pic_get_ponint6_to_ssdb(self, img_url, img_desc, username):
        captcha_body = get_content_by_requests(img_url, self.headers)
        captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".jpeg", image_describe=img_desc)
        code = captcha_code.split(',')
        return code[0], code[1], code[2], code[3], code[4], code[5]

    def parse_mbox(self, response):
        meta = response.meta
        try:
            search_url = meta['host'] + 'js6/s?sid=' + meta['sid'] + '&func=mbox:searchMessages'
            data = {
                'var': '<?xml version="1.0"?><object><string name="pattern">' + CREDIT_CARD_KEYWORD
                       + '</string><boolean name="fts.ext">true</boolean><string name="fts.fields">'
                         'from,to,subj,cont,aname</string><object name="groupings">'
                         '<string name="fromAddress"></string><string name="fid"></string>'
                         '<string name="sentDate"></string><string name="flags.attached"></string>'
                         '<string name="flags.read"></string></object><string name="order">date</string>'
                         '<boolean name="desc">true</boolean><array name="fids">{0}</array>'
                         '<int name="windowSize">{1}</int><boolean name="returnTag">true</boolean>'
                         '</object>'.format(meta['folder_str'], self.PAGE_PER_COUNT)
            }
            yield FormRequest(url=search_url, callback=self.parse_search, formdata=data,
                              meta=meta, dont_filter=True, errback=self.err_callback)
        except Exception:
            yield from self.except_handle(meta["item"]["username"], msg="解析文件夹异常",
                                          tell_msg="邮箱登录失败，请刷新页面重试")
