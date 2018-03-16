from itertools import islice
from re import compile as re_compile

from bs4 import BeautifulSoup
from requests import get as http_get, post as http_post

from global_utils import json_loads

BILL_CYCLE_SEP = "~"
DATE_SEP = "-"
money_pattern = re_compile(r'([\d\.\-]+)')  # 不包含逗号


def date_add_sep(date_str):
    return date_str[:4] + DATE_SEP + date_str[4:6] + DATE_SEP + date_str[6:]


def get_money(money_str):
    try:
        return money_pattern.search(money_str.replace(",", "")).group(1)
    except Exception:
        return money_str


bocom_name_pattern = re_compile(r'尊敬的 (\S+)您好！')
bocom_billing_cycle_html_pattern = re_compile(r'账单周期：')
bocom_card_pattern = re_compile(r'卡号:([\d\*]+)')


def parse_bocom_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_info = {}

    find_name = bs_obj.find('p', text=bocom_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[4:-5]

    find_card = bs_obj.find('p', text=bocom_card_pattern)
    if find_card:
        bill_info['card_num'] = bocom_card_pattern.search(find_card.getText()).group(1)

    find_billing_cycle = bs_obj.find('p', text=bocom_billing_cycle_html_pattern)
    if find_billing_cycle:
        bill_info['bill_cycle'] = find_billing_cycle.getText(strip=True)[5:] \
            .replace("-", BILL_CYCLE_SEP).replace("/", DATE_SEP)

    trs = bs_obj.find('table', id='table1').findAll('tr')
    due_date = trs[0].find('td').getText(strip=True)
    bill_info['due_date'] = due_date.replace("/", DATE_SEP) if due_date != "---" else ""
    bill_info['repayment'] = get_money(trs[1].find('td').getText(strip=True))
    bill_info['min_repayment'] = get_money(trs[2].find('td').getText(strip=True))
    bill_info['credit_limit'] = get_money(trs[3].find('td').getText(strip=True))
    bill_info['cash_limit'] = get_money(trs[4].find('td').getText(strip=True))

    bill_detail = []
    for table in bs_obj.findAll('table', id='table3'):
        trade_type = table.findParent().findPrevious().getText(strip=True)
        amount_prefix = '-' if trade_type == '以下是您的还款、退货及费用返还明细' else ""
        for tbody in table.findAll('tbody'):
            for tr in tbody.findAll('tr'):
                tds = tr.findAll('td')
                if len(tds) < 5:
                    continue

                record_amount = amount_prefix + get_money(tds[4].getText(strip=True))
                bill_detail.append({
                    'trade_date': tds[0].getText(strip=True).replace("/", DATE_SEP),
                    'book_date': tds[1].getText(strip=True).replace("/", DATE_SEP),
                    'trade_summary': tds[2].getText(strip=True),
                    'trade_amount': record_amount,
                    'record_amount': record_amount,
                })

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


abc_name_pattern = re_compile(r'尊敬的(\S+)先生/女士：')


def parse_abc_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_info = {}

    find_name = bs_obj.find('font', text=abc_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[3:-6]

    card_info_tds = bs_obj.find('font', text='卡号').findParent("table").findAll('td')
    bill_info['card_num'] = card_info_tds[2].getText(strip=True)
    bill_cycle1, bill_cycle2 = card_info_tds[4].getText(strip=True).split("-", 1)
    bill_info['bill_cycle'] = date_add_sep(bill_cycle1) + BILL_CYCLE_SEP + date_add_sep(bill_cycle2)
    due_date = card_info_tds[6].getText(strip=True)
    bill_info['due_date'] = due_date[:4] + DATE_SEP + due_date[4:6] + DATE_SEP + due_date[6:]

    values = []
    for td in bs_obj.find('div', id='fixBand3').findAll('td'):
        if not len(td.findChildren()) > 3:
            the_info = td.getText(strip=True)
            if the_info:
                values.append(the_info)
    bill_info['currency'] = values[0]
    bill_info['repayment'] = values[1].replace(",", "").replace("-", "")
    bill_info['min_repayment'] = values[2].replace(",", "").replace("-", "")
    bill_info['credit_limit'] = values[3].replace(",", "")

    bill_detail = []
    divs = bs_obj.findAll('div', id='fixBand10')[1].findAll('div')
    group_list_split = 7
    for record in (divs[i:i + group_list_split] for i in range(0, len(divs), group_list_split)):
        record_amount = get_money(record[6].getText(strip=True))
        bill_detail.append({
            'trade_date': date_add_sep(record[0].getText(strip=True)),
            'book_date': date_add_sep(record[1].getText(strip=True)),
            'card_num': record[2].getText(strip=True),
            'trade_summary': record[3].getText(strip=True),
            'record_location': record[4].getText(strip=True),
            'trade_amount': record_amount.lstrip("-") if record_amount.startswith("-") else "-" + record_amount,
            'record_amount': record_amount,
        })

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


ccb_name_pattern = re_compile(r'尊敬的(\S+)，您好！')
ccb_bill_cycle_html_pattern = re_compile(r'账单周期 ：')
ccb_bill_detail_html_pattern = re_compile(r'交易明细')


def parse_ccb_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_cycle = bs_obj.find('font', text=ccb_bill_cycle_html_pattern)
    if bill_cycle:  # 老账单
        info = []
        for div in bs_obj.find('font', text='账单日').findParent("table").findAll('td'):
            the_info = div.find('font')
            if the_info:
                info.append(the_info.getText(strip=True))

        bill_info = {
            'bill_cycle': bill_cycle.getText(strip=True)[6:].replace("-", BILL_CYCLE_SEP).replace("年", DATE_SEP).replace("月", DATE_SEP).replace("日", ""),
            'bill_date': info[1],
            'due_date': info[3],
            'credit_limit': get_money(info[5]),
            'cash_limit': get_money(info[7]),
        }
    else:  # 新账单
        bill_info = {}

        credit_infos = bs_obj.find('font', text='本期账单日').findParent("table").findAll('font')
        if len(credit_infos) >= 13:
            bill_info['bill_date'] = credit_infos[2].getText(strip=True)
            bill_info['credit_limit'] = get_money(credit_infos[5].find('a').getText(strip=True))
            bill_info['cash_limit'] = get_money(credit_infos[8].getText(strip=True))
            bill_info['avaliable_limit'] = credit_infos[12].findParent().getText(strip=True).replace(",", "")

        due_infos = bs_obj.find('font', text='Statement Cycle').findParent("table").findAll("font")
        if len(due_infos) >= 6:
            bill_info['bill_cycle'] = due_infos[3].getText(strip=True)\
                .replace("-", BILL_CYCLE_SEP).replace("/", DATE_SEP)
            bill_info['due_date'] = due_infos[6].getText(strip=True).replace("/", DATE_SEP)

    bill_table = bs_obj.find('font', text='信用卡卡号')
    if bill_table:
        tds = bill_table.findParent("table").findAll('tr')[1].findAll('td')
        bill_info['card_num'] = tds[0].getText(strip=True)
        bill_info['currency'] = tds[1].getText(strip=True)
        bill_info['repayment'] = tds[2].getText(strip=True).replace(",", "")
        bill_info['min_repayment'] = tds[3].getText(strip=True).replace(",", "")
    else:
        bill_info.setdefault('card_num', "")
        bill_info.setdefault('currency', "人民币(CNY)")
        bill_info.setdefault('repayment', "0")
        bill_info.setdefault('min_repayment', "0")

    bill_detail = []
    for info_tr in bs_obj.find('font', text=ccb_bill_detail_html_pattern).findParent("table").findAll('tr')[4:-1]:
        record = info_tr.findAll('td')
        record_amount = record[7].getText(strip=True).replace(",", "")
        bill_detail.append({
            'trade_date': record[0].getText(strip=True),
            'book_date': record[1].getText(strip=True),
            'card_num': record[2].getText(strip=True),
            'trade_summary': record[3].getText(strip=True),
            'trade_amount': record_amount,
            'record_amount': record_amount,
        })

    find_name = bs_obj.find('font', text=ccb_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[3:-4]

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


pingan_name_pattern = re_compile(r'尊敬的(\S+) \S+ ：')
pingan_card_num_pattern = re_compile(r'平安银行\S* ([\*\d]+)')


def parse_pingan_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_info = {}

    find_name = bs_obj.find('strong', text=pingan_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[3:-5]

    card_info_tds = bs_obj.find('td', text='本期账单日').findParent("table").findAll('td')
    bill_info['bill_date'] = card_info_tds[1].getText(strip=True)
    bill_info['due_date'] = card_info_tds[3].getText(strip=True)
    bill_info['credit_limit'] = get_money(card_info_tds[5].getText(strip=True))
    bill_info['cash_limit'] = get_money(card_info_tds[7].getText(strip=True))

    card_info_table2 = bs_obj.find('td', text='本期应还金额').findParents()[3]
    card_info_texts = [info.strip() for info in card_info_table2.text.split('\n\n\n') if info.strip()]
    bill_info['repayment'] = get_money(card_info_texts[2])
    bill_info['min_repayment'] = get_money(card_info_texts[4])
    card_num = bs_obj.find('td', text=pingan_card_num_pattern)
    if card_num:
        bill_info['card_num'] = pingan_card_num_pattern.search(card_num.getText()).group(1)

    bill_detail = []
    for card_detail in islice(card_num.findParent("table").findAll('tr'), 2, None):
        record = [info.strip() for info in card_detail.text.split('\n') if info.strip()]
        bill_detail.append({
            'trade_date': record[0],
            'book_date': record[1],
            'trade_summary': record[2],
            'trade_amount': get_money(record[3]),
        })

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


cncb_name_pattern = re_compile(r'尊敬的(\S+)：')
cncb_biling_cycle_pattern = re_compile(r'记录了您(\S+)账户变动')
cncb_due_date_pattern = re_compile(r'到期还款日：(\S+)')
cncb_card_num_pattern = re_compile(r'卡号:([\d\-*]+)')


def parse_cncb_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_info = {}

    find_name = bs_obj.find('font', text=cncb_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[3:-3]

    biling_cycle = bs_obj.find('div', text=cncb_biling_cycle_pattern)
    if biling_cycle:
        bill_info['bill_cycle'] = cncb_biling_cycle_pattern.search(biling_cycle.getText()).group(1) \
            .replace("-", BILL_CYCLE_SEP).replace("年", DATE_SEP).replace("月", DATE_SEP).replace("日", "")

    due_date = bs_obj.find('div', text=cncb_due_date_pattern).getText(strip=True)
    if due_date:
        bill_info['due_date'] = due_date[6:].replace("年", DATE_SEP).replace("月", DATE_SEP).replace("日", "")

    card_num = bs_obj.find('div', text=cncb_card_num_pattern).getText(strip=True)
    if card_num:
        bill_info['card_num'] = card_num[4:].replace("-", "")

    info_fonts = [info.getText(strip=True) for info in bs_obj.find('html').find('table').contents[1].findAll('font')
                  if info.getText(strip=True)]
    if "due_date" not in bill_info:
        bill_info['due_date'] = info_fonts[0][6:].replace("年", DATE_SEP).replace("月", DATE_SEP).replace("日", "")
    bill_info['repayment'] = info_fonts[2].replace(",", "")
    bill_info['min_repayment'] = info_fonts[6].replace(",", "")
    bill_info['credit_limit'] = info_fonts[11].replace(",", "")
    bill_info['cash_limit'] = info_fonts[13].replace(",", "")

    detail_fonts = bs_obj.find('html').find('table').contents[7].findAll('font')
    if 'card_num' not in bill_info:
        bill_info['card_num'] = detail_fonts[2].getText(strip=True)[4:].replace("-", "")

    bill_detail = []
    detail = [info.getText(strip=True) for info in detail_fonts if info.getText(strip=True)][14:]
    group_list_split = 8
    for record in (detail[i:i + group_list_split] for i in range(0, len(detail), group_list_split)):
        trade_date = record[0]
        if not trade_date[0].isdigit():
            break

        record_amount = record[7].replace(",", "")
        bill_detail.append({
            'trade_date': date_add_sep(trade_date),
            'book_date': date_add_sep(record[1]),
            'card_num': record[2],
            'trade_summary': record[3],
            'trade_amount': record_amount,
            'record_amount': record_amount,
        })

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


cmb_name_pattern = re_compile(r"尊敬的 (\S+) \S+，您好！")
cmb_date_pattern = re_compile(r"\d+")
cmb_money_pattern = re_compile(r"￥[\-\.\d]+")
cmb_subject_date_pattern = re_compile(r"(\d{4})年\d+月")

# 招商银行e招贷
ezd_due_date_pattern = re_compile(r'(\d+)月(\d{2})日')
ezd_repayment_pattern = re_compile(r'账单金额\D+([\d\.,]+)')
ezd_min_repayment_pattern = re_compile(r'本期最低还款\D+([\d\.,]+)')


def _parse_cmb_detail_date(bill_cycle_pair, the_date):
    if not the_date:
        return ""

    month = the_date[:2]
    for year_month in bill_cycle_pair:
        if year_month.endswith(month):
            return year_month + DATE_SEP + the_date[2:]

    # 应该永远不会运行到这步
    return bill_cycle_pair[0][:5] + month + DATE_SEP + the_date[2:]


def parse_cmb_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_detail = []
    if '您好！以下是您的招商银行信用卡' in html_string:
        info = [info_font.getText(strip=True) for info_font in bs_obj.findAll('font')]
        bill_cycle = info[1].replace("-", BILL_CYCLE_SEP).replace("/", DATE_SEP)
        bill_info = {
            'bill_cycle': bill_cycle,
            'credit_limit': get_money(info[2]),
            'repayment': get_money(info[3]),
            'min_repayment': get_money(info[4]),
            'due_date': info[5].replace("/", DATE_SEP),
        }

        find_name = bs_obj.find("font", text=cmb_name_pattern)
        if find_name:
            bill_info['real_name'] = cmb_name_pattern.search(find_name.getText()).group(1)

        bill_cycle_pair = [i[:7] for i in bill_cycle.split(BILL_CYCLE_SEP)]
        for detail in (info[i:i + 7] for i in range(14, len(info), 7)):
            book_date = detail[1]
            if book_date and book_date[0].isdigit():
                bill_detail.append({
                    'trade_date': _parse_cmb_detail_date(bill_cycle_pair, detail[0]),
                    'book_date': _parse_cmb_detail_date(bill_cycle_pair, book_date),
                    'trade_summary': detail[2],
                    'trade_amount': detail[6].replace(",", ""),
                    'card_num': detail[4],
                    'record_location': detail[5],
                })
    elif "信用卡e招贷账单已出" in html_string:
        bill_info = {}
        account_info_str = bs_obj.find("span", id="fixBand44").getText(strip=True)

        find_repayment = ezd_repayment_pattern.search(account_info_str)
        if find_repayment:
            bill_info['repayment'] = find_repayment.group(1).replace(",", "")

        find_min_repayment = ezd_min_repayment_pattern.search(account_info_str)
        if find_min_repayment:
            bill_info['min_repayment'] = find_min_repayment.group(1).replace(",", "")

        find_due_date = ezd_due_date_pattern.search(account_info_str)
        if find_due_date:
            month, day = find_due_date.groups()
            month = int(month)
            year = bs_obj.find("span", id="fixBand17").getText(strip=True)[1:5]
            if month == 1:
                year = str(int(year) + 1)
            bill_info['due_date'] = year + DATE_SEP + ("%02d" % month) + DATE_SEP + day
    else:
        info = []
        for info_font in bs_obj.findAll('font'):
            the_info = info_font.getText(strip=True)
            if the_info:
                info.append(the_info)

        location = 0
        for i, info_str in enumerate(info):
            if cmb_money_pattern.search(info_str):
                location = i  # 多个版本html 用应还款额位置确定其他信息
                break

        year = cmb_subject_date_pattern.search(subject).group(1)
        bill_info = {}
        if location == 11:
            month = info[7]
            if int(month) == 1 and year:
                year = str(int(year) + 1)
            bill_info['due_date'] = year + DATE_SEP + month + DATE_SEP + info[9]
            bill_info['repayment'] = get_money(info[11])
            bill_info['min_repayment'] = get_money(info[13])
        elif location == 15:
            month = info[8]
            if int(month) == 1 and year:
                year = str(int(year) + 1)
            bill_info['due_date'] = year + DATE_SEP + month + DATE_SEP + info[10]
            bill_info['repayment'] = get_money(info[15])
            bill_info['min_repayment'] = get_money(info[18])
        elif location == 1:
            due_date = info[0].split("/")
            month = due_date[-2]
            if int(month) == 1 and year:
                year = str(int(year) + 1)
            bill_info['due_date'] = year + DATE_SEP + month + DATE_SEP + due_date[-1]
            bill_info['repayment'] = get_money(info[1])
            bill_info['min_repayment'] = get_money(info[3])

    result = {
        'bill_info': bill_info,
        'bill_detail': bill_detail
    }

    return result


cgb_name_pattern = re_compile(r'尊敬的(\S+),您好！')
cgb_bill_cycle_html_pattern = re_compile(r'账单周期：')


def parse_cgb_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    info = []
    par = bs_obj.find('font', text=cgb_bill_cycle_html_pattern).findParents()[13]
    for info_font in par.findAll('font'):
        the_info = info_font.getText(strip=True)
        if the_info:
            info.append(the_info)

    bill_info = {
        'bill_cycle': info[1][5:].replace("/", DATE_SEP).replace(" 至 ", BILL_CYCLE_SEP),
        'card_num': info[8],
        'repayment': info[9].replace(",", ""),
        'min_repayment': info[10].replace(",", ""),
        'due_date': info[11].replace("/", DATE_SEP),
        'credit_limit': info[13].replace(",", ""),
    }

    find_name = bs_obj.find("font", text=cgb_name_pattern)
    if find_name:
        bill_info['real_name'] = find_name.getText(strip=True)[3:-6]

    result = {
        'bill_info': bill_info,
        'bill_detail': []
    }

    return result


spdb_name_pattern = re_compile(r'尊敬的(\S+) \S+:')
spdb_repayment_pattern = re_compile(r'本期应还款总额：\D+([\d\.,]+)')
spdb_due_date_pattern = re_compile(r'到期还款日：\s*([\d/]+)')
SPDB_HEADERS = {
    'Host': 'ebill.spdbccc.com.cn',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3212.0 Safari/537.36',
    'Upgrade-Insecure-Requests': '1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}


def parse_spdb_credit_email_html(html_string, subject=""):
    bs_obj = BeautifulSoup(html_string, "lxml")

    bill_info = {}

    account_info_str = bs_obj.find("td").getText(strip=True)

    find_name = spdb_name_pattern.search(account_info_str)
    if find_name:
        bill_info['real_name'] = find_name.group(1)

    find_repayment = spdb_repayment_pattern.search(account_info_str)
    if find_repayment:
        bill_info['repayment'] = find_repayment.group(1).replace(",", "")

    find_due_date = spdb_due_date_pattern.search(account_info_str)
    if find_due_date:
        bill_info['due_date'] = find_due_date.group(1).replace("/", DATE_SEP)

    try:
        url1 = bs_obj.find('span', text='点击').findParent("table").find('a').get('href')

        headers = SPDB_HEADERS.copy()
        r1 = http_get(url1, headers=headers)
        cookie_str = r1.headers.get('Set-Cookie')
        headers['Cookie'] = cookie_str
        url2 = 'https://ebill.spdbccc.com.cn/cloudbank-portal/myBillController/loadHomeData.action'

        r = http_post(url2, headers=headers)
        json_info = json_loads(r.text)
        bill_info['card_num'] = json_info.get('cardNo')
        bill_info['due_date'] = json_info.get('dueDate')
        bill_info['repayment'] = json_info.get('stmtAmt')
        bill_info['min_repayment'] = json_info.get('minPay')
        bill_info['credit_limit'] = json_info.get('creditLimit')
        bill_info['cash_limit'] = json_info.get('cashLimit')
        bill_info['bill_date'] = json_info.get('closeDate')
    except Exception:
        pass

    result = {
        'bill_info': bill_info,
        'bill_detail': []
    }

    return result


PARSE_FUNCTIONS = {
    "招商银行": parse_cmb_credit_email_html,
    "建设银行": parse_ccb_credit_email_html,
    "农业银行": parse_abc_credit_email_html,
    "中信银行": parse_cncb_credit_email_html,
    "平安银行": parse_pingan_credit_email_html,
    "广发银行": parse_cgb_credit_email_html,
    "交通银行": parse_bocom_credit_email_html,
    "浦发银行": parse_spdb_credit_email_html,
}


def parse_bank_email(bank_name, email_html, subject=""):
    parse_func = PARSE_FUNCTIONS.get(bank_name)
    return parse_func(email_html, subject) if parse_func else {}
