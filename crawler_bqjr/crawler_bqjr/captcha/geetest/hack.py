# -*- coding:utf-8 -*-
#####################################################
# 极验验证码破解API
#
#####################################################

import logging
from enum import Enum
from io import BytesIO
from random import random, randint
from re import compile as re_compile
from time import sleep

from PIL import Image
from requests import get as http_get
from selenium.webdriver import ActionChains


######################################################
# 浏览器类型
######################################################
class DRIVER_TYPE(Enum):
    CHROME = 1
    FIREFOX = 2
    IE = 3
    PHANTOMJS = 4


class GeetestHack(object):
    def __init__(self, driver, wait, logger=None):
        self.driver = driver
        self.wait = wait
        self.logger = logger or logging
        self.pattern = re_compile(r'background-image: url\("(.*)"\); background-position: (.*)px (.*)px;')

    #################################################################
    # @description  合并图片
    #               极验验证码采用的模式是将一整张图片拆分成很多slice片段
    #               然后使用div的background-image css属性配合不同的background-position
    #               重组这些片段形成验证码图片
    # @param  filename      文件名
    #         location_list 多个位置坐标组成的链表
    # @return 获取合成后的图片
    #################################################################
    def __get_merge_image__(self, filename, location_list):
        with Image.open(filename) as im:
            im_list_upper = []
            im_list_down = []

            for location in location_list:
                if location['y'] == -58:
                    im_list_upper.append(im.crop((abs(location['x']), 58,
                                                  abs(location['x']) + 10, 166)))
                if location['y'] == 0:
                    im_list_down.append(im.crop((abs(location['x']), 0,
                                                 abs(location['x']) + 10, 58)))

            new_im = Image.new('RGB', (260, 116))
            x_offset = 0
            for i in im_list_upper:
                new_im.paste(i, (x_offset, 0))
                x_offset += i.size[0]
                i.close()

            x_offset = 0
            for i in im_list_down:
                new_im.paste(i, (x_offset, 58))
                x_offset += i.size[0]
                i.close()

            del im_list_upper
            del im_list_down
            return new_im

    #################################################################
    # @description 从slice（图像片段）的容器div中获取所有slice（片段）
    #              及其坐标（background-position）
    # @param  driver        webdriver对象
    #         location_list 多个位置坐标组成的链表
    # @return 获取重新合成的图片
    #################################################################
    def __get_image__(self, div):
        # 找到图片所在的div
        background_images = self.driver.find_elements_by_xpath(div)

        location_list = []

        imageurl = ''
        pattern = self.pattern
        for background_image in background_images:
            location = {}
            # 在html里面解析出小图片的url地址，还有长高的数值
            info = pattern.search(background_image.get_attribute('style')).groups()
            imageurl = info[0]
            location['x'] = int(info[1])
            location['y'] = int(info[2])
            location_list.append(location)
        imageurl = imageurl.replace("webp", "jpg")
        with BytesIO(http_get(imageurl).content) as jpgfile:
            return self.__get_merge_image__(jpgfile, location_list)  # 重新合并图片

    #################################################################
    # @description:对比两个坐标上的rgb值
    # @param: img1  webdriver对象
    #         img2  多个位置坐标组成的链表
    #         x     横坐标
    #         y     纵坐标
    # @return 两张图片上对应的两个点是否一样
    #################################################################
    def __comparation_between_pixels__(self, img1, img2, x, y):
        pixel1 = img1.getpixel((x, y))
        pixel2 = img2.getpixel((x, y))

        for i in range(3):
            if abs(pixel1[i] - pixel2[i]) >= 50:
                return False
        return True

    #################################################################
    # @description:计算验证码缺口的位置
    #              对比两张图片中的每个像素点的rgb值
    # @param: img1  图片一
    #         img2  图片二
    # @return 两张图片上对应的两个点是否一样
    #################################################################
    def __get_diff_location__(self, img1, img2):
        for i in range(260):
            for j in range(116):
                if not self.__comparation_between_pixels__(img1, img2, i, j):
                    return i
        return 0

    #################################################################
    # @description:获取移动的轨迹
    #              采用随机方式模拟滑动滑块到缺口的过程
    # @param: slider_pos_x  滑块的X轴坐标
    # @return 生成一系列将要滑动到的点的X坐标
    #################################################################
    def __get_track__(self, slider_pos_x):
        pox_x_list = []
        slider_pos_x = slider_pos_x - 5
        # 间隔通过随机范围函数来获得
        random_x = 1
        half_x = int(slider_pos_x / 2)
        # 循环次数
        cycle_count = 0
        fz = randint(3, 6)
        while slider_pos_x > 0:
            slider_pos_x -= random_x
            pox_x_list.append(random_x)
            if cycle_count > fz:
                cycle_count = 0
                fz = randint(3, 6)
                if slider_pos_x < half_x:
                    random_x = random_x - 1 if random_x > 1 else 1
                else:
                    random_x += 1
            cycle_count += 1
        pox_x_list.append(int(slider_pos_x))

        return pox_x_list

    #################################################################
    # @description:获取移动的轨迹
    #              采用随机方式模拟滑动滑块到缺口的过程
    # @param:
    #         driver  webdriver对象，driver中已加载了带有极验验证码的网页
    #         successed_element_selector 验证码通过后才会出现的DOM元素
    # @return 生成一系列将要滑动到的点的X坐标
    #################################################################
    def drag_and_move_slider(self, img1_c_selector, img2_c_selector, img1_selector,
                             img2_selector, slider_selector, successed_element_selector):
        try:
            # 等待页面的上元素刷新出来
            self.wait.until(lambda d: d.find_element_by_xpath(img1_c_selector).is_displayed())
            self.wait.until(lambda d: d.find_element_by_xpath(img2_c_selector).is_displayed())
            # with open("web.html", "w", encoding='utf-8') as file:
            #     file.write(self.driver.page_source)

            # 下载图片
            image1 = self.__get_image__(img1_selector)
            image2 = self.__get_image__(img2_selector)
            # 计算缺口位置
            loc = self.__get_diff_location__(image1, image2)
            # 生成x的移动轨迹点
            track_list = self.__get_track__(loc)
            # 找到滑动的圆球
            self.wait.until(lambda d: d.find_element_by_xpath(slider_selector).is_displayed())
            element = self.driver.find_element_by_xpath(slider_selector)
            location = element.location
            # 获得滑动圆球的高度
            y = location['y']

            # 鼠标点击元素并按住不放
            ActionChains(self.driver).click_and_hold(on_element=element).perform()

            track_string = ""
            cycle_count = 0
            y_tmp = 0
            is_reversed = False

            def get_y_offset(source, reverse=False):
                if source == 9 or reverse:
                    return True, source + randint(-1, 0)
                else:
                    return False, source + randint(0, 1)

            for track in track_list:
                track_string = track_string + "{%f,%d}," % (track, y - 364)
                # xoffset=track+22:这里的移动位置的值是相对于滑动圆球左上角的相对值，而轨迹变量里的是圆球的中心点，所以要加上圆球长度的一半。
                # yoffset=y-445:这里也是一样的。不过要注意的是不同的浏览器渲染出来的结果是不一样的，要保证最终的计算后的值是22，也就是圆球高度的一半
                is_reversed, y_tmp = get_y_offset(y_tmp, is_reversed)
                ActionChains(self.driver).move_to_element_with_offset(to_element=element, xoffset=track + 22,
                                                                      yoffset=y - 364 - y_tmp).perform()
                # 间隔时间也通过随机函数来获得
                if cycle_count > 2:
                    sleep(random() / 100.0)
                cycle_count = cycle_count + 1

            # xoffset=21，本质就是向后退一格。这里退了5格是因为圆球的位置和滑动条的左边缘有5格的距离
            ActionChains(self.driver).move_to_element_with_offset(to_element=element, xoffset=20,
                                                                  yoffset=y - 364).perform()
            # 释放鼠标
            ActionChains(self.driver).release(on_element=element).perform()
            self.wait.until(lambda d: d.find_element_by_xpath(successed_element_selector).is_displayed())
            return True
        except Exception:
            self.logger.info("爬取异常：{message:%s}" % "极验验证码破解失败")
            return False
