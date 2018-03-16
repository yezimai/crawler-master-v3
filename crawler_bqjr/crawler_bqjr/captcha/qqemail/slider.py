# -*- coding: utf-8 -*-
##############################################
# pc端qq邮箱登录的滑块验证码破解
#
# 注：目前仅稳定支持chrome浏览器(包含无头)，其他浏览器未测试
##############################################

import logging
from io import BytesIO
from os import path as os_path, listdir
from random import randint, uniform
from time import sleep

from PIL import Image
from PIL import ImageChops
from requests import get as http_get
from selenium.webdriver import ActionChains


class QQEmailSlider(object):
    """
    使用示例：
    qq = QQEmailSlider(dricer, wait)
    reslut = qq.drag_slider("//*[@id='slideBkg']",
                            "//*[@id='tcaptcha_drag_thumb']",
                            "//*[@id='slideBkg']", None, True)
    """

    current_url = os_path.dirname(os_path.abspath(__file__))

    def __init__(self, driver, wait, logger=None):
        self.driver = driver
        self.wait = wait
        self.origin_xoffset = 19  # 滑块相较于图片原点(0, 0)的x轴偏移量
        self.zoom_rate = 280 / 680  # 缩放率，原始图片为680*390px，网页上为：280*158px
        self.min_sleep, self.max_sleep = 0.02, 0.1  # 拉动滑块时，最小、最大暂停时间
        self.min_xoffset, self.max_xoffset = 5, 10  # 拉动滑块时，x轴最小、最大移动距离
        self.logger = logger or logging
        self.headers = {
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Connection': 'keep-alive',
            'Host': 'ssl.captcha.qq.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
        }

    def _get_image(self, img_xpath):
        """
        根据图片的xpath路径，下载图片并返回图片的二进制
        :param img_xpath: 图片xpath路径
        :return         : success：图片的二进制  error：None
        """
        img_url = self.driver.find_element_by_xpath(img_xpath).get_attribute("src")

        cookies = self._get_cookies()
        try:
            image_data = http_get(img_url, cookies=cookies, verify=False, headers=self.headers)
        except Exception:
            self.logger.exception("下载图片出现异常:")
            return None
        else:
            return image_data.content

    def _get_cookies(self):
        """
        获取当前webdriver所有的cookie
        """
        cookies = {}
        for cookie in self.driver.get_cookies():
            cookies.update({cookie['name']: cookie['value']})
        return cookies

    def _find_similar_img(self, check_img):
        """
        在图库中找出和check_img同类型的原图
        :param check_img: 被检查的图片
        :return         : success：原图Image对象，error：None
        """
        img_library_url = self.current_url + '/img_library/'
        img_names = listdir(img_library_url)

        for name in img_names:
            img_url = img_library_url + name
            im = Image.open(img_url)

            flag = True
            error_times = 0  # 匹配错误次数
            # 检查图片x(0,50),y(0,50)坐标内的像素，若错误次数超过2000则认为不是同一类图片
            for x_ in range(50):
                for y_ in range(50):
                    r, g, b = im.getpixel((x_, y_))
                    r_, g_, b_ = check_img.getpixel((x_, y_))
                    # 像素差异在4以内，被认为是相同的
                    if abs(r - r_) > 4 or abs(g - g_) > 4 or abs(b - b_) > 4:
                        error_times += 1
                        if error_times >= 2000:
                            flag = False
                            break
                else:
                    continue
                break

            if flag:
                return im
        return None

    def _check_miss_position(self, check_img):
        """
        将传进来的图片和图库进行对比，找出不同的地方
        注：qq邮箱返回同一类图片，每次的结果都可能不一样(像素不完全一样)
        :param check_img: 被对比图片
        :return         : success：Image对象，error：None
        """
        if isinstance(check_img, BytesIO):
            check_im = Image.open(check_img)
        elif isinstance(check_img, bytes):
            check_im = Image.open(BytesIO(check_img))
        else:
            return None

        # 若没有找到对应的原始图，则直接返回
        origin_im = self._find_similar_img(check_im)
        if not origin_im:
            msg = "没有找到当前验证码图片的对应原始图片。"
            self.logger.warning(msg)
            return None

        # 找出验证码图和原始图不同的地方
        diff = ImageChops.difference(origin_im, check_im)
        if diff.getbbox() is None:
            msg = '验证码图片和原始图完全一样。'
            self.logger.warning(msg)
            return None
        else:
            return diff

    def _get_miss_px(self, im):
        """
        获取图片"缺失"(左上角)的坐标
        :param im: Image对象
        :return  : success：坐标，error：None
        """
        error_times = 0  # 匹配错误次数
        error_dic = {}  # 匹配错误记录字典：{y坐标 : 错误次数}
        im = im.convert('L')

        # 二值化后，对比每个像素点。若大于5，判定为错误，若连续错误30次，则表示找到滑块
        for x in range(680):
            for y in range(390):
                rgb = im.getpixel((x, y))
                if rgb <= 5:
                    continue

                # 记录错误y坐标和次数
                error_times += 1
                error_dic[y] = error_times
                if error_times == 1:
                    continue

                if (y - 1) not in error_dic:
                    error_times = 0
                    error_dic.clear()
                elif error_times >= 30:
                    # 截图
                    # box = (x, y - 30, x + 105, y - 30 + 105)
                    # screenshot = im.crop(box)
                    # new_im = Image.new('RGB', (680, 390), (255, 255, 255))
                    # new_im.paste(screenshot, (x, y))
                    # new_im.show()
                    return x, y - 30
        return None, None

    def _drap_slider(self, slider_xpath, xoffset):
        """
        拉动滑块
        :param slider_xpath: 滑块的xpath
        :param xoffset     : 偏移量
        :return            : None
        """
        total_length = round(self.zoom_rate * xoffset) - self.origin_xoffset

        slider = self.driver.find_element_by_xpath(slider_xpath)
        w = slider.size['width']

        ActionChains(self.driver).click_and_hold(slider).perform()

        total_x = 0  # 累积偏移量
        while True:
            xoffset = randint(self.min_xoffset, self.max_xoffset)  # 随机偏移像素
            yoffset = randint(-1, 1)
            total_x += xoffset
            if total_x > total_length:
                xoffset -= (total_x - total_length)
                total_x = total_length

            action = ActionChains(self.driver)
            action.move_to_element_with_offset(slider, xoffset + w / 2, yoffset).perform()
            # 随机暂停
            sleep(uniform(self.min_sleep, self.max_sleep))

            if total_x == total_length:
                break
        ActionChains(self.driver).release(slider).perform()

    def drag_slider(self, wait_xpath, slider_xpath, img_xpath, success_xpath=None, has_iframe=False):
        """
        拉动滑块
        :param wait_xpath   : 等待验证码元素出现的xpath
        :param slider_xpath : 滑块元素xpath
        :param img_xpath    : 验证码背景图片xpath
        :param success_xpath: 成功后元素xpath
        :param has_iframe   : 是否进入一层iframe
        :return             : success：True，error：False
        """
        try:
            # 若iframe存在，则先进入iframe
            if has_iframe:
                self.wait.until(lambda dr: dr.find_elements_by_tag_name("iframe"))
                self.driver.switch_to.frame(self.driver.find_elements_by_tag_name("iframe")[0])
            self.wait.until(lambda dr: dr.find_element_by_xpath(wait_xpath))

            # 下载图片
            img_bytes = self._get_image(img_xpath)
            if not img_bytes:
                return

            # 确定图片"缺失"位置
            diff = self._check_miss_position(img_bytes)
            if not diff:
                return

            # 获取图片"缺失"的偏移量
            xoffset, yoffset = self._get_miss_px(diff)

            # 拖动滑块
            self._drap_slider(slider_xpath, xoffset)

            # 判断验证是否成功
            if success_xpath:
                self.wait.until(lambda dr: dr.find_element_by_xpath(success_xpath))
        except Exception:
            self.logger.exception("滑块验证码破解失败，报错信息:")
            return False
        else:
            return True
