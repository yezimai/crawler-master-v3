# -*- coding: utf-8 -*-

from scrapy import Field

from crawler_bqjr.items.base import AccountItem


class BankItem(AccountItem):
    bank = Field()  # 银行
    identification_number = Field()  # 身份证号码

    balance = Field()  # 余额
    trade_records = Field()  # 近期交易记录

    #############################################
    # trade_records字段说明
    #############################################
    # 字段名                  # 字段释义          # 包含该字段的银行
    # trade_date              # 交易日期          # 农行 民生 建行 广发 招商 中信 交通 兴业 工行 华夏 邮政 中行 浦发 光大 平安
    # trade_income            # 收入              # 农行 民生 建行 广发 招商 中信 交通 兴业 工行 华夏 邮政 中行 浦发 光大 平安
    # trade_outcome           # 支出              # 农行 民生 建行 广发 招商 中信 交通 兴业 工行 华夏 邮政 中行 浦发 光大 平安
    # trade_amount            # 交易金额          # 农行 民生 建行 广发 招商 中信 交通 兴业 工行 华夏 邮政 中行 浦发 光大 平安
    # trade_acceptor_account  # 交易接受方账号    #           建行 广发      中信           工行 华夏      中行      光大 平安
    # trade_acceptor_name     # 交易接受方姓名    # 农行 民生 建行 广发                兴业 工行 华夏      中行      光大 平安
    # trade_accounting_date   # 入账日            #           建行      招商 中信 交通           华夏
    # trade_balance           # 交易后的账户余额  # 农行 民生      广发 招商 中信 交通      工行 华夏 邮政 中行 浦发 光大 平安
    # trade_channel           # 交易渠道          # 农行 民生      广发                                    中行      光大
    # trade_currency          # 交易币种          #           建行 广发           交通      工行 华夏      中行
    # trade_location          # 交易地点          #           建行           中信 交通      工行
    # trade_name              # 交易名称          #      民生                                    华夏
    # trade_remark            # 交易摘要          # 农行           广发 招商 中信      兴业 工行 华夏 邮政 中行 浦发 光大 平安
    # trade_type              # 交易类型          # 农行 民生           招商      交通           华夏                     平安
    #############################################
