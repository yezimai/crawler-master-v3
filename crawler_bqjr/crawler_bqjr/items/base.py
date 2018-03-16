# -*- coding: utf-8 -*-

from scrapy import Field, Item


class AccountItem(Item):
    customer_id = Field()
    serial_no = Field()

    username = Field()  # 用户名
    password = Field()  # 密码
    is_complete = Field()  # 是否爬取完成
