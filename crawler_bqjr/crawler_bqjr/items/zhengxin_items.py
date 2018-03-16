# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


class ZhengxinPbcItem(AccountItem):
    """
    人行征信数据
    """
    code = Field()  # 身份验证码

    real_name = Field()  # 姓名
    identification_number = Field()  # 身份证号
    report_time = Field()  # 报告时间

    tips_html = Field()  # 个人信用信息提示的网页
    summary_html = Field()  # 个人信用信息概要
    report_html = Field()  # 个人信用报告
    detail = Field()  # 个人信息详细


class ZhengxinBankItem(ZhengxinPbcItem):
    """
    银行征信数据报告
    """
    report_no = Field()
