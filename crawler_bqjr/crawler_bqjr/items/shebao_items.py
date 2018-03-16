# -*- coding: utf-8 -*-

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


class SheBaoItem(AccountItem):
    city = Field()  # 城市

    private_no = Field()  # 社保编码
    real_name = Field()  # 姓名
    identification_number = Field()  # 身份证号
    sex = Field()  # 性别
    birthday = Field()  # 出生日期
    date_of_recruitment = Field()  # 参加工作时间
    status = Field()  # 参保状态
    identity = Field()  # 个人身份
    agency = Field()  # 经办机构/参保单位

    insurance_detail = Field()  # 社保明细
