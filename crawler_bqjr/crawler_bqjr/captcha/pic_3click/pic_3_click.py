# -*- coding: utf-8 -*-

from random import uniform
from time import sleep

from requests import get as http_get
from selenium.webdriver import ActionChains


class E_3click(object):
    """
    使用示例：
    e163 = E_3click(driver)
    reslut = e163.click_3_char("//div[@class='ncpt_panel']",
                            (x1,y1),
                            (x2,y2),
                             (x3,y3))
    """

    def __init__(self, driver):
        self.driver = driver
        self.min_sleep, self.max_sleep = 0.1, 0.5

    def sleep(self):
        sleep(uniform(self.min_sleep, self.max_sleep))

    def click_3_char(self, img_xpath, xoffset1, yoffset1, xoffset2, yoffset2, xoffset3, yoffset3):
        driver = self.driver
        img_clicker = driver.find_element_by_xpath(img_xpath)

        ActionChains(driver).move_to_element_with_offset(img_clicker, xoffset1, yoffset1).perform()
        self.sleep()
        ActionChains(driver).click().perform()
        self.sleep()
        ActionChains(driver).release(img_clicker).perform()

        ActionChains(driver).move_to_element_with_offset(img_clicker, xoffset2, yoffset2).perform()
        self.sleep()
        ActionChains(driver).click().perform()
        self.sleep()
        ActionChains(driver).release(img_clicker).perform()

        ActionChains(driver).move_to_element_with_offset(img_clicker, xoffset3, yoffset3).perform()
        self.sleep()
        ActionChains(driver).click().perform()
        self.sleep()
        ActionChains(driver).release(img_clicker).perform()


if __name__ == '__main__':
    from selenium.webdriver import Chrome
    from crawler_bqjr.settings import CHROME_EXECUTABLE_PATH

    driver = Chrome(executable_path=CHROME_EXECUTABLE_PATH)
    driver.get('http://email.163.com/')
    sleep(1)
    iframe = driver.find_element_by_tag_name('iframe')
    i_x = iframe.location['x']
    i_y = iframe.location['y']
    driver.switch_to.frame(iframe)
    driver.find_element_by_name("email").send_keys('taz')
    driver.find_element_by_name("password").send_keys('1234')
    driver.execute_script("document.getElementById('dologin').click();")
    sleep(1)

    try:
        if 'errorAlert-show' in driver.find_element_by_id('errorAlert').get_attribute('class'):
            err_message = '账号或密码错误'
            print(err_message)
    except Exception:
        pass

    curr_url = driver.current_url

    # 跳转多种页面。
    if 'http://email.163.com/' == curr_url or 'errorType' in curr_url:
        # 说明未登录成功
        err_message = '账号或密码错误'
        print(err_message)

    if 'clearlimit' in curr_url:
        print('异地')
    scap = driver.find_element_by_id('ScapTcha')
    if scap:
        print('点击验证')
        s_x = driver.find_element_by_id('ScapTcha').location['x']
        s_y = driver.find_element_by_id('ScapTcha').location['y']
        driver.find_element_by_id('ScapTcha').click()
        sleep(0.5)

        img_url = driver.find_element_by_xpath('//div[@class="ncpt_pzzClick"]/img').get_attribute('src')
        r = http_get(img_url)
        with open('1.jpg', 'wb') as f:
            f.write(r.content)

        i = input()
        position = i.split(',')
        x1, y1, x2, y2, x3, y3 = position[0], position[1], position[2], position[3], position[4], position[5]
        e163 = E_3click(driver)
        e163.click_3_char('//div[@class="ncpt_pzzClick"]/img', x1, y1, x2, y2, x3, y3)

        print('ok')
