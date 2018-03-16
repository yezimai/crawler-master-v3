# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class CompanyItem(Item):
    from_web = Field()  # 来源网站
    from_url = Field()  # 来源URL

    name = Field()  # 公司名称
    summary = Field()  # 简介
    address = Field()  # 地址
    industry = Field()  # 行业
    employee_scale = Field()  # 雇员规模
    company_form = Field()  # 公司性质
    area = Field()  # 地区

    mobile = Field()  # 手机号码
    telephone = Field()  # 电话
    annual_turnover = Field()  # 年营业额
    annual_export_volume = Field()  # 年出口额
    main_area = Field()  # 主营地区
    main_products = Field()  # 主营产品

    legal_person = Field()  # 法人
    found_date = Field()  # 成立日期
    check_date = Field()  # 核准日期
    registered_capital = Field()  # 注册资本
    business_period = Field()  # 经营期限


class CompanyDetailItem(CompanyItem):
    registration_code = Field()  # 注册号
    uniform_social_credit_code = Field()  # 统一社会信用代码
    registered_address = Field()  # 注册地址
    general_business = Field()  # 一般经营项目
    licensed_business = Field()  # 许可经营项目
    type = Field()  # 类型
    status = Field()  # 企业登记状态

    shareholder_info = Field()  # 股东列表，例如[[姓名, 出资金额, 出资比例]...]
    member_info = Field()  # 成员信息，例如[[姓名, 职务]...]

    search_url = Field()  # 查询来源url
    html = Field()  # html源文(会被pipeline替换成存储文件的文件名html_file)


class CompanyDetail2Item(CompanyDetailItem):
    organization_code = Field()  # 组织机构代码
    registered_authority = Field()  # 登记机关


class CompanyGXSTDetailItem(CompanyDetail2Item):
    pass
