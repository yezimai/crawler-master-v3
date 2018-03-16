# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class AnonymousLevel(object):
    HIGH = 1
    MIDDLE = 2
    LOW = 3


class SchemeType(object):
    HTTP = 1
    HTTPS = 2
    HTTP_OR_HTTPS = 3


class SupportMethod(object):
    GET = 1
    POST = 2
    GET_OR_POST = 3


class StableTime(object):
    ALL = 0
    MIN_10 = 1  # 10分钟
    MIN_30 = 2  # 30分钟
    HOUR_1 = 3  # 1小时
    HOUR_2 = 4  # 2小时


class ProxyItem(Item):
    ip = Field()
    port = Field()
    anonymous_level = Field()  # 匿名度
    scheme_type = Field()  # 类型
    support_method = Field()  # get/post支持
    location = Field()  # 位置
    response_time = Field()  # 响应时间
