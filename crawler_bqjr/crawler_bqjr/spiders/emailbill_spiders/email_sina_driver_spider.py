# -*- coding:utf-8 -*-

from time import sleep

from crawler_bqjr.spider_class import PhantomJSWebdriverSpider
from crawler_bqjr.spiders.emailbill_spiders.email_sina_scrapy_spider import EmailSinaSpider


class EmailSinaDriverSpider(EmailSinaSpider, PhantomJSWebdriverSpider):
    def parse(self, response):
        meta = response.meta
        item = meta['item']
        username = item["username"]

        url = self._start_url_
        driver = self.load_page_by_webdriver(url, '//div[@class="loginBox"]')
        # 开始登录
        try:
            password = item["password"]
            driver.find_element_by_id("freename").send_keys(username)
            driver.find_element_by_id("freepassword").send_keys(password)
            driver.execute_script("document.getElementsByClassName('loginBtn')[0].click();")

            sleep(1.5)
            curr_url = driver.current_url
            if url == curr_url or url + '#' == curr_url:
                # 说明未登录成功
                err_message = '账号或密码错误'
                yield from self.error_handle(username,
                                             msg="sina---登录失败：(username:%s, password:%s) %s"
                                                 % (username, password, err_message),
                                             tell_msg=err_message)
                return

            cooikies = driver.get_cookies()
            request = self.get_search_email_request(response, cooikies)
            request.meta["cookie"] = cooikies
            yield request
        except Exception:
            yield from self.except_handle(username, msg="sina---email未知异常",
                                          tell_msg="出现未知异常")
            return
        finally:
            driver.delete_all_cookies()
            driver.quit()
