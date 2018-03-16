# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field

from crawler_bqjr.items.base import AccountItem


class CommunicationsBrand(object):
    Mobile = 1  # 中移动
    Unicom = 2  # 联通
    Telecom = 3  # 电信


class UserStatus(object):
    Opened = 1  # 开通
    Shutdown = 0  # 停机


class CallType(object):
    Caller = 1  # 主叫
    Called = 0  # 被叫


class MsgType(object):
    Send = 1  # 主叫
    Receive = 0  # 被叫


class Sex(object):
    Male = 1  # 男
    Female = 0  # 女


class UserCommunicationInfoItem(AccountItem):
    """
        用户的运营商数据
    """
    brand = Field()  # 运营商品牌
    province = Field()  # 省份
    city = Field()  # 城市

    balance = Field()  # 余额
    registration_time = Field()  # 注册时间，格式为1999-01-01
    in_nets_duration = Field()  # 在网时长，单位是月
    status = Field()  # 在网状态：1代表开通，0代表停机
    identification_number = Field()  # 身份证号
    identification_addr = Field()  # 身份证地址
    contact_addr = Field()  # 联系地址
    real_name = Field()  # 实际名字
    is_real_name = Field()  # 是否实名制，True or False
    sex = Field()  # 性别：1代表男，0代表女
    package = Field()  # 套餐

    # 近六个月通话记录，字典类型
    # 例如{"201601": [{"time":"2017-01-02 18:00:56","duration":"00:03:11","type":1,"other_num":"18628271780",
    #                  "my_location":"四川成都","other_location":"四川成都","fee":1.5,"land_type":"国内通话"}]}
    # 其中duration是通话时长，type是呼叫类型：1代表主叫，0代表被叫，my_location是本机通话地，
    # other_num是对方号码，other_location是对方归属地，land_type是通话类型，如“国内通话”
    history_call = Field()

    # 近六个月短信记录，字典类型
    # 例如{"201601": [{"time":"2017-01-02 18:00:56","type":1,"other_num":"18628271780"}]}
    # 其中type是传送方式 ：1代表发送，0代表接收，other_num是对方号码
    history_msg = Field()

    # 近六个月账单，字典类型，例如{"201601": {"all_fee": 46.00}}
    # 其中all_fee是月消费金额
    history_bill = Field()

    # 近六个月交费记录，字典类型
    # 例如{"201601": [{"time":"2017-01-02 18:00:56","channel":"银行代收_普通预存款","fee":1.5}]}
    # 其中channel是交费方式，fee是金额
    history_payment = Field()


class YournumberItem(Item):
    phone = Field()
    result = Field()
