# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


class XuexinItem(AccountItem):
    """
    学信网学历学籍数据
    """
    xueli = Field()

    # 信息内容字段说明，字段key来自学信网的资料描述有可能随网页变化。
    #############################################
    # 字段名                 # 例子
    # 姓名                    张三
    # 性别                    男
    # 出生日期              1985年03月19日
    # 名族                    汉族
    # 证件号码         320122198503195563
    # 学校名称              四川大学
    # 层次                    本科
    # 专业                  信息工程
    # 学制                    4
    # 学历类型              普通
    # 学习形式              普通全日制
    # 分院                  信息软件工程学院
    # 系（所、函授站）      信息软件工程学院
    # 班级                  20002230
    # 学号                  20002230155525
    # 入学日期              2000年01月01日
    # 离校日期              2004年01月01日
    # 学籍状态              不在籍（毕业）
    # 证书编号           	1061 4120 1505 0012 23
    # 毕业证照片            /data/image_data/xuexin/8e953ec2518411e7b9c8dc4a3e761bbc.jpg
