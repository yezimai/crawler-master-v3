# -*- coding: utf-8 -*-

from crawler_bqjr.items.emailbill_items import EmailBillItem
from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.spiders.emailbill_spiders.email_html_parse import parse_bank_email

class EmailSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=EmailBillItem, **kwargs)
        self.bill_name_sep = ": "

    def get_account_request(self, account_info):
        request = super().get_account_request(account_info)
        request.meta["item"]['bill_records'] = []
        return request

    def get_bill_record(self, bankname, subject, content_html):
        bill_name = subject
        try:
            bill_info = parse_bank_email(bankname, content_html, subject)
            if "bill_info" in bill_info:
                bill_name += self.bill_name_sep + bill_info["bill_info"].get("due_date", "")
        except Exception:
            self.logger.exception(bill_name + "账单解析失败")
            bill_info = {}

        return {'bankname': bankname, 'billname': bill_name, 'bill': bill_info}
