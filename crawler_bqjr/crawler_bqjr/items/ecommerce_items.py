# -*- coding: utf-8 -*-

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


################################
# 支付宝实体类
################################
class ZhiFuBaoItem(AccountItem):
    identification_number = Field()  # 身份证
    nick_name = Field()  # 支付宝昵称
    is_real_name = Field()  # 是否实名认证
    email = Field()  # 邮箱
    mobile = Field()  # 手机
    taobao_username = Field()  # 淘宝会员名
    registration_time = Field()  # 注册时间
    bank_card = Field()  # 银行卡
    receiver_addresses = Field()  # 收货地址

    # 支付宝交易记录，是一个list，类似于[{},{},...,{}],其中"{}"表示每条具体交易记录
    zhifubao_deals = Field()

    # 花呗账单,是一个dict，类似于{{},{},...,{}},其中"{}"表示每个月账单
    huabei = Field()


################################
# 淘宝实体类
################################
class TaoBaoItem(AccountItem):
    # 账户信息
    # accounts: {
    #     account  账号
    #     type  淘宝
    #     nick_name 昵称
    #     birthday  生日
    #     gender  性别
    #     taobao_account  会员名
    #     mobile  手机
    #     email  邮箱
    #     is_real_name  是否实名制
    #     identification_number  身份证号
    # }
    accounts = Field()

    # 收货地址信息list
    # 每个item包含以下字段
    # {
    #    receiver_name 收货人姓名
    #    receiver_area 收货人所在区域
    #    receiver_location_detail  收货人详细地址
    #    receiver_mobile 收货人手机号码
    #    receiver_phone  收货人座机号码
    #    receiver_postcode  收货人邮编
    #  }
    receiver_addresses = Field()

    # 订单list
    # 每个item包含以下字段
    # {
    #   deal_time  交易时间
    #   order_no   订单号
    #   sub_orders 子订单 包含字段：{'商品名':value,'数量':value}
    #   order_fee  交易金额
    #   status     交易状态
    # }
    orders = Field()


################################
# 京东实体类
################################
class JDItem(AccountItem):
    # 账户信息
    # accounts: {
    #     account  账号
    #     type  京东
    #     nick_name 昵称
    #     birthday  生日
    #     gender  性别
    #     email  邮箱
    #     mobile  电话
    #     is_real_name  是否实名制
    #     real_name  真实姓名
    #     identification_number  身份证号
    # }
    accounts = Field()

    # 收货地址信息list
    # 每个item包含以下字段
    # {
    #    receiver_name 收货人姓名
    #    receiver_area 收货人所在区域
    #    receiver_location_detail  收货人详细地址
    #    receiver_mobile 收货人手机号码
    #    receiver_phone  收货人座机号码
    #    receiver_email  收货人电子邮件
    #    receiver_tag 标签
    #    receiver_is_default 是否是默认地址
    #  }
    receiver_addresses = Field()

    # 订单list
    # 每个item包含以下字段
    # {
    #     "status": 状态,
    #     "settle_date": 订单时间,
    #     "goods_amount": 商品总额,
    #     "cashback_amount": 返现,
    #     "transportation_cost": 运费,
    #     "settle_amount": 应付总额,
    #     "payment_mode": 付款方式,
    #     "name": 收货人,
    #     "mobile": 手机号码,
    #     "address_detail": 收货地址,
    #     "goods": [
    #         {
    #             "good_name": 商品名称
    #             "good_price": 价格
    #             "good_num": 商品数量
    #         }
    #     ]
    # }
    orders = Field()

    # 白条
    # avaliable_credit_line 可用信用额度
    # total_credit_line     总信用额度
    # baitiao_count         打白条次数
    # baitiao_score         白条信用分
    baitiao = Field()

    # 资产信息
    # assets: {
    #     total_assets  总资产
    #     balance  京东小金库金额
    #     balance_available  京东小金库可用金额
    #     finance  理财金额
    #     wallet_money_available  京东钱包可用金额
    #     wallet_money  京东钱包金额
    # }
    assets = Field()

    # 定期持仓list
    # 每个item包含以下字段
    # {
    #     code  产品代码
    #     name  产品名称
    #     status  状态
    #     currency  币种(中文，如人民币)
    #     start_date  开始日期(格式：“YYYY - MM - DD”)(date)
    #     end_date  到期日期(格式：“YYYY - MM - DD”)(date)
    #     capital  本金(单位：分)
    #     interest  利息(单位：分)
    #     amount  本息总额(单位：分)
    #     interest_rate  利率(单位：百分比)
    #     term  存期
    #     automatic_redeposit  自动转存
    # }
    position_fixed = Field()

    # 基金持仓list
    # 每个item包含以下字段
    # {
    #     code // 产品代码(varchar(64))
    #     name // 产品名称(varchar(32))
    #     currency // 币种(中文，如人民币)(varchar(16))
    #     capital // 本金(单位：分)(bigint(20))
    #     share // 当前份额(单位：分)(bigint(20))
    #     usable_share // 可用份额(单位：分)(bigint(20))
    #     dividend_type // 分红方式(如
    #     现金分红)(varchar(32))
    #     net_value // 当前净值(单位：分)(bigint(20))
    #     net_value_date // 净值日期(格式：“YYYY - MM - DD”)(date)
    #     market_value // 当前市值(单位：分)(bigint(20))
    #     floating_pl // 浮动盈亏(单位：分)(bigint(20))
    #     yield // 收益率(单位：百分比)(double)
    #     income_yesterday // 昨日收益(单位：分)(bigint(20))
    # }
    position_fund = Field()

    # 理财持仓list
    # 每个item包含以下字段
    # {
    #     code // 产品代码(varchar(64))
    #     name // 产品名称(varchar(32))
    #     currency // 币种(中文，如人民币)(varchar(16))
    #     capital // 本金(单位：分)(bigint(20))
    #     share // 当前份额(单位：分)(bigint(20))
    #     usable_share // 可用份额(单位：分)(bigint(20))
    #     dividend_type // 分红方式(如现金分红)(varchar(32))
    #     net_value // 当前净值(单位：分)(bigint(20))
    #     market_value // 当前市值(单位：分)(bigint(20))
    #     start_date // 开始时间(格式：“YYYY - MM - DD”)(date)
    #     end_date // 到期时间(格式：“YYYY - MM - DD”)(date)
    #     expected_return // 预期收益(单位：分)(bigint(20))
    #     expected_yield // 预期收益率(单位：百分比)(double)
    #     floating_pl // 浮动盈亏(单位：分)(bigint(20))
    #     term // 存期(varchar(32))
    #     income_yesterday // 昨日收益(单位：分)(bigint(20))
    #     status // 状态(varchar(32))
    # }
    position_finance = Field()


class YhdItem(AccountItem):
    pass
