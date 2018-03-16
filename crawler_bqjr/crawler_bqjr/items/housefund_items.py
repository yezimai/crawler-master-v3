# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


class HousefundItem(AccountItem):
    """
    用户的公积金数据
    """
    city = Field()  # 所属城市

    mobile = Field()  # 电话
    private_no = Field()  # 个人编号(公积金账号)
    real_name = Field()  # 个人姓名
    birthday = Field()  # 出生日期
    identification_number = Field()  # 证件号码
    identification_type = Field()  # 证件类型
    phone = Field()  # 固定电话
    nation = Field()  # 民族
    sex = Field()  # 性别
    signflag = Field()  # 面签状态
    mail = Field()  # 电子邮箱
    remark = Field()  # 备注信息

    # 个人账户详情/缴存信息(缴费单位及基数等信息):
    # [{"private_no":"社保编号", "corpcode":"公司代码", "corpname": "公司名称", "accmny": "余额",
    # "mperpaystate": "缴存状态", "basemny": "缴存基数", "corpscale": "公司缴存比例", "perscale": "个人缴存比例",
    # "perdepmny": "个人月汇缴额", "corpdepmny": "公司月汇缴额", "mpayendmnh": "缴至年月"},...]
    account_detail = Field()

    # 缴存明细详情
    # [{"acctime":"缴存时间", "bustype": "缴存类型", "depmny": "缴存合计", "corpdepmny"："单位缴存",
    # "perdepmny"："个人缴存""corpcode"："公司代码", "corpname": "公司名","remark":"备注"}]
    payment_detail = Field()

    # 提取明细
    # {"list":[{"acctime":"2017-03-22",....}]}
    fetch_detail = Field()

    # 贷款信息
    # [{"agrcode":"贷款合同号"，"loancode":"个贷申请号","loanbank":"还款银行"，"depname":"分行名字","repayway":"还款方式",
    # "loanbal":"剩余本金"，"ratetotal"："已还利息","nobase":"逾期本金","norate":"逾期利息","addres":"地址",
    # "mntpay": "每月还款额", "loanmnhs":"还款年限","loanmny":"贷款总额",},...]
    loan_detail = Field()

    # 还款记录
    # [{"ratemny":"还利息","basemny":"还本金","bkdate":"还款时间", "paytype":"还款类型",
    # "loanrate": "利率", "loanbal":"还款余额"}]
    repayment_detail = Field()
