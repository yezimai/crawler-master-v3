# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class CnmoItem(Item):
    brand_name = Field()  # 手机品牌
    brand_pic = Field()  # 手机品牌图链接
    brand_url = Field()  # 手机品牌链接
    product_name = Field()  # 手机型号
    product_url = Field()  # 手机链接
    product_pic = Field()  # 手机图片链接
    product_price = Field()  # 价格
    for_sale = Field()  # 是否在售
    update_time = Field()  # 更新时间
    detail_info = Field()  # 详细参数


class ZolAccessoryItem(Item):
    name = Field()  # 配件名称
    category = Field()  # 配件类别
    url = Field()  # 配件链接
    price = Field()  # 配件价格
    pic_url = Field()  # 配件图片链接
    info = Field()  # 配件参数
    status = Field()  # 销售状态
    update_time = Field()  # 更新时间
