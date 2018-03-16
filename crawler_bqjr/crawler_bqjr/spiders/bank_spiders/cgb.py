# -*- coding: utf-8 -*-

from datetime import date
from time import sleep

from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import ui

from crawler_bqjr.ddxoft.dd_operator import Ddxoft
from crawler_bqjr.spider_class import WebBrowserSpider, CaptchaTimeout
from crawler_bqjr.spiders.bank_spiders.base import BankSpider
from crawler_bqjr.utils import driver_screenshot_2_bytes


#################################################
# 广发银行爬虫
#################################################
class CGBSpider(WebBrowserSpider, BankSpider):
    name = "bank_cgb"
    allowed_domains = ["cgbhina.com"]
    start_urls = ["https://ebanks.cgbchina.com.cn/perbank/"]

    def get_theday_3_month_ago(self, now=None):
        return (now or date.today()) - relativedelta(months=+3)

    def parse(self, response):
        item = response.meta["item"]
        username = item["username"]

        driver = self.getdriver(executable_path=self.settings["IE_EXECUTABLE_233_PATH"], browser_type="IE")
        try:
            wait = ui.WebDriverWait(driver, 20)
            driver.get(response.url)
            wait.until(lambda dr: dr.find_element_by_id("loginId"))
            driver.maximize_window()

            pid = driver.iedriver.process.pid
            with Ddxoft(pid) as visual_keyboard:
                driver.execute_script('user_input=document.getElementById("loginId");'
                                      'user_input.focus();'
                                      'user_input.value="' + username + '";')
                visual_keyboard.dd_tab()
                sleep(0.1)
                for key in item["password"]:
                    visual_keyboard.dd_keyboard(key)
                    sleep(0.1)

            # 检查是否需要输入验证码
            captcha_input = driver.find_element_by_id("captcha")
            if captcha_input and captcha_input.is_displayed():
                captcha_image = driver.find_element_by_id("verifyImg")
                location = captcha_image.location
                size = captcha_image.size
                left = location["x"] - 5
                top = location["y"]
                right = left + size["width"]
                bottom = top + size["height"]

                photo_base64 = driver.get_screenshot_as_base64()
                captcha_body = driver_screenshot_2_bytes(photo_base64, (left, top, right, bottom))
                captcha_code = self.ask_image_captcha(captcha_body, username, file_type=".png")
                captcha_input.send_keys(captcha_code)
                driver.execute_script('document.getElementById("captcha").value="'
                                      + captcha_code + '";')

            driver.execute_script('document.getElementById("loginButton").click();')
            wait.until(lambda dr: dr.find_element_by_id("_b01").is_displayed())
            driver.execute_script('document.getElementById("_b01").children[1].style.display="block";'
                                  'document.getElementById("_b01").children[1].style.left="-49px";')

            sleep(5)
            # with open("webpage.html", "w", encoding="utf-8") as file
            #     file.write(driver.page_source)
            # 跳转到银行流水界面
            trade_detail_btn = driver.find_element_by_xpath("//a[contains(text(),'交易明细')]")
            if trade_detail_btn:
                trade_detail_btn.click()

                wait.until(lambda dr: dr.find_element_by_id("windowContainer").is_displayed())
                driver.switch_to.frame(driver.find_element_by_id("windowContainer").find_element_by_xpath("//iframe"))
                start_date_input = driver.find_element_by_id("beginDate")
                end_date_input = driver.find_element_by_id("endDate")
                submit_input = driver.find_element_by_id("advancedQueryTable")\
                    .find_element_by_xpath("//a[contains(text(),'查询')]")
                end_date = date.today()

                trade_detail = []
                for i in range(4):
                    start_date = self.get_theday_3_month_ago(end_date)
                    try:
                        start_date_input.clear()
                        start_date_input.send_keys(start_date.strftime("%Y-%m-%d"))
                        end_date_input.clear()
                        end_date_input.send_keys(end_date.strftime("%Y-%m-%d"))
                        submit_input.click()
                        wait.until(lambda dr: dr.find_element_by_id("advancedQueryTable").is_displayed())
                        trade_detail.extend(self.parse_item_from_webpage(driver, wait, item))
                    except Exception:
                        pass
                    end_date = start_date

                item["trade_records"] = trade_detail
                yield from self.crawling_done(item)
            else:
                yield from self.error_handle(username, msg="广发银行---错误信息：在页面中找不到[交易明细]按钮",
                                             tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        except CaptchaTimeout:
            yield from self.error_handle(username, "广发银行---等待验证码超时",
                                         tell_msg="等待验证码超时，请刷新页面重试。。")
        except Exception:
            yield from self.except_handle(username, msg="广发银行---错误信息：",
                                          tell_msg="银行流水数据爬取失败，请刷新页面重试!")
        finally:
            driver.quit()

    #######################################################
    # 从银行流水页面解析出item
    #######################################################
    def parse_item_from_webpage(self, driver, wait, item):
        trade_detail = []
        while True:
            wait.until(lambda dr: dr.find_element_by_xpath("//tbody[@id='resultTableBody']"))
            data_list = driver.find_elements_by_xpath("//tbody[@id='resultTableBody']/tr")
            if data_list:
                for data_item in data_list:
                    try:
                        temp_item = {}
                        # 交易日期
                        trade_date = data_item.find_element_by_xpath("td[1]").text
                        temp_item["trade_date"] = trade_date
                        # 交易渠道
                        trade_channel = data_item.find_element_by_xpath("td[2]").text
                        temp_item["trade_channel"] = trade_channel
                        # 交易币种
                        trade_currency = data_item.find_element_by_xpath("td[3]").text
                        temp_item["trade_currency"] = trade_currency
                        # 收入
                        trade_income = data_item.find_element_by_xpath("td[4]").text
                        temp_item["trade_income"] = trade_income
                        # 支出
                        trade_outcome = data_item.find_element_by_xpath("td[5]").text
                        temp_item["trade_outcome"] = trade_outcome
                        # 账户余额
                        trade_balance = data_item.find_element_by_xpath("td[6]").text
                        temp_item["trade_balance"] = trade_balance
                        # 交易接收方姓名
                        trade_acceptor_name = data_item.find_element_by_xpath("td[7]").text
                        temp_item["trade_acceptor_name"] = trade_acceptor_name
                        # 交易接收方账号
                        trade_acceptor_account = data_item.find_element_by_xpath("td[8]").text
                        temp_item["trade_acceptor_account"] = trade_acceptor_account
                        # 交易摘要
                        trade_remark = data_item.find_element_by_xpath("td[9]").text
                        temp_item["trade_remark"] = trade_remark

                        temp_item["trade_amount"] = trade_income or ("-" + trade_outcome)
                        trade_detail.append(temp_item)
                    except Exception:
                        self.except_handle(item["username"], msg="解析交易详情数据出错：")

            try:
                next_page_input = driver.find_element_by_xpath("//div[@id='printContent']"
                                                               "//div[@class='turnpage']"
                                                               "//div[@class='nextPage']")
                next_page_input.click()
                wait.until(lambda dr: dr.find_element_by_id("resultTableBody").is_displayed())
            except NoSuchElementException:
                return trade_detail
