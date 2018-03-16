# *- coding: utf-8 -*-
####################################################
# 验证码识别工具
# 主要提供验证码相关的处理函数
# 依赖pil,numpy,opencv等第三方库
# 作者： tao.jiang02@bqjr.cn
# 日期： 2017年1月6日
# 版本： V1.0
####################################################

import cv2

import numpy
from PIL import Image


####################################################
# 降噪处理，消除验证码图片中的干扰线、点等
# 参数：
#      filepath 图片路径 String类型
# 返回值：
#      dest_img PIL.Image类型
####################################################
def denosing(filepath):
    with Image.open(filepath, "wr") as img:
        # 构造算子为32位浮点三维矩阵kernel：[(1/20,1/20,1/20,1/20,1/20)
        #                                (1/20,1/20,1/20,1/20,1/20)
        #                                (1/20,1/20,1/20,1/20,1/20)
        #                                (1/20,1/20,1/20,1/20,1/20)
        #                                (1/20,1/20,1/20,1/20,1/20)]
        kernel = numpy.ones((5, 5), numpy.float32) / 20
        # 做卷积去噪点
        eroded = cv2.filter2D(numpy.array(img), -1, kernel)
        # 图像灰度化处理
        eroded = cv2.cvtColor(eroded, cv2.COLOR_BGR2GRAY)
        # 图像二值化处理
        ret, eroded = cv2.threshold(eroded, 127, 255, cv2.THRESH_BINARY)

        return Image.fromarray(eroded)
