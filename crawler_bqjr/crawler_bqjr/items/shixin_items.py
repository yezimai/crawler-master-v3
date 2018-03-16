# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class ShixinListItem(Item):
    from_web = Field()  # 来源网站，0代表baidu，1代表shixinmingdan，2代表dailianmeng
    link_id = Field()  # 链接ID
    update_time = Field()  # 更新时间

    name = Field()  # 被执行人姓名/名称
    id = Field()  # 身份证号码/组织机构代码


class ShixinDetailItem(ShixinListItem):
    sex = Field()  # 性别
    age = Field()  # 年龄
    legal_person = Field()  # 法定代表人或者负责人姓名
    adjudge_court = Field()  # 做出执行依据单位
    execution_court = Field()  # 执行法院
    province = Field()  # 省份
    execution_file_code = Field()  # 执行依据文号
    on_file_date = Field()  # 立案时间
    file_code = Field()  # 案号
    duty = Field()  # 生效法律文书确定的义务
    fulfill_status = Field()  # 被执行人的履行情况
    fulfill_situation = Field()  # 失信被执行人行为具体情形
    publish_date = Field()  # 发布时间


class ZhixingDetailItem(ShixinListItem):
    execution_court = Field()  # 执行法院
    execution_money = Field()  # 执行标的/执行金额
    on_file_date = Field()  # 立案时间
    file_code = Field()  # 案号


class P2PItem(ShixinListItem):
    """
    P2P老赖信息
    """
    personal_detail = Field()  # 个人详情
    account_detail = Field()  # 账户详情
    debt_detail = Field()  # 欠款详情
