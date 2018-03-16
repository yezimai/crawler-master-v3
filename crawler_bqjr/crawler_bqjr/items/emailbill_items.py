# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

from crawler_bqjr.items.base import AccountItem


class WsScItemDetail(Item):
    id = Field()  # 站口号
    t_date = Field()  # 结束日期
    p_date = Field()  # 起始日期
    description = Field()  # 消费详情
    curr_price = Field()  # 消费金额


class EmailBillItem(AccountItem):
    bill_records = Field()
