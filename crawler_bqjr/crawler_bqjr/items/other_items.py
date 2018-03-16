# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class YishangItem(Item):
    """
    亿商联盟商铺信息
    """

    name = Field()  # 商店名
    address = Field()  # 商店地址
    pic = Field()  # 商店图片


class GpsspgItem(Item):
    """
    地址转经纬度
    """
    id = Field()
    address = Field()  # 地址
    lng = Field()  # 纬度值
    lat = Field()  # 经度值
    # precise = Field()  # 是否精确查找
    # confidence = Field()  # 可信度
    # level = Field()  # 地址类型
