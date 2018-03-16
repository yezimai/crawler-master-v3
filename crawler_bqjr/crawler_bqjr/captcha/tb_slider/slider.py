# -*- coding: utf-8 -*-
##############################################
# pc端淘宝登录的滑块验证码破解
#
# 注意事项：
# 1、目前仅稳定支持chrome浏览器，其他浏览器未测试；
# 2、由于sikuli是基于图形化的语言，所以此破解方法不支持无头浏览器；
# 3、配置好java的环境变量，并且还要将 jvm.dll 的路径添加到 PATH 变量中；
#    jvm.dll 路径应该是: xxx/java/jdk[your-jdk-version]/jre/bin/server
# 4、java环境变量配置好后，重启pychram IDE
##############################################

from platform import system as get_os

from crawler_bqjr.tools.flock import FilelockUtil

if 'Windows' == get_os():
    import logging
    from os import path as os_path
    from sys import path as sys_path

    sys_path.append(os_path.dirname(os_path.abspath(__file__)))

    from sikuli.sikuli import Sikuli

    class TaoBaoLoginSlider(object):
        """
        针对淘宝登录异常时的滑块验证码，使用示例：
        with TaoBaoLoginSlider(driver, wait, pid) as tb:
            res = tb.drag_login_slider("//*[text()='验证通过']")
        """

        current_url = os_path.dirname(os_path.abspath(__file__))

        def __init__(self, driver, wait, logger=None, pid=None, **kwargs):
            self.flock = FilelockUtil()
            self.skl = Sikuli(**kwargs)
            self.driver = driver
            self.wait = wait
            self.pid = pid
            self.logger = logger or logging

        def __enter__(self):
            self.flock.acquire()
            try:
                if self.pid:
                    self.hwnds = self.flock.get_hwnds(self.pid)
                    self.flock.hwnd_top_most(self.hwnds)
            except Exception:
                self.logger.error("页面置顶失败。")
            finally:
                return self

        def __exit__(self, type, value, trace):
            if self.hwnds:
                self.flock.hwnd_not_top_most(self.hwnds)
            self.flock.release()

        def drag_login_slider(self, success_xpath=None):
            """
            拖动滑块验证
            :param success_xpath: 成功后元素xpath
            :return             : success：True  error：False
            """
            img_library_url = self.current_url + '/img_library/'

            # 滑块图片的开始结束地址
            slider_start = img_library_url + 'login_slider_start.png'
            slider_end = img_library_url + 'login_slider_end.png'
            login = img_library_url + 'login.png'

            try:
                if not self.skl.wait(slider_start):
                    self.logger.warning("滑块没有加载成功。")
                    return False

                # 先模拟鼠标点击一下"登录"按钮，此时页面会刷新
                self.skl.click(login)

                if not self.skl.wait(slider_start):
                    self.logger.warning("滑块没有加载成功。")
                    return False

                # 开始拖动滑块验证码
                self.skl.dragDrop(slider_start, slider_end)

                if success_xpath:
                    self.wait.until(lambda dr: dr.find_element_by_xpath(success_xpath))
            except Exception:
                self.logger.exception("淘宝登录滑块验证码破解失败，报错信息:")
                return False
            else:
                return True
else:
    class TaoBaoLoginSlider(object):
        def __init__(self, *args, **kwargs):
            pass
