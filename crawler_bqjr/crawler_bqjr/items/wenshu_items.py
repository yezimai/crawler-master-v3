# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class WenshuItem(Item):
    """
    文书信息
    """

    case_type = Field()  # 案件类型
    sentence_date = Field()  # 裁判日期
    case_name = Field()  # 案件名称
    file_id = Field()  # 文书ID
    trial_procedure = Field()  # 审判程序
    case_no = Field()  # 案号
    court_name = Field()  # 法院名称
    relation = Field()  # 关联文书
    title = Field()  # 文书标题
    pub_date = Field()  # 发布时间
    html = Field()  # 文书内容


class ChinacourtItem(Item):
    """
    中国法院
    """
    name = Field()  # 法院名称
    level = Field()  # 法院级别
    province = Field()  # 省份
