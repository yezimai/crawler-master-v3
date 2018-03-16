from datetime import date, timedelta
from email import message_from_bytes
from email.header import decode_header
from email.parser import Parser
from email.utils import parseaddr
from imaplib import IMAP4
from poplib import POP3, error_proto
from re import compile as re_compile
from traceback import print_exc

from imapclient import IMAPClient

try:
    from cchardet import detect as charset_detect
except ImportError:
    from chardet import detect as charset_detect

# 正误code常量
SUCCESS = 10000
NO_SUITABLE_POP3_ADDRESS = 10001
UNABLE_TO_LOG_ON = 10010
EMPTY_IN_EMAIL = 10011

# 用于根据账号得到pop3地址
POP3_SUFFIX_ADDRESS_DICT = {
    'sina.com': 'pop3.sina.com.cn',
    'sina.cn': 'pop3.sina.com',
    'vip.sina.com': 'pop3.vip.sina.com',
    'sohu.com': 'pop3.sohu.com',
    '126.com': 'pop.126.com',
    '139.com': 'pop.139.com',
    '163.com': 'pop.163.com',
    'qq.com': 'pop.qq.com',
    'yahoo.com': 'pop.mail.yahoo.com',
    'china.com': 'pop.china.com',
    'tom.com': 'pop.tom.com',
    'etang.com': 'pop.etang.com',
}

IMAP4_SUFFIX_ADDRESS_DICT = {
    '126.com': 'imap.126.com',
    'sina.cn': 'imap.sina.cn',
    '163.com': 'imap.163.com',
    'qq.com': 'imap.qq.com',
    '139.com': 'imap.139.com',
    'yahoo.com': 'imap.mail.yahoo.com',
    'china.com': 'imap.china.com',
    'tom.com': 'imap.tom.com',
    'etang.com': 'imap.etang.com',
}

IMAP4_DONT_SEARCH_FOLDER_LIST = ['\\Drafts', '\\Sent']
IMAP4_SEARCH_SINCE_DAY = 90

# 用于判断发件人是否为是银行的
BANK_CREDICT_ADDRESS_DICT = {'PCCC@bocomcc.com': '交通银行',
                             'ccsvc@message.cmbchina.com': '招商银行',
                             'service@vip.ccb.com': '建设银行',
                             'creditcard@cgbchina.com.cn': '广发银行',
                             'citiccard@citiccard.com': '中信银行',
                             'e-statement@creditcard.abchina.com': '农业银行',
                             'creditcard@service.pingan.com': '平安银行',
                             'estmtservice@eb.spdbccc.com.cn': '浦发银行',
                             }

BANK_CREDICT_SUBJECT_DICT = {'招商银行信用卡电子账单': '招商银行',
                             '广发卡': '广发银行',
                             '平安信用卡电子账单': '平安银行',
                             '中信银行信用卡电子账单': '中信银行',
                             '中国建设银行信用卡电子账单': '建设银行',
                             '中国农业银行': '农业银行',
                             '交通银行信用卡电子账单': '交通银行',
                             '浦发银行-信用卡电子账单': '浦发银行',
                             }

CREDIT_CARD_KEYWORD = '账单'


def check_email_credit_card_by_address(subject, address):
    return BANK_CREDICT_ADDRESS_DICT.get(address) if CREDIT_CARD_KEYWORD in subject else None


def check_email_credit_card_by_subject(subject):
    if CREDIT_CARD_KEYWORD in subject:
        for bank_subject_keyword in BANK_CREDICT_SUBJECT_DICT:
            if bank_subject_keyword in subject:
                return BANK_CREDICT_SUBJECT_DICT[bank_subject_keyword]
    return None


def get_email_suffix(email_account):
    """
    邮件账户后缀
    :param email_account:
    :return:
    """
    return email_account.rsplit('@', 1)[-1]


def parse_email_headers(msg):
    address = parseaddr(msg["From"])[1]
    subject, charset = decode_header(msg["Subject"])[0]
    return address, (subject.decode(charset) if charset else subject)


charset_pattren = re_compile(b"""(?:charset|CHARSET)\s*?=\s*?["']?([\w\-]+)["']?""")


def parse_email(msg):
    content = None
    for part in msg.walk():
        if not part.is_multipart():
            content = part.get_payload(decode=True)
            if isinstance(content, bytes):
                charset = part.get_charset()
                if not charset:
                    try:
                        content_type = part.get('Content-Type', '').lower().encode()
                        charset = charset_pattren.search(content_type).group(1).decode()
                        return content.decode(charset)
                    except Exception:
                        try:
                            charset = charset_pattren.search(content).group(1).decode()  # 先搜索charset="xxx"
                        except Exception:
                            charset = charset_detect(content)["encoding"]

                return content.decode(charset)
            else:
                return content

    return content


# 输入邮件地址,pop3客户端验证码（可能与密码不同）:
def get_credit_card_bill_by_pop3(email_account, email_password):
    email_suffix = get_email_suffix(email_account)
    pop3_server_addr = POP3_SUFFIX_ADDRESS_DICT.get(email_suffix, "pop." + email_suffix)

    pop3_server = POP3(pop3_server_addr)
    try:
        try:
            pop3_server.user(email_account)
            pop3_server.pass_(email_password)
        except error_proto:
            raise

        yield True

        email_count, _ = pop3_server.stat()
        # _, mails, _ = pop3_server.list()
        for index in range(1, email_count + 1):
            try:
                _, email_lines, _ = pop3_server.retr(index)  # 索引号从1开始的
                email_content_str = '\r\n'.join(list(map(bytes.decode, email_lines)))
                msg = Parser().parsestr(email_content_str)
            except Exception:
                print_exc()
                continue

            address, subject = parse_email_headers(msg)
            bank_name = check_email_credit_card_by_address(subject, address)
            if bank_name:
                try:
                    content = parse_email(msg)
                except Exception:
                    print_exc()
                    content = '解析邮件正文出错'

                yield (bank_name, subject, content)
    finally:
        pop3_server.quit()


def get_credit_card_bill_by_imap4_old(email_account, email_password):
    email_suffix = get_email_suffix(email_account)
    imap4_server_addr = IMAP4_SUFFIX_ADDRESS_DICT.get(email_suffix, "imap." + email_suffix)

    c = IMAPClient(host=imap4_server_addr)
    try:
        c.login(email_account, email_password)
        yield True

        for folder_type, _, folder_name in c.list_folders():
            folder_ok = True
            folder_type = str(folder_type)
            for t in IMAP4_DONT_SEARCH_FOLDER_LIST:
                if t in folder_type:
                    folder_ok = False
                    break
            if not folder_ok:
                continue

            c.select_folder(folder_name, readonly=True)
            # c.search(['SUBJECT', 'test']) # 搜索 TEXT SUBJECT HEADER 都不行
            since = date.today() - timedelta(days=IMAP4_SEARCH_SINCE_DAY)
            r_ids = c.search(['SINCE', since])
            msgdict = c.fetch(r_ids, ['BODY.PEEK[]'])
            for message_id, message in msgdict.items():
                msg = message_from_bytes(message[b'BODY[]'])
                address, subject = parse_email_headers(msg)
                bank_name = check_email_credit_card_by_address(subject, address)
                if bank_name:
                    try:
                        content = parse_email(msg)
                    except Exception:
                        print_exc()
                        content = '解析邮件正文出错'

                    yield (bank_name, subject, content)

            c.close_folder()
    finally:
        c.logout()


IMAP4_SEARCH_KEYWORD = CREDIT_CARD_KEYWORD.encode('utf-8')


# 返回生成器
def get_credit_card_bill_by_imap4(email_account, email_password):
    email_suffix = get_email_suffix(email_account)
    imap4_server_addr = IMAP4_SUFFIX_ADDRESS_DICT.get(email_suffix, "imap." + email_suffix)

    with IMAP4(imap4_server_addr) as c:
        c.login(email_account, email_password)
        yield True

        _, folders = c.list()
        # 开始搜索所有文件夹
        for x in folders:
            folder_ok = True
            folder_type, _, folder_name = x.decode().split()
            for t in IMAP4_DONT_SEARCH_FOLDER_LIST:
                if t in folder_type:
                    folder_ok = False
                    break
            if not folder_ok:
                continue

            _, __ = c.select(folder_name.strip('"'), readonly=True)
            _, data = c.search(None, 'SUBJECT', IMAP4_SEARCH_KEYWORD)  # 开始筛选带账单的文件
            for y in data[0].split():
                _, mail_data = c.fetch(y, "(RFC822)")
                mail_text = mail_data[0][1]
                msg = message_from_bytes(mail_text)
                address, subject = parse_email_headers(msg)
                bank_name = check_email_credit_card_by_address(subject, address)
                if bank_name:
                    try:
                        content = parse_email(msg)
                    except Exception:
                        print_exc()
                        content = '解析邮件正文出错'

                    yield (bank_name, subject, content)


if __name__ == '__main__':
    email_account = '18702898679@139.com'
    email_password = 'scx1123x'
    # r = get_credit_card_bill_by_pop3(email_account,email_password)
    r = get_credit_card_bill_by_imap4(email_account, email_password)
    print(list(r))
    # get_cookie_str({'a': '123', 'reqtype': 'pc', 'gidinf': 'x099980109ee0d2fbfc853473000c34962de3d8c67db', 'jv': 'bf2481b5621f63cad2bcec28b6820242-HEMt3USO1515377665551'}
    # )
