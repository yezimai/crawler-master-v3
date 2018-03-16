# -*- coding: utf-8 -*-

from scrapy import Spider
from scrapy.selector import Selector
from crawler_bqjr.spiders_settings import ZHENANGXIN_DICT
from crawler_bqjr.items.zhengxin_items import ZhengxinBankItem

import re


class ZhengxinBankSpider(Spider):
    name = ZHENANGXIN_DICT['征信接口']
    # allowed_domains = ["yishanggongyi.com"]
    start_urls = ["file:///C:/Users/think/workspace_spider/crawler/crawler_bqjr/crawler_bqjr/spiders/zhengxin_spiders/zhengxin_bank_test/report_html/4.12.html"]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=ZhengxinBankItem, **kwargs)
        self.ReportNo = ''

    def _extract_replace(self, selector, replace_char=''):
        """
        对解析出的信息做过滤
        :param replace_char:
        :return:
        """
        return selector.extract().replace(replace_char, '').strip()

    def get_keys(self, d, value):
        result = [k for k, v in d.items() if v.find(value) > -1]
        if len(result) > 0:
            return result[0]
        return None

    def html2selector(self, regex, text):
        search = re.search(regex, text, re.S)
        html = search.group(1) if search else ""
        return Selector(text=html)

    def _parse_report_base(self, response, result):
        """
        1、解析报告基本信息
        :param response:
        :param result:
        :return:
        """
        table1_tr3 = response.xpath('//span[@class="style1"]//font[@color="#0066cc"]').xpath('string()')
        # 报告编号
        self.ReportNo = self._extract_replace(table1_tr3[0], '报告编号:')
        # 查询时间
        QueryTime = self._extract_replace(table1_tr3[1], '查询请求时间:')
        # 报告时间
        ReportCreateTime = self._extract_replace(table1_tr3[2], '报告时间:')
        table2_tr1 = response.xpath('//table[@width="620"]/*/tr[1]//div[@class="high"]').xpath('string()')
        # 姓名
        Name = self._extract_replace(table2_tr1[0])
        # 证件类型
        CertType = self._extract_replace(table2_tr1[1])
        # 证件号码
        CertNo = self._extract_replace(table2_tr1[2])
        # 查询操作员
        Operate = self._extract_replace(table2_tr1[3]).split('/')
        OperateOrg = Operate[0]
        OperateUser = Operate[1] if len(Operate) == 2 else ''
        # 查询原因
        QueryReason = self._extract_replace(table2_tr1[4])
        # 未知信息
        QueryMode = ''
        ReportPath = ''
        ReportResource = ''
        ReportType = ''
        result["ReportNo"] = self.ReportNo
        result["ReportDescribe"] = {
            "CertNo": CertNo,
            "CertType": CertType,
            "Name": Name,
            "OperateOrg": OperateOrg,
            "OperateUser": OperateUser,
            "QueryMode": QueryMode,
            "QueryReason": QueryReason,
            "QueryTime": QueryTime,
            "ReportCreateTime": ReportCreateTime,
            "ReportNo": self.ReportNo,
            "ReportPath": ReportPath,
            "ReportResource": ReportResource,
            "ReportType": ReportType
        }
        result["ReportData"] = {
            "PartList": []
        }
        PartList = result["ReportData"]["PartList"]
        # table1中的数据（个人信用报告所在表格）对应json格式
        table1_json = {
            "BizObjectClass": {
                "Attributes": {
                    "QueryTime": "查询请求时间",
                    "ReportCreateTime": "报告生成时间",
                    "ReportNo": "报告编号"
                },
                "ClassLabel": "报告头",
                "ClassName": "jbo.crq.icr.MessageHeader"
            },
            "Content": [
                {
                    "QueryTime": QueryTime,
                    "ReportCreateTime": ReportCreateTime,
                    "ReportNo": self.ReportNo
                }
            ],
            "Id": "00",
            "JboClass": "jbo.crq.icr.MessageHeader",
            "Label": "报告头信息",
            "Multi": False,
            "Name": "MessageHeader",
            "Properties": {
                "REPORTNONODE": "true"
            }
        }
        PartList.append(table1_json)

        # table2中的数据（个人信用报告下方表格）对应json格式
        table2_json = {
            "BizObjectClass": {
                "Attributes": {
                    "Certno": "被查询者证件号码",
                    "Certtype": "被查询者证件类型",
                    "Name": "被查询者姓名",
                    "QueryReason": "查询原因",
                    "ReportNo": "报告编号",
                    "UserCode": "查询操作员"
                },
                "ClassLabel": "查询信息",
                "ClassName": "jbo.crq.icr.QueryReq"
            },
            "Content": [
                {
                    "Certno": CertNo,
                    "Certtype": CertType,
                    "Name": Name,
                    "QueryReason": QueryReason,
                    "ReportNo": self.ReportNo,
                    "UserCode": "/".join(Operate)
                }
            ],
            "Id": "0",
            "JboClass": "jbo.crq.icr.QueryReq",
            "Label": "查询信息",
            "Multi": False,
            "Name": "QueryReq"
        }
        PartList.append(table2_json)

        return result

    def _parse_report_personal(self, response, result):
        """
        2、解析个人基本信息
        :param response:
        :param result:
        :return:
        """
        PartList = result["ReportData"]["PartList"]
        ChapterList = []
        Gender = Birthday = MaritalState = Mobile = OfficeTelephoneNo = HomeTelephoneNo = EduLevel = \
        EduDegree = PostAddress = RegisteredAddress = ''
        if response.text.find('身份信息') > -1:
            # 解析个人基本信息（身份信息）
            table2_tr5 = response.xpath('//table[@width="620"]/*/tr[5]//div[@align]/font[@color]').xpath('string()')
            # 性别
            Gender = self._extract_replace(table2_tr5[0])
            # 出生日期
            Birthday = self._extract_replace(table2_tr5[1])
            # 婚姻状况
            MaritalState = self._extract_replace(table2_tr5[2])
            # 手机号码
            Mobile = self._extract_replace(table2_tr5[3])
            # 单位电话
            OfficeTelephoneNo = self._extract_replace(table2_tr5[4])
            # 住宅电话
            HomeTelephoneNo = self._extract_replace(table2_tr5[5])
            # 学历
            EduLevel = self._extract_replace(table2_tr5[6])
            # 学位
            EduDegree = self._extract_replace(table2_tr5[7])
            # 通讯地址
            PostAddress = self._extract_replace(table2_tr5[8])
            # 户籍地址
            RegisteredAddress = self._extract_replace(table2_tr5[9])
        ICRIdentity = {
            "BizObjectClass": {
                "Attributes": {
                    "Birthday": "出生日期",
                    "EduDegree": "学位",
                    "EduLevel": "学历",
                    "Gender": "性别",
                    "HomeTelephoneNo": "住宅电话",
                    "MaritalState": "婚姻状况",
                    "Mobile": "手机号码",
                    "OfficeTelephoneNo": "单位电话",
                    "PostAddress": "通讯地址",
                    "RegisteredAddress": "户籍地址",
                    "ReportNo": "报告编号"
                },
                "ClassLabel": "身份信息",
                "ClassName": "jbo.crq.icr.ICRIdentity"
            },
            "Content": [
                {
                    "Birthday": Birthday,
                    "EduDegree": EduDegree,
                    "EduLevel": EduLevel,
                    "Gender": Gender,
                    "HomeTelephoneNo": HomeTelephoneNo,
                    "MaritalState": MaritalState,
                    "Mobile": Mobile,
                    "OfficeTelephoneNo": OfficeTelephoneNo,
                    "PostAddress": PostAddress,
                    "RegisteredAddress": RegisteredAddress,
                    "ReportNo": self.ReportNo
                }
            ],
            "Id": "1.1",
            "JboClass": "jbo.crq.icr.ICRIdentity",
            "Label": "身份信息",
            "Multi": False,
            "Name": "Identity",
            "Properties": {
                "MULTI": "false"
            }
        }
        ChapterList.append(ICRIdentity)
        # 解析个人基本信息（配偶信息）
        Name = Certtype = Certno = Employer = TelephoneNo = ''
        if response.text.find('配偶信息') > -1:
            table2_tr7 = response.xpath('//table[@width="620"]/*/tr[7]//div[@align]/font[@color]').xpath('string()')
            # 姓名
            Name = self._extract_replace(table2_tr7[0])
            # 证件类型
            Certtype = self._extract_replace(table2_tr7[1])
            # 证件号码
            Certno = self._extract_replace(table2_tr7[2])
            # 工作单位
            Employer = self._extract_replace(table2_tr7[3])
            # 联系电话
            TelephoneNo = self._extract_replace(table2_tr7[4])
        ICRSpouse = {
            "BizObjectClass": {
                "Attributes": {
                    "Certno": "证件号码",
                    "Certtype": "证件类型",
                    "Employer": "工作单位",
                    "Name": "姓名",
                    "ReportNo": "报告编号",
                    "TelephoneNo": "联系电话"
                },
                "ClassLabel": "配偶信息",
                "ClassName": "jbo.crq.icr.ICRSpouse"
            },
            "Content": [
                {
                    "Certno": Certno,
                    "Certtype": Certtype,
                    "Employer": Employer,
                    "Name": Name,
                    "ReportNo": self.ReportNo,
                    "TelephoneNo": TelephoneNo
                }
            ],
            "Id": "1.2",
            "JboClass": "jbo.crq.icr.ICRSpouse",
            "Label": "配偶信息",
            "Multi": False,
            "Name": "Spouse",
            "Properties": {
                "MULTI": "false"
            }
        }
        ChapterList.append(ICRSpouse)
        # 解析个人基本信息（居住信息）
        if response.text.find('居住信息') > -1:
            table2_tr9 = response.xpath('//table[@width="620"]/*/tr[9]//tbody/tr[position()>1]')
            # 遍历居住信息
            Residence = []
            for tr in table2_tr9:
                Address = self._extract_replace(tr.xpath('td[2]').xpath('string()')[0])
                ResidenceType = self._extract_replace(tr.xpath('td[3]').xpath('string()')[0])
                GetTime = self._extract_replace(tr.xpath('td[4]').xpath('string()')[0])
                data = {
                    "Address": Address,
                    "GetTime": GetTime,
                    "ReportNo": self.ReportNo,
                    "ResidenceType": ResidenceType
                }
                Residence.append(data)
            ICRResidence = {
                "BizObjectClass": {
                    "Attributes": {
                        "Address": "居住地址",
                        "GetTime": "信息更新日期",
                        "ReportNo": "报告编号",
                        "ResidenceType": "居住状况",
                        "SerialNo": "流水号"
                    },
                    "ClassLabel": "居住信息",
                    "ClassName": "jbo.crq.icr.ICRResidence"
                },
                "Content": Residence,
                "Id": "1.3",
                "JboClass": "jbo.crq.icr.ICRResidence",
                "Label": "居住信息",
                "Multi": True,
                "Name": "Residence",
                "Properties": {
                    "MULTI": "true"
                }
            }
            ChapterList.append(ICRResidence)
        # 解析个人基本信息（职业信息）
        if response.text.find('职业信息') > -1:
            table2_tr11 = response.xpath('//table[@width="620"]/*/tr[11]//tbody/tr')
            middle = int(len(table2_tr11) / 2) + 1
            table2_tr11_address = response.xpath('//table[@width="620"]/*/tr[11]//tbody/tr[position()>1 and position()< %d]' % middle)
            table2_tr11_duty = response.xpath('//table[@width="620"]/*/tr[11]//tbody/tr[position()>%d]' % middle)
            Professional = []
            for index in range(len(table2_tr11_address)):
                Employer = self._extract_replace(table2_tr11_address[index].xpath('td[2]').xpath('string()')[0])
                EmployerAddress = self._extract_replace(table2_tr11_address[index].xpath('td[3]').xpath('string()')[0])
                Occupation = self._extract_replace(table2_tr11_duty[index].xpath('td[2]').xpath('string()')[0])
                Industry = self._extract_replace(table2_tr11_duty[index].xpath('td[3]').xpath('string()')[0])
                Duty = self._extract_replace(table2_tr11_duty[index].xpath('td[4]').xpath('string()')[0])
                Title = self._extract_replace(table2_tr11_duty[index].xpath('td[5]').xpath('string()')[0])
                StartYear = self._extract_replace(table2_tr11_duty[index].xpath('td[6]').xpath('string()')[0])
                GetTime = self._extract_replace(table2_tr11_duty[index].xpath('td[7]').xpath('string()')[0])
                data = {
                    "Duty": Duty,
                    "Employer": Employer,
                    "EmployerAddress": EmployerAddress,
                    "GetTime": GetTime,
                    "Industry": Industry,
                    "Occupation": Occupation,
                    "ReportNo": self.ReportNo,
                    "StartYear": StartYear,
                    "Title": Title
                }
                Professional.append(data)
            ICRProfessional = {
                "BizObjectClass": {
                    "Attributes": {
                        "Duty": "职务",
                        "Employer": "工作单位",
                        "EmployerAddress": "单位地址",
                        "GetTime": "信息更新日期",
                        "Industry": "行业",
                        "Occupation": "职业",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号",
                        "StartYear": "进入本单位年份",
                        "Title": "职称"
                    },
                    "ClassLabel": "职业信息",
                    "ClassName": "jbo.crq.icr.ICRProfessional"
                },
                "Content": Professional,
                "Id": "1.4",
                "JboClass": "jbo.crq.icr.ICRProfessional",
                "Label": "职业信息",
                "Multi": True,
                "Name": "Professional",
                "Properties": {
                    "MULTI": "true"
                }
            }
            ChapterList.append(ICRProfessional)
        PartList.append({
            "ChapterList": ChapterList,
            "Id": "1",
            "Label": "个人基本信息",
            "Multi": False,
            "Name": "PersonalInfo"
        })
        return result

    def _parse_report_summary(self, response, result):
        """
        3、解析贷款信息概要
        :param response:
        :param result:
        :return:
        """
        PartList = result["ReportData"]["PartList"]
        ChapterList = []
        SectionList = []
        # 解析信用提示
        regex = r'信用提示</b>(.*?)<tr height=.+? valign="bottom">'
        # 解析查询记录汇总
        selector = self.html2selector(regex, response.text)
        # 信用提示表格
        info_summary_table1_header = selector.xpath('//tr/td/div/table//tr[1]/td').xpath('string()')
        info_summary_table1_body = selector.xpath('//tr/td/div/table//tr[2]/td').xpath('string()')
        keys = {
            "AnnounceCount": "本人声明数目",
            "DissentCount": "异议标注数目",
            "FirstLoanOpenMonth": "首笔贷款发放月份",
            "FirstLoancardOpenMonth": "首张贷记卡发卡月份",
            "FirstStandardLoancardOpenMonth": "首张准贷记卡发卡月份",
            "HouseLoan2Count": "个人商用房（包括商住两用）贷款笔数",
            "HouseLoanCount": "个人住房贷款笔数",
            "LoancardCount": "贷记卡账户数",
            "Month": "评分月份",
            "OtherLoanCount": "其他贷款笔数",
            "ReportNo": "报告编号",
            "Score": "中征信评分",
            "StandardLoancardCount": "准贷记卡账户数"
        }
        keys_new = {}.fromkeys(keys, "")
        for (i, header) in enumerate(info_summary_table1_header):
            key = self.get_keys(keys, self._extract_replace(header))
            if key:
                keys_new[key] = self._extract_replace(info_summary_table1_body[i])
        Section = {
            "BizObjectClass": {
                "Attributes": keys,
                "ClassLabel": "信用提示",
                "ClassName": "jbo.crq.icr.ICRCreditCue"
            },
            "Content": [
                keys_new,
            ],
            "Id": "2.1.1",
            "JboClass": "jbo.crq.icr.ICRCreditCue",
            "Label": "信用提示",
            "Multi": False,
            "Name": "CreditCue",
            "Properties": {
                "MULTI": "false"
            }
        }
        SectionList.append(Section)
        # 解析个人信用报告“数字解读”
        regex = r'<b>个人信用报告“数字解读”</b>(.*?)<tr height=.+? valign="bottom">'
        # 解析查询记录汇总
        selector = self.html2selector(regex, response.text)
        # 数字解读表格
        info_summary_table2 = selector.xpath('//tr/td/table//tr[2]/td').xpath('string()')
        DigitalInterpretation = RelativePosition = Illustration = ''
        if len(info_summary_table2) > 0:
            # 数字解读
            DigitalInterpretation = self._extract_replace(info_summary_table2[0])
            # 相对位置
            RelativePosition = self._extract_replace(info_summary_table2[1])
            # 说明
            Illustration = self._extract_replace(info_summary_table2[2])
        Section = {
            "BizObjectClass": {
                "Attributes": {
                    "DigitalInterpretation": "数字解读",
                    "Illustration": "说明",
                    "RelativePosition": "相对位置",
                    "ReportNo": "报告编号"
                },
                "ClassLabel": "个人信用报告“数字解读”",
                "ClassName": "jbo.crq.icr.ICRDigitalInterpretation"
            },
            "Content": [
                {
                    "DigitalInterpretation": DigitalInterpretation,
                    "Illustration": Illustration,
                    "RelativePosition": RelativePosition,
                    "ReportNo": self.ReportNo
                }
            ],
            "Id": "2.1.2",
            "JboClass": "jbo.crq.icr.ICRDigitalInterpretation",
            "Label": "个人信用报告“数字解读”",
            "Multi": False,
            "Name": "DigitalInterpretation",
            "Properties": {
                "MULTI": "false"
            }
        }
        SectionList.append(Section)
        ChapterList.append({
            "Id": "2.1",
            "Label": "信用提示",
            "Multi": False,
            "Name": "Cue",
            "SectionList": SectionList
        })
        # 呆账信息
        regex = r'呆账信息汇总(.*?)<tr height=.+? valign="bottom">'
        selector = self.html2selector(regex, response.text)
        bad_debt_table_td = selector.xpath('//tr[2]/td').xpath('string()')
        bad_debt_Count = bad_debt_Balance = bad_debt_Count2 = bad_debt_Balance2 = \
        bad_debt_Count3 = bad_debt_Balance3 = ''
        if len(bad_debt_table_td) > 0:
            # 呆账信息笔数
            bad_debt_Count = self._extract_replace(bad_debt_table_td[0])
            # 呆账信息余额
            bad_debt_Balance = self._extract_replace(bad_debt_table_td[1], ',')
            # 资产处置信息笔数
            bad_debt_Count2 = self._extract_replace(bad_debt_table_td[2])
            # 资产处置信息余额
            bad_debt_Balance2 = self._extract_replace(bad_debt_table_td[3], ',')
            # 保证人代偿信息笔数
            bad_debt_Count3 = self._extract_replace(bad_debt_table_td[4])
            # 保证人代偿信息余额
            bad_debt_Balance3 = self._extract_replace(bad_debt_table_td[5], ',')
        # 解析逾期及违约信息概要
        regex = r'逾期（透支）信息汇总</b>(.*?)<tr height=.+? valign="bottom">'
        # 解析查询记录汇总
        selector = self.html2selector(regex, response.text)
        # 逾期（透支）信息汇总表格
        info_summary_table3_body = selector.xpath('//tr/td/div/table//tr[3]/td').xpath('string()')
        Count = Months = HighestOverdueAmountPerMon = MaxDuration = Count2 = Months2= \
        HighestOverdueAmountPerMon2 = MaxDuration2 = Count3 = Months3 = \
        HighestOverdueAmountPerMon3 = MaxDuration3 = ""
        if len(info_summary_table3_body) > 0:
            # 笔数(贷款逾期)
            Count = self._extract_replace(info_summary_table3_body[0])
            # 月份数（贷款逾期）
            Months = self._extract_replace(info_summary_table3_body[1])
            # 单月最高逾期总额（贷款逾期）
            HighestOverdueAmountPerMon = self._extract_replace(info_summary_table3_body[2], ',')
            # 最长逾期月数（贷款逾期）
            MaxDuration = self._extract_replace(info_summary_table3_body[3])
            # 账户数（贷记卡逾期）
            Count2 = self._extract_replace(info_summary_table3_body[4])
            # 月份数（贷记卡逾期）
            Months2 = self._extract_replace(info_summary_table3_body[5])
            # 单月最高逾期总额（贷记卡逾期）
            HighestOverdueAmountPerMon2 = self._extract_replace(info_summary_table3_body[6], ',')
            # 最长逾期月数（贷记卡逾期）
            MaxDuration2 = self._extract_replace(info_summary_table3_body[7])
            # 账户数（准贷记卡60天以上透支）
            Count3 = self._extract_replace(info_summary_table3_body[8])
            # 月份数（准贷记卡60天以上透支）
            Months3 = self._extract_replace(info_summary_table3_body[9])
            # 单月最高透支余额（准贷记卡60天以上透支）
            HighestOverdueAmountPerMon3 = self._extract_replace(info_summary_table3_body[10], ',')
            # 最长透支月数（准贷记卡60天以上透支）
            MaxDuration3 = self._extract_replace(info_summary_table3_body[11])
        ChapterList.append({
            "Id": "2.2",
            "Label": "逾期及违约信息概要",
            "Multi": False,
            "Name": "OverdueAndFellback",
            "SectionList": [
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "Balance": "呆账信息余额",
                            "Balance2": "资产处置信息余额",
                            "Balance3": "保证人代偿信息余额",
                            "Count": "呆账信息笔数",
                            "Count2": "资产处置信息笔数",
                            "Count3": "保证人代偿信息笔数",
                            "ReportNo": "报告编号"
                        },
                        "ClassLabel": "呆账、资产处置、保证人代偿信息概要",
                        "ClassName": "jbo.crq.icr.ICRFellbackSummary"
                    },
                    "Content": [
                        {
                            "ReportNo": self.ReportNo,
                            "Count": bad_debt_Count,
                            "Balance": bad_debt_Balance,
                            "Count2": bad_debt_Count2,
                            "Balance2": bad_debt_Balance2,
                            "Count3": bad_debt_Count3,
                            "Balance3": bad_debt_Balance3
                        }
                    ],
                    "Id": "2.2.1",
                    "JboClass": "jbo.crq.icr.ICRFellbackSummary",
                    "Label": "呆账、资产处置、保证人代偿信息概要",
                    "Multi": False,
                    "Name": "FellbackSummary",
                    "Properties": {
                        "MULTI": "false"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "Count": "贷款逾期笔数",
                            "Count2": "贷记卡逾期笔数",
                            "Count3": "准贷记卡60天以上透支笔数",
                            "HighestOverdueAmountPerMon": "贷款逾期单月最高逾期总额",
                            "HighestOverdueAmountPerMon2": "贷记卡逾期单月最高逾期总额",
                            "HighestOverdueAmountPerMon3": "准贷记卡60天以上透支单月最高逾期总额",
                            "MaxDuration": "贷款逾期最长逾期月数",
                            "MaxDuration2": "贷记卡逾期最长逾期月数",
                            "MaxDuration3": "准贷记卡60天以上透支最长逾期月数",
                            "Months": "贷款逾期月份数",
                            "Months2": "贷记卡逾期月份数",
                            "Months3": "准贷记卡60天以上透支月份数",
                            "ReportNo": "报告编号"
                        },
                        "ClassLabel": "逾期(透支)信息汇总",
                        "ClassName": "jbo.crq.icr.ICROverdueSummary"
                    },
                    "Content": [
                        {
                            "Count": int(Count) if Count else "",
                            "Count2": int(Count2) if Count2 else "",
                            "Count3": int(Count3) if Count3 else "",
                            "HighestOverdueAmountPerMon": round(float(HighestOverdueAmountPerMon), 1) if HighestOverdueAmountPerMon else "",
                            "HighestOverdueAmountPerMon2": round(float(HighestOverdueAmountPerMon2), 1) if HighestOverdueAmountPerMon2 else "",
                            "HighestOverdueAmountPerMon3": round(float(HighestOverdueAmountPerMon3), 1) if HighestOverdueAmountPerMon3 else "",
                            "MaxDuration": int(MaxDuration) if MaxDuration else "",
                            "MaxDuration2": int(MaxDuration2) if MaxDuration2 else "",
                            "MaxDuration3": int(MaxDuration3) if MaxDuration3 else "",
                            "Months": int(Months) if Months else "",
                            "Months2": int(Months2) if Months2 else "",
                            "Months3": int(Months3) if Months3 else "",
                            "ReportNo": self.ReportNo
                        }
                    ],
                    "Id": "2.2.2",
                    "JboClass": "jbo.crq.icr.ICROverdueSummary",
                    "Label": "逾期（透支）信息汇总",
                    "Multi": False,
                    "Name": "OverdueSummary",
                    "Properties": {
                        "MULTI": "false"
                    }
                }
            ]
        })

        # 解析授信及负债信息概要
        regex = r'未结清贷款信息汇总</b></font>(.*?)<tr height=.+? valign="bottom">'
        selector = self.html2selector(regex, response.text)
        # 未结清贷款信息汇总表格
        info_summary_table4_body = selector.xpath('//tr/td/table//tr[2]/td').xpath('string()')
        FinanceCorpCount = FinanceOrgCount = AccountCount = CreditLimit = Balance = \
        Latest6MonthUsedAvgAmount = ""
        if len(info_summary_table4_body) > 0:
            # 贷款法人机构数
            FinanceCorpCount = self._extract_replace(info_summary_table4_body[0])
            # 贷款机构数
            FinanceOrgCount = self._extract_replace(info_summary_table4_body[1])
            # 笔数
            AccountCount = self._extract_replace(info_summary_table4_body[2])
            # 合同总额
            CreditLimit = self._extract_replace(info_summary_table4_body[3], ',')
            # 余额
            Balance = self._extract_replace(info_summary_table4_body[4], ',')
            # 最近6个月平均应还款
            Latest6MonthUsedAvgAmount = self._extract_replace(info_summary_table4_body[5], ',')
        SectionList = []
        Section = {
            "BizObjectClass": {
                "Attributes": {
                    "AccountCount": "笔数",
                    "Balance": "余额",
                    "CreditLimit": "合同总额",
                    "FinanceCorpCount": "贷款法人机构数",
                    "FinanceOrgCount": "贷款机构数",
                    "Latest6MonthUsedAvgAmount": "最近6个月平均应还款",
                    "ReportNo": "报告编号"
                },
                "ClassLabel": "未结清贷款信息汇总",
                "ClassName": "jbo.crq.icr.ICRUnpaidLoan"
            },
            "Content": [
                {
                    "AccountCount": int(AccountCount) if AccountCount else "",
                    "Balance": round(float(Balance), 1) if Balance else "",
                    "CreditLimit": round(float(CreditLimit), 1) if CreditLimit else "",
                    "FinanceCorpCount": int(FinanceCorpCount) if FinanceCorpCount else "",
                    "FinanceOrgCount": int(FinanceOrgCount) if FinanceOrgCount else "",
                    "Latest6MonthUsedAvgAmount": round(float(Latest6MonthUsedAvgAmount), 1) if Latest6MonthUsedAvgAmount else "",
                    "ReportNo": self.ReportNo
                }
            ],
            "Id": "2.3.1",
            "JboClass": "jbo.crq.icr.ICRUnpaidLoan",
            "Label": "未结清贷款信息汇总",
            "Multi": False,
            "Name": "UnpaidLoan",
            "Properties": {
                "MULTI": "false"
            }
        }
        SectionList.append(Section)
        # 未销户贷记卡信息汇总表格
        regex = r'未销户贷记卡信息汇总</b></font>(.*?)<tr height=.+? valign="bottom">'
        selector = self.html2selector(regex, response.text)
        info_summary_table5_body = selector.xpath('//tr/td/div/table//tr[2]/td').xpath('string()')
        FinanceCorpCount = FinanceOrgCount = AccountCount = CreditLimit = \
        MaxCreditLimitPerOrg = MinCreditLimitPerOrg = UsedCreditLimit = \
        Latest6MonthUsedAvgAmount = ""
        if len(info_summary_table5_body) > 0:
            # 发卡法人机构数
            FinanceCorpCount = self._extract_replace(info_summary_table5_body[0])
            # 发卡机构数
            FinanceOrgCount = self._extract_replace(info_summary_table5_body[1])
            # 账户数
            AccountCount = self._extract_replace(info_summary_table5_body[2])
            # 授信总额
            CreditLimit = self._extract_replace(info_summary_table5_body[3], ',')
            # 单家行最高授信额
            MaxCreditLimitPerOrg = self._extract_replace(info_summary_table5_body[4], ',')
            # 单家行最低授信额
            MinCreditLimitPerOrg = self._extract_replace(info_summary_table5_body[5], ',')
            # 已用额度
            UsedCreditLimit = self._extract_replace(info_summary_table5_body[6], ',')
            # 最近6个月平均使用额度
            Latest6MonthUsedAvgAmount = self._extract_replace(info_summary_table5_body[7], ',')
        Section = {
            "BizObjectClass": {
                "Attributes": {
                    "AccountCount": "账户数",
                    "CreditLimit": "授信总额",
                    "FinanceCorpCount": "发卡法人机构数",
                    "FinanceOrgCount": "发卡机构数",
                    "Latest6MonthUsedAvgAmount": "最近6个月平均使用额度",
                    "MaxCreditLimitPerOrg": "单家行最高授信额",
                    "MinCreditLimitPerOrg": "单家行最低授信额",
                    "ReportNo": "报告编号",
                    "UsedCreditLimit": "已用额度"
                },
                "ClassLabel": "未销户贷记卡信息汇总",
                "ClassName": "jbo.crq.icr.ICRUndestoryLoancard"
            },
            "Content": [
                {
                    "AccountCount": int(AccountCount) if AccountCount else "",
                    "CreditLimit": round(float(CreditLimit), 1) if CreditLimit else "",
                    "FinanceCorpCount": int(FinanceCorpCount) if FinanceCorpCount else "",
                    "FinanceOrgCount": int(FinanceOrgCount) if FinanceOrgCount else "",
                    "Latest6MonthUsedAvgAmount": round(float(Latest6MonthUsedAvgAmount), 1) if Latest6MonthUsedAvgAmount else "",
                    "MaxCreditLimitPerOrg": round(float(MaxCreditLimitPerOrg), 1) if MaxCreditLimitPerOrg else "",
                    "MinCreditLimitPerOrg": round(float(MinCreditLimitPerOrg), 1) if MinCreditLimitPerOrg else "",
                    "ReportNo": self.ReportNo,
                    "UsedCreditLimit": round(float(UsedCreditLimit), 1) if UsedCreditLimit else ""
                }
            ],
            "Id": "2.3.2",
            "JboClass": "jbo.crq.icr.ICRUndestoryLoancard",
            "Label": "未销户贷记卡信息汇总",
            "Multi": False,
            "Name": "UndestoryLoancard",
            "Properties": {
                "MULTI": "false"
            }
        }
        SectionList.append(Section)
        # 未销户准贷记卡信息汇总表格
        regex = r'未销户准贷记卡信息汇总</b></font>(.*?)<tr style="line-height:15px">'
        selector = self.html2selector(regex, response.text)
        info_summary_table5_body = selector.xpath('//tr/td/div/table//tr[2]/td').xpath('string()')
        FinanceCorpCount = FinanceOrgCount = AccountCount = CreditLimit = \
            MaxCreditLimitPerOrg = MinCreditLimitPerOrg = UsedCreditLimit = \
            Latest6MonthUsedAvgAmount = ""
        if len(info_summary_table5_body) > 0:
            # 发卡法人机构数
            FinanceCorpCount = self._extract_replace(info_summary_table5_body[0])
            # 发卡机构数
            FinanceOrgCount = self._extract_replace(info_summary_table5_body[1])
            # 账户数
            AccountCount = self._extract_replace(info_summary_table5_body[2])
            # 授信总额
            CreditLimit = self._extract_replace(info_summary_table5_body[3], ',')
            # 单家行最高授信额
            MaxCreditLimitPerOrg = self._extract_replace(info_summary_table5_body[4], ',')
            # 单家行最低授信额
            MinCreditLimitPerOrg = self._extract_replace(info_summary_table5_body[5], ',')
            # 已用额度
            UsedCreditLimit = self._extract_replace(info_summary_table5_body[6], ',')
            # 最近6个月平均使用额度
            Latest6MonthUsedAvgAmount = self._extract_replace(info_summary_table5_body[7], ',')
        Section = {
            "BizObjectClass": {
                "Attributes": {
                    "AccountCount": "账户数",
                    "CreditLimit": "授信总额",
                    "FinanceCorpCount": "发卡法人机构数",
                    "FinanceOrgCount": "发卡机构数",
                    "Latest6MonthUsedAvgAmount": "最近6个月平均使用额度",
                    "MaxCreditLimitPerOrg": "单家行最高授信额",
                    "MinCreditLimitPerOrg": "单家行最低授信额",
                    "ReportNo": "报告编号",
                    "UsedCreditLimit": "透支余额"
                },
                "ClassLabel": "未销户准贷记卡信息汇总",
                "ClassName": "jbo.crq.icr.ICRUndestoryStandardLoancard"
            },
            "Content": [
                {
                    "AccountCount": int(AccountCount) if AccountCount else "",
                    "CreditLimit": round(float(CreditLimit), 1) if CreditLimit else "",
                    "FinanceCorpCount": int(FinanceCorpCount) if FinanceCorpCount else "",
                    "FinanceOrgCount": int(FinanceOrgCount) if FinanceOrgCount else "",
                    "Latest6MonthUsedAvgAmount": round(float(Latest6MonthUsedAvgAmount),
                                                       1) if Latest6MonthUsedAvgAmount else "",
                    "MaxCreditLimitPerOrg": round(float(MaxCreditLimitPerOrg), 1) if MaxCreditLimitPerOrg else "",
                    "MinCreditLimitPerOrg": round(float(MinCreditLimitPerOrg), 1) if MinCreditLimitPerOrg else "",
                    "ReportNo": self.ReportNo,
                    "UsedCreditLimit": round(float(UsedCreditLimit), 1) if UsedCreditLimit else ""
                }
            ],
            "Id": "2.3.3",
            "JboClass": "jbo.crq.icr.ICRUndestoryStandardLoancard",
            "Label": "未销户准贷记卡信息汇总",
            "Multi": False,
            "Name": "UndestoryStandardLoancard",
            "Properties": {
                "MULTI": "false"
            }
        }
        SectionList.append(Section)
        # 对外担保信息表格
        regex = r'对外担保信息汇总</b></font>(.*?)<tr height=.+? valign="bottom">'
        selector = self.html2selector(regex, response.text)
        info_summary_table6_body = selector.xpath('//tr/td/div/table//tr[2]/td').xpath('string()')
        Count = Amount = Balance = ""
        if len(info_summary_table6_body) > 0:
            # 担保笔数
            Count = self._extract_replace(info_summary_table6_body[0], ',')
            # 担保金额
            Amount = self._extract_replace(info_summary_table6_body[1], ',')
            # 担保本金余额
            Balance = self._extract_replace(info_summary_table6_body[2], ',')
        SectionList.append({
            "BizObjectClass": {
                "Attributes": {
                    "Amount": "担保金额",
                    "Balance": "担保本金余额",
                    "Count": "担保笔数",
                    "ReportNo": "报告编号"
                },
                "ClassLabel": "对外担保信息汇总",
                "ClassName": "jbo.crq.icr.ICRGuaranteeSummary"
            },
            "Id": "2.3.4",
            "JboClass": "jbo.crq.icr.ICRGuaranteeSummary",
            "Content": [
                {
                    "ReportNo": self.ReportNo,
                    "Count": int(Count) if Count else "",
                    "Amount": round(float(Amount), 1) if Amount else "",
                    "Balance": round(float(Balance), 1) if Balance else ""
                }
            ],
            "Label": "对外担保信息汇总",
            "Multi": False,
            "Name": "GuaranteeSummary",
            "Properties": {
                "MULTI": "false"
            }
        })
        ChapterList.append({
            "Id": "2.3",
            "Label": "授信及负债信息概要",
            "Multi": False,
            "Name": "ShareAndDebt",
            "SectionList": SectionList
        })

        PartList.append({
            "ChapterList": ChapterList,
            "Id": "2",
            "Label": "信息概要",
            "Multi": False,
            "Name": "InfoSummary"
        })
        return result

    def _parse_report_loan_detail(self, response, result):
        """
        4、信贷交易信息明细
        :param response:
        :param result:
        :return:
        """
        PartList = result["ReportData"]["PartList"]
        ChapterList = []
        SectionListMap = {}
        ChapterList.append({
            "BizObjectClass": {
                "Attributes": {
                    "Balance": "余额",
                    "GetTime": "债务接收日期",
                    "LatestRepayDate": "最近一次还款日期",
                    "Money": "接收的债权金额",
                    "Organname": "资产管理公司",
                    "ReportNo": "报告编号",
                    "SerialNo": "流水号"
                },
                "ClassLabel": "资产处置信息",
                "ClassName": "jbo.crq.icr.ICRAssetDisposition"
            },
            "Id": "3.1",
            "JboClass": "jbo.crq.icr.ICRAssetDisposition",
            "Label": "资产处置信息",
            "Multi": True,
            "Name": "AssetDisposition",
            "Properties": {
                "MULTI": "true"
            }
        })
        ChapterList.append({
            "BizObjectClass": {
                "Attributes": {
                    "Balance": "余额",
                    "LatestAssurerRepayDate": "最近一次代偿日期",
                    "LatestRepayDate": "最近一次还款日期",
                    "Money": "累计代偿金额",
                    "Organname": "代偿机构",
                    "ReportNo": "报告编号",
                    "SerialNo": "流水号"
                },
                "ClassLabel": "保证人代偿信息",
                "ClassName": "jbo.crq.icr.ICRAssurerRepay"
            },
            "Id": "3.2",
            "JboClass": "jbo.crq.icr.ICRAssurerRepay",
            "Label": "保证人代偿信息",
            "Multi": True,
            "Name": "AssurerRepay",
            "Properties": {
                "MULTI": "true"
            }
        })
        # 解析贷款
        # 解析<!--贷款明细信息-->到<!--信用卡明细信息-->之间的内容（此间为贷款信息）
        regex = r'<!--贷款明细(.*?)<!--信用卡明细'
        selector = self.html2selector(regex, response.text)
        # 从结果中筛选
        regex = r'<tr height=35 .*?<span class=high>(.*?)</span>.*?<tbody>(.*?)</tbody>'
        loan_list = re.findall(regex, selector.response.text, re.S)
        for (i,loan) in enumerate(loan_list):
            keys = {
                "Account": "业务号",
                "ActualPaymentAmount": "本月实还款",
                "BadBalance": "呆帐余额",
                "Balance": "本金余额",
                "BeginMonth": "还款起始月",
                "Class5State": "五级分类",
                "CreditLimitAmount": "合同金额",
                "Cue": "描述信息",
                "CueSerialNo": "描述信息序号",
                "CurrOverdueAmount": "当前逾期金额",
                "CurrOverdueCyc": "当前逾期期数",
                "Currency": "币种",
                "EndDate": "到期日期",
                "EndMonth": "还款截止月",
                "FinanceOrg": "贷款机构",
                "FinanceType": "授信机构类型",
                "GuaranteeType": "担保方式",
                "Latest24State": "24个月还款状态",
                "OpenDate": "发放日期",
                "Overdue31To60Amount": "逾期31—60天未还本金",
                "Overdue61To90Amount": "逾期61－90天未还本金",
                "Overdue91To180Amount": "逾期91－180天未还本金",
                "OverdueOver180Amount": "逾期180天以上未还本金",
                "PaymentCyc": "还款期数",
                "PaymentRating": "还款频率",
                "RecentPayDate": "最近一次还款日期",
                "RemainPaymentCyc": "剩余还款期数",
                "ReportNo": "报告编号",
                "ScheduledPaymentAmount": "本月应还款",
                "ScheduledPaymentDate": "应还款日",
                "SerialNo": "流水号",
                "State": "账户状态",
                "StateEndDate": "状态截止日",
                "StateEndMonth": "状态截止月",
                "Type": "贷款种类细分",
                "bizType": "类型"
            }
            keys_new = {}.fromkeys(keys, "")
            # 描述信息
            keys_new["Cue"] = re.sub(r'\w+?\.', '', loan[0])
            # 业务号
            Account = 'Biz%s' % str(i + 1)
            keys_new["Account"] = Account
            SectionListMap[Account] = []
            if loan[1].strip() and loan[1].find("五级分类")>-1:
                # 解析具体信息
                selector = Selector(text=loan[1])
                tr1_header = selector.xpath('//tr[1]/td').xpath('string()')
                tr2_body = selector.xpath('//tr[2]/td').xpath('string()')
                for (i, header) in enumerate(tr1_header):
                    key = self.get_keys(keys, self._extract_replace(header))
                    if key:
                        keys_new[key] = self._extract_replace(tr2_body[i])
                # 当前逾期期数
                keys_new["CurrOverdueCyc"] = int(self._extract_replace(selector.xpath('//tr[4]/td[1]//text()')[0], ','))
                # 当前逾期金额
                keys_new["CurrOverdueAmount"] = round(float(self._extract_replace(selector.xpath('//tr[4]/td[2]//text()')[0], ',')),1)
                # 逾期31 - 60天未还本金
                keys_new["Overdue31To60Amount"] = self._extract_replace(selector.xpath('//tr[4]/td[3]//text()')[0])
                # 逾期61－90天未还本金
                keys_new["Overdue61To90Amount"] = self._extract_replace(selector.xpath('//tr[4]/td[4]//text()')[0])
                # 逾期91－180天未还本金
                keys_new["Overdue91To180Amount"] = self._extract_replace(selector.xpath('//tr[4]/td[5]//text()')[0])
                # 逾期180天以上未还本金
                keys_new["OverdueOver180Amount"] = self._extract_replace(selector.xpath('//tr[4]/td[6]//text()')[0])
                # 还款起始月
                repayment_text = self._extract_replace(selector.xpath('//tr[5]/td[1]//text()')[0])
                repayment_regex = r'(.*?)月-(.*?)月的还款记录'
                repayment = re.search(repayment_regex, repayment_text)
                keys_new["BeginMonth"] = repayment.group(1).replace('年', '.').replace('月', '')
                # 还款截止月
                keys_new["EndMonth"] = repayment.group(2).replace('年', '.').replace('月', '')
                # 24个月还款状态
                keys_new["Latest24State"] = self._extract_replace(selector.xpath('//tr[6]').xpath('string()')[0])
            keys_new["bizType"] = "贷款"
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": keys,
                    "ClassLabel": "贷款信息",
                    "ClassName": "jbo.crq.icr.ICRLoanInfo"
                },
                "Content": [
                    keys_new
                ],
                "Id": "3.3.1",
                "JboClass": "jbo.crq.icr.ICRLoanInfo",
                "Label": "贷款信息",
                "Multi": False,
                "Name": "LoanInfo",
                "Properties": {
                    "ACCOUNTNODE": "true"
                }
            })
            # 解析贷款逾期记录明细
            keys = {
                "ReportNo": "报告编号",
                "Account": "业务号",
                "SerialNo": "流水号",
                "Month": "逾期月份",
                "LastMonths": "逾期持续月数",
                "Amount": "逾期金额"
            }
            keys_new = {}.fromkeys(keys, "")
            YQ_BeginMonth = YQ_EndMonth = ''
            content_list = []
            if loan[1].strip() and loan[1].find("逾期记录") > -1:
                selector = Selector(text=loan[1])
                repayment_text = self._extract_replace(selector.xpath('//*[contains(text(), "逾期记录")]//text()')[0])
                repayment_regex = r'(.*?)-(.*?)的逾期记录'
                repayment = re.search(repayment_regex, repayment_text)
                YQ_BeginMonth = repayment.group(1).replace('年', '.').replace('月', '')
                # 还款截止月
                YQ_EndMonth = repayment.group(2).replace('年', '.').replace('月', '')
                # 解析具体信息
                # 查找“逾期记录”的td的父元素tr，再根据tr找到后一个的兄弟元素
                tr1_header = selector.xpath('//*[contains(text(), "逾期记录")]/../../../../../following-sibling::tr[1]/td').xpath('string()')
                tr2_body = selector.xpath('//*[contains(text(), "逾期记录")]/../../../../../following-sibling::tr[position()>1]')
                for tr2 in tr2_body:
                    for (i, header) in enumerate(tr1_header):
                        key = self.get_keys(keys, self._extract_replace(header))
                        if key:
                            try:
                                keys_new[key] = self._extract_replace(tr2.xpath('td').xpath('string()')[i])
                            except:
                                pass
                    content_list.append(keys_new)
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "BeginMonth": "起始月",
                        "EndMonth": "截止月",
                        "ReportNo": "报告编号"
                    },
                    "ClassLabel": "最近5年内的贷款逾期记录",
                    "ClassName": "jbo.crq.icr.ICRLatest5YearOverdueRecord"
                },
                "Id": "3.3.2",
                "JboClass": "jbo.crq.icr.ICRLatest5YearOverdueRecord",
                "Content": [{
                        "Account": Account,
                        "BeginMonth": YQ_BeginMonth,
                        "EndMonth": YQ_EndMonth,
                        "ReportNo": self.ReportNo
                    }],
                "Label": "贷款逾期记录",
                "Multi": False,
                "Name": "Latest5YearOverduesection_Loan",
                "Properties": {
                    "MULTI": "false"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": keys,
                    "ClassLabel": "逾期记录明细",
                    "ClassName": "jbo.crq.icr.ICRLatest5YearOverdueDetail"
                },
                "Id": "3.3.3",
                "JboClass": "jbo.crq.icr.ICRLatest5YearOverdueDetail",
                "Content": content_list,
                "Label": "贷款逾期记录明细",
                "Multi": True,
                "Name": "Latest5YearOverdueDetail_Loan",
                "Properties": {
                    "MULTI": "true"
                }
            })

            # 解析特殊交易类型
            keys = {
                "Account": "业务号",
                "ChangingAmount": "发生金额",
                "ChangingMonths": "变更月数",
                "Content": "明细记录",
                "GetTime": "发生日期",
                "ReportNo": "报告编号",
                "SerialNo": "流水号",
                "Type": "特殊交易类型"
            }
            keys_new = {}.fromkeys(keys, "")
            if loan[1].strip() and loan[1].find("特殊交易类型") > -1:
                # 解析具体信息
                selector = Selector(text=loan[1])
                # 查找“特殊交易类型”的td的父元素tr，再根据tr找到后一个的兄弟元素
                tr1_header = selector.xpath('//*[text()="特殊交易类型"]/../../../../../../td').xpath('string()')
                tr2_body = selector.xpath('//*[text()="特殊交易类型"]/../../../../../../following-sibling::tr[1]/td').xpath('string()')
                for (i, header) in enumerate(tr1_header):
                    key = self.get_keys(keys, self._extract_replace(header))
                    if key:
                        keys_new[key] = self._extract_replace(tr2_body[i])
                    keys_new["Type"] = "特殊交易类型"
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": keys,
                    "ClassLabel": "贷款特殊信息",
                    "ClassName": "jbo.crq.icr.ICRSpecialTrade"
                },
                "Id": "3.3.4",
                "JboClass": "jbo.crq.icr.ICRSpecialTrade",
                "Content": [
                    keys_new
                ],
                "Label": "贷款特殊信息",
                "Multi": True,
                "Name": "SpecialTrade_Loan",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Content": "贷款机构说明",
                        "GetTime": "添加日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号"
                    },
                    "ClassLabel": "贷款机构说明",
                    "ClassName": "jbo.crq.icr.ICRBankIlluminate"
                },
                "Id": "3.3.5",
                "JboClass": "jbo.crq.icr.ICRBankIlluminate",
                "Label": "贷款机构说明",
                "Multi": True,
                "Name": "BankIlluminate_Loan",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Content": "本人声明",
                        "GetTime": "添加日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号",
                        "Type": "声明类型"
                    },
                    "ClassLabel": "贷款本人声明",
                    "ClassName": "jbo.crq.icr.ICRAnnounceInfo"
                },
                "Id": "3.3.6",
                "JboClass": "jbo.crq.icr.ICRAnnounceInfo",
                "Label": "贷款本人声明",
                "Multi": True,
                "Name": "AnnounceInfo_Loan",
                "Properties": {
                    "MULTI": "true"
                }
            })
            # 解析异议标注
            keys = {
                "ReportNo": "报告编号",
                "Account": "业务号",
                "SerialNo": "流水号",
                "Content": "异议标注",
                "GetTime": "添加日期",
                "Type": "异议类型"
            }
            keys_new = {}.fromkeys(keys, "")
            if loan[1].strip() and loan[1].find("异议标注") > -1:
                # 解析具体信息
                selector = Selector(text=loan[1])
                # 查找“特殊交易类型”的td的父元素tr，再根据tr找到后一个的兄弟元素
                tr1_header = selector.xpath('//*[text()="异议标注"]/../../../../../td').xpath('string()')
                tr2_body = selector.xpath(
                    '//*[text()="异议标注"]/../../../../../following-sibling::tr[1]/td').xpath('string()')
                for (i, header) in enumerate(tr1_header):
                    key = self.get_keys(keys, self._extract_replace(header))
                    if key:
                        keys_new[key] = self._extract_replace(tr2_body[i])
                    keys_new["Type"] = "异议标注"
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": keys,
                    "ClassLabel": "贷款异议标注",
                    "ClassName": "jbo.crq.icr.ICRDissentInfo"
                },
                "Id": "3.3.7",
                "JboClass": "jbo.crq.icr.ICRDissentInfo",
                "Content": [
                    keys_new
                ],
                "Label": "贷款异议标注",
                "Multi": True,
                "Name": "DissentInfo_Loan",
                "Properties": {
                    "MULTI": "true"
                }
            })
        ChapterList.append({
            "Id": "3.3",
            "Label": "贷款",
            "MainSection": "3.3.1",
            "Multi": True,
            "Name": "Loan",
            "Properties": {
                "CUSTOMPARSE": "true",
                "MULTI": "true"
            },
            "RelativeField": "Account",
            "SectionListMap": SectionListMap
        })
        # 解析贷记卡
        SectionListMap = {}
        regex = r'<!--信用卡明细信息-->(.*?)<tr height=.*? valign="bottom"><td>'
        selector = self.html2selector(regex, response.text)
        # 从结果中筛选
        regex = r'<tr style="line-height:25px">.*?<span class=high>(.*?)</span>.*?<tbody>(.*?)</tbody>'
        loan_list = re.findall(regex, selector.response.text, re.S)
        for (i, loan) in enumerate(loan_list):
            # 描述信息
            Cue = re.sub(r'\w+?\.', '', loan[0])
            # 业务号
            Account = 'Biz%s' % str(i + 1)
            SectionListMap[Account] = []
            header_td1_name = State = UsedCreditLimitAmount = Latest6MonthUsedAvgAmount = \
            UsedHighestAmount = ScheduledPaymentAmount = ScheduledPaymentDate = \
            ActualPaymentAmount = RecentPayDate = CurrOverdueCyc = CurrOverdueAmount = \
            BeginMonth = EndMonth = Latest24State = ''
            if loan[1].strip():
                # 解析具体信息
                selector = Selector(text=loan[1])
                # 表头第一列列名
                header_td1_name = self._extract_replace(selector.xpath('//tr[1]/td[1]//text()')[0])
                # 账户状态
                State = self._extract_replace(selector.xpath('//tr[2]/td[1]//text()')[0], ',')
                # 已用额度
                UsedCreditLimitAmount = round(float(self._extract_replace(selector.xpath('//tr[2]/td[2]//text()')[0], ',')), 1)
                # 最近6个月平均使用额度
                Latest6MonthUsedAvgAmount = round(float(self._extract_replace(selector.xpath('//tr[2]/td[3]//text()')[0], ',')), 1)
                # 最大使用额度
                UsedHighestAmount = round(float(self._extract_replace(selector.xpath('//tr[2]/td[4]//text()')[0], ',')), 1)
                # 本月应还款
                ScheduledPaymentAmount = round(float(self._extract_replace(selector.xpath('//tr[2]/td[5]//text()')[0], ',')), 1)
                # 账单日
                ScheduledPaymentDate = self._extract_replace(selector.xpath('//tr[4]/td[1]//text()')[0])
                # 本月实还款
                ActualPaymentAmount = round(float(self._extract_replace(selector.xpath('//tr[4]/td[2]//text()')[0], ',')), 1)
                # 最近一次还款日期
                RecentPayDate = self._extract_replace(selector.xpath('//tr[4]/td[3]//text()')[0])
                # 当前逾期期数
                CurrOverdueCyc = round(float(self._extract_replace(selector.xpath('//tr[4]/td[4]//text()')[0], ',')), 1)
                # 当前逾期金额
                CurrOverdueAmount = round(float(self._extract_replace(selector.xpath('//tr[4]/td[5]//text()')[0], ',')), 1)
                # 还款起始月
                repayment_text = self._extract_replace(selector.xpath('//tr[5]/td[1]//text()')[0])
                repayment_regex = r'(.*?)月-(.*?)月的还款记录'
                repayment = re.search(repayment_regex, repayment_text)
                BeginMonth = repayment.group(1).replace('年', '.').replace('月', '')
                # 还款截止月
                EndMonth = repayment.group(2).replace('年', '.').replace('月', '')
                # 24个月还款状态
                Latest24State = self._extract_replace(selector.xpath('//tr[6]').xpath('string()')[0])
            SectionListMap[Account].append({
                    "BizObjectClass": {
                        "Attributes": {
                            "Account": "业务号",
                            "ActualPaymentAmount": "本月实还款",
                            "BadBalance": "呆帐余额",
                            "BeginMonth": "还款起始月",
                            "CreditLimitAmount": "授信额度",
                            "Cue": "描述",
                            "CueSerialNo": "描述流水号",
                            "CurrOverdueAmount": "当前逾期金额",
                            "CurrOverdueCyc": "当前逾期期数",
                            "Currency": "币种",
                            "EndMonth": "还款截止月",
                            "FinanceOrg": "发卡机构",
                            "FinanceType": "授信机构类型",
                            "GuaranteeType": "担保方式",
                            "Latest24State": "24个月还款状态",
                            "Latest6MonthUsedAvgAmount": "最近6个月平均使用额度",
                            "OpenDate": "发卡日期",
                            "RecentPayDate": "最近一次还款日期",
                            "ReportNo": "报告编号",
                            "ScheduledPaymentAmount": "本月应还款",
                            "ScheduledPaymentDate": "账单日",
                            "SerialNo": "流水号",
                            "ShareCreditLimitAmount": "共享额度",
                            "State": "帐户状态",
                            "StateEndDate": "状态截止日",
                            "UsedCreditLimitAmount": "已用额度",
                            "UsedHighestAmount": "最大使用额度",
                            "bizType": "类型"
                        },
                        "ClassLabel": "贷记卡信息",
                        "ClassName": "jbo.crq.icr.ICRLoancardInfo"
                    },
                    "Content": [
                        {
                            "Account": Account,
                            "ActualPaymentAmount": ActualPaymentAmount,
                            "BeginMonth": BeginMonth,
                            "CreditLimitAmount": "",
                            "Cue": Cue,
                            "CueSerialNo": "",
                            "CurrOverdueAmount": CurrOverdueAmount,
                            "CurrOverdueCyc": CurrOverdueCyc,
                            "Currency": "",
                            "EndMonth": EndMonth,
                            "FinanceOrg": "",
                            "FinanceType": "",
                            "GuaranteeType": "",
                            "Latest24State": Latest24State,
                            "Latest6MonthUsedAvgAmount": Latest6MonthUsedAvgAmount,
                            "OpenDate": "",
                            "RecentPayDate": RecentPayDate,
                            "ReportNo": self.ReportNo,
                            "ScheduledPaymentAmount": ScheduledPaymentAmount,
                            "ScheduledPaymentDate": ScheduledPaymentDate,
                            "ShareCreditLimitAmount":  round(float(State), 1) if header_td1_name == "共享额度" else "",
                            "State": State if header_td1_name == "账户状态" else "",
                            "StateEndDate": "",
                            "UsedCreditLimitAmount": UsedCreditLimitAmount,
                            "UsedHighestAmount": UsedHighestAmount,
                            "bizType": "贷记卡"
                        }
                    ],
                    "Id": "3.4.1",
                    "JboClass": "jbo.crq.icr.ICRLoancardInfo",
                    "Label": "贷记卡信息",
                    "Multi": False,
                    "Name": "LoancardInfo"
                })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "BeginMonth": "起始月",
                        "EndMonth": "截止月",
                        "ReportNo": "报告编号"
                    },
                    "ClassLabel": "最近5年内的贷款逾期记录",
                    "ClassName": "jbo.crq.icr.ICRLatest5YearOverdueRecord"
                },
                "Id": "3.4.2",
                "JboClass": "jbo.crq.icr.ICRLatest5YearOverdueRecord",
                "Label": "贷记卡逾期记录",
                "Multi": False,
                "Name": "Latest5YearOverduesection_Loancard",
                "Properties": {
                    "MULTI": "false"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Amount": "逾期金额",
                        "LastMonths": "逾期持续月数",
                        "Month": "逾期月份",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号"
                    },
                    "ClassLabel": "逾期记录明细",
                    "ClassName": "jbo.crq.icr.ICRLatest5YearOverdueDetail"
                },
                "Id": "3.4.3",
                "JboClass": "jbo.crq.icr.ICRLatest5YearOverdueDetail",
                "Label": "贷记卡逾期记录明细",
                "Multi": True,
                "Name": "Latest5YearOverdueDetail_Loancard",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "ChangingAmount": "发生金额",
                        "ChangingMonths": "变更月数",
                        "Content": "明细记录",
                        "GetTime": "发生日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号",
                        "Type": "特殊交易类型"
                    },
                    "ClassLabel": "贷款特殊信息",
                    "ClassName": "jbo.crq.icr.ICRSpecialTrade"
                },
                "Id": "3.4.4",
                "JboClass": "jbo.crq.icr.ICRSpecialTrade",
                "Label": "贷记卡特殊信息",
                "Multi": True,
                "Name": "SpecialTrade_Loancard",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Content": "贷款机构说明",
                        "GetTime": "添加日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号"
                    },
                    "ClassLabel": "贷款机构说明",
                    "ClassName": "jbo.crq.icr.ICRBankIlluminate"
                },
                "Id": "3.4.5",
                "JboClass": "jbo.crq.icr.ICRBankIlluminate",
                "Label": "贷记卡机构说明",
                "Multi": True,
                "Name": "BankIlluminate_Loancard",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Content": "本人声明",
                        "GetTime": "添加日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号",
                        "Type": "声明类型"
                    },
                    "ClassLabel": "贷款本人声明",
                    "ClassName": "jbo.crq.icr.ICRAnnounceInfo"
                },
                "Id": "3.4.6",
                "JboClass": "jbo.crq.icr.ICRAnnounceInfo",
                "Label": "贷记卡本人声明",
                "Multi": True,
                "Name": "AnnounceInfo_Loancard",
                "Properties": {
                    "MULTI": "true"
                }
            })
            SectionListMap[Account].append({
                "BizObjectClass": {
                    "Attributes": {
                        "Account": "业务号",
                        "Content": "异议标注",
                        "GetTime": "添加日期",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号",
                        "Type": "异议类型"
                    },
                    "ClassLabel": "贷款异议标注",
                    "ClassName": "jbo.crq.icr.ICRDissentInfo"
                },
                "Id": "3.4.7",
                "JboClass": "jbo.crq.icr.ICRDissentInfo",
                "Label": "贷记卡异议标注",
                "Multi": True,
                "Name": "DissentInfo_Loancard",
                "Properties": {
                    "MULTI": "true"
                }
            })
        ChapterList.append({
            "Id": "3.4",
            "Label": "贷记卡",
            "MainSection": "3.4.1",
            "Multi": True,
            "Name": "Loancard",
            "Properties": {
                "CUSTOMPARSE": "true",
                "MULTI": "true"
            },
            "RelativeField": "Account",
            "SectionListMap": SectionListMap
        })
        # 解析准贷记卡
        SectionListMap = {}
        regex = r'准贷记卡</b>(.*?)<!--C为他人担保详细信息-->'
        selector = self.html2selector(regex, response.text)
        # 从结果中筛选
        regex = r'<tr style="line-height:25px">.*?<span class=high>(.*?)</span>.*?<tbody>(.*?)</tbody>'
        loan_list = re.findall(regex, selector.response.text, re.S)
        for (i, loan) in enumerate(loan_list):
            # 描述信息
            Cue = re.sub(r'\w+?\.', '', loan[0])
            # 业务号
            Account = 'Biz%s' % str(i + 1)
            SectionListMap[Account] = []
            if loan[1].strip():
                # 解析具体信息
                selector = Selector(text=loan[1])
                # 共享额度
                ShareCreditLimitAmount = self._extract_replace(selector.xpath('//tr[2]/td[1]//text()')[0], ',')
                # 透支额度
                UsedCreditLimitAmount = self._extract_replace(selector.xpath('//tr[2]/td[2]//text()')[0], ',')
                # 最近6个月平均使用额度
                Latest6MonthUsedAvgAmount = self._extract_replace(selector.xpath('//tr[2]/td[3]//text()')[0], ',')
                # 最大使用额度
                UsedHighestAmount = self._extract_replace(selector.xpath('//tr[2]/td[4]//text()')[0], ',')
                # 账单日
                ScheduledPaymentDate = self._extract_replace(selector.xpath('//tr[2]/td[5]//text()')[0])
                # 本月实还款
                ActualPaymentAmount = self._extract_replace(selector.xpath('//tr[2]/td[6]//text()')[0], ',')
                # 最近一次还款日期
                RecentPayDate = self._extract_replace(selector.xpath('//tr[2]/td[7]//text()')[0])
                # 透支180天以上未付余额
                CurrOverdueAmount = self._extract_replace(selector.xpath('//tr[2]/td[8]//text()')[0], ',')
                # 还款起始月
                repayment_text = self._extract_replace(selector.xpath('//tr[3]/td[1]//text()')[0])
                repayment_regex = r'(.*?)月-(.*?)月的还款记录'
                repayment = re.search(repayment_regex, repayment_text)
                BeginMonth = repayment.group(1).replace('年', '.').replace('月', '')
                # 还款截止月
                EndMonth = repayment.group(2).replace('年', '.').replace('月', '')
                # 24个月还款状态
                Latest24State = self._extract_replace(selector.xpath('//tr[4]').xpath('string()')[0])
                SectionListMap[Account].append({
                    "BizObjectClass": {
                        "Attributes": {
                            "ReportNo": "报告编号",
                            "Account": "业务号",
                            "SerialNo": "流水号",
                            "ShareCreditLimitAmount": "共享额度",
                            "UsedCreditLimitAmount": "透支额度",
                            "Latest6MonthUsedAvgAmount": "最近6个月平均使用额度",
                            "UsedHighestAmount": "最大使用额度",
                            "ScheduledPaymentDate": "账单日",
                            "ActualPaymentAmount": "本月实还款",
                            "RecentPayDate": "最近一次还款日期",
                            "CurrOverdueAmount": "透支180天以上未付余额",
                            "bizType": "类型",
                            "Cue": "描述",
                            "FinanceOrg": "发卡机构",
                            "Currency": "币种",
                            "OpenDate": "发卡日期",
                            "CreditLimitAmount": "授信额度",
                            "GuaranteeType": "担保方式",
                            "State": "帐户状态",
                            "BadBalance": "呆帐余额",
                            "StateEndDate": "状态截止日",
                            "BeginMonth": "还款起始月",
                            "EndMonth": "还款截止月",
                            "Latest24State": "24个月还款状态"
                        },
                        "ClassLabel": "贷记卡信息",
                        "ClassName": "jbo.crq.icr.ICRLoancardInfo"
                    },
                    "Content": [
                        {
                            "ReportNo": self.ReportNo,
                            "Account": Account,
                            "SerialNo": "",
                            "ShareCreditLimitAmount": ShareCreditLimitAmount,
                            "UsedCreditLimitAmount": UsedCreditLimitAmount,
                            "Latest6MonthUsedAvgAmount": Latest6MonthUsedAvgAmount,
                            "UsedHighestAmount": UsedHighestAmount,
                            "ScheduledPaymentDate": ScheduledPaymentDate,
                            "ActualPaymentAmount": ActualPaymentAmount,
                            "RecentPayDate": RecentPayDate,
                            "CurrOverdueAmount": CurrOverdueAmount,
                            "bizType": "准贷记卡",
                            "Cue": Cue,
                            "FinanceOrg": "",
                            "Currency": "",
                            "OpenDate": "",
                            "CreditLimitAmount": "",
                            "GuaranteeType": "",
                            "State": "",
                            "BadBalance": "",
                            "StateEndDate": "",
                            "BeginMonth": BeginMonth,
                            "EndMonth": EndMonth,
                            "Latest24State": Latest24State
                        }
                    ],
                    "Id": "3.5.1",
                    "JboClass": "jbo.crq.icr.ICRLoancardInfo",
                    "Label": "准贷记卡信息",
                    "Multi": False,
                    "Name": "StandardLoancard"
                })
        ChapterList.append({
            "Id": "3.5",
            "Label": "准贷记卡",
            "MainSection": "3.5.1",
            "Multi": True,
            "Name": "StandardLoancard",
            "Properties": {
                "CUSTOMPARSE": "true",
                "MULTI": "true"
            },
            "RelativeField": "Account",
            "SectionListMap": SectionListMap
        })
        # 对外担保信息
        Content = []
        regex = r'对外担保信息</b>(.*?)<tr height=.+? valign="bottom">'
        selector = self.html2selector(regex, response.text)
        tr_list = selector.xpath('//tr/td/div/table//tr[position()>1]')
        for tr in tr_list:
            # 流水号
            SerialNo = self._extract_replace(tr.xpath('td[1]//text()')[0])
            # 担保贷款发放机构
            Organname = self._extract_replace(tr.xpath('td[2]//text()')[0])
            # 担保贷款合同金额
            ContractMoney = self._extract_replace(tr.xpath('td[3]//text()')[0], ',')
            # 担保贷款发放日期
            BeginDate = self._extract_replace(tr.xpath('td[4]//text()')[0])
            # 担保贷款到期日期
            EndDate = self._extract_replace(tr.xpath('td[5]//text()')[0])
            # 担保金额
            GuananteeMoney = self._extract_replace(tr.xpath('td[6]//text()')[0], ',')
            # 担保贷款本金余额
            GuaranteeBalance = self._extract_replace(tr.xpath('td[7]//text()')[0], ',')
            # 担保贷款五级分类
            Class5State = self._extract_replace(tr.xpath('td[8]//text()')[0])
            # 结算日期
            BillingDate = self._extract_replace(tr.xpath('td[9]//text()')[0])
            Content.append({
                "ReportNo": self.ReportNo,
                "SerialNo": SerialNo,
                "Organname": Organname,
                "ContractMoney": round(float(ContractMoney), 1) if ContractMoney else "",
                "BeginDate": BeginDate,
                "EndDate": EndDate,
                "GuananteeMoney": round(float(GuananteeMoney), 1) if GuananteeMoney else "",
                "GuaranteeBalance": round(float(GuaranteeBalance), 1) if GuaranteeBalance else "",
                "Class5State": Class5State,
                "BillingDate": BillingDate
            })
        ChapterList.append({
            "Id": "3.6",
            "Label": "对外担保信息",
            "Multi": False,
            "Name": "Guarantee",
            "SectionList": [
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "BeginDate": "担保贷款发放日期",
                            "BillingDate": "结算日期",
                            "Class5State": "担保贷款五级分类",
                            "ContractMoney": "担保贷款合同金额",
                            "EndDate": "担保贷款到期日期",
                            "GuananteeMoney": "担保金额",
                            "GuaranteeBalance": "担保贷款本金余额",
                            "Organname": "担保贷款发放机构",
                            "ReportNo": "报告编号",
                            "SerialNo": "流水号"
                        },
                        "ClassLabel": "对外担保信息",
                        "ClassName": "jbo.crq.icr.ICRGuarantee"
                    },
                    "Id": "3.6.1",
                    "JboClass": "jbo.crq.icr.ICRGuarantee",
                    "Content": Content,
                    "Label": "对外贷款担保信息",
                    "Multi": True,
                    "Name": "LoanGuarantee",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "BeginDate": "担保信用卡发卡日期",
                            "BillingDate": "账单日",
                            "CreditLimit": "担保信用卡授信额度",
                            "GuananteeMoney": "担保金额",
                            "Organname": "担保信用卡发放机构",
                            "ReportNo": "报告编号",
                            "SerialNo": "流水号",
                            "UsedLimit": "担保信用卡已用额度"
                        },
                        "ClassLabel": "对外信用卡担保信息",
                        "ClassName": "jbo.crq.icr.ICRCardGuarantee"
                    },
                    "Id": "3.6.2",
                    "JboClass": "jbo.crq.icr.ICRCardGuarantee",
                    "Label": "对外信用卡担保信息",
                    "Multi": True,
                    "Name": "CardGuarantee",
                    "Properties": {
                        "MULTI": "true"
                    }
                }
            ]
        })

        PartList.append({
            "ChapterList": ChapterList,
            "Id": "3",
            "Label": "信贷交易信息明细",
            "Multi": False,
            "Name": "CreditDetail"
        })
        return result

    def _parse_common_info(self, response, result):
        """
        5、解析公共信息
        :param response:
        :param result:
        :return:
        """
        # 解析欠税记录
        regex = r'<b>欠税记录(.*?)<!--法院诉讼信息-->'
        selector = self.html2selector(regex, response.text)
        content_list = []
        if selector.response.text:
            tr_list = selector.xpath('//tr/td/table/tr[position()>1]')
            for tr in tr_list:
                # 担保笔数
                Organname = self._extract_replace(tr.xpath('td//text()')[1])
                Revenuedate = self._extract_replace(tr.xpath('td//text()')[3])
                TaxArreaAmount = self._extract_replace(tr.xpath('td//text()')[2])
                content_list.append({
                    "Organname": Organname,
                    "ReportNo": self.ReportNo,
                    "Revenuedate": Revenuedate,
                    "SerialNo": "",
                    "TaxArreaAmount": TaxArreaAmount
                })
        # 解析强制执行记录
        regex = r'<b>强制执行记录(.*?)<!--公积金-->'
        selector = self.html2selector(regex, response.text)
        qzzx_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Court": "执行法院",
            "CaseReason": "执行案由",
            "RegisterDate": "立案日期",
            "ClosedType": "结案方式",
            "CaseState": "案件状态",
            "ClosedDate": "结案日期",
            "EnforceObject": "申请执行标的",
            "EnforceObjectMoney": "申请执行标的价值",
            "AlreadyEnforceObject": "已执行标的",
            "AlreadyEnforceObjectMoney": "已执行标的金额"
        }
        qzzx_keys_new = {}.fromkeys(qzzx_keys, "")
        if selector.response.text:
            # 查找“特殊交易类型”的td的父元素tr，再根据tr找到后一个的兄弟元素
            tr1_header = selector.xpath('//*[text()="执行法院"]/../../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="执行法院"]/../../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(qzzx_keys, self._extract_replace(header))
                if key:
                    qzzx_keys_new[key] = self._extract_replace(tr2_body[i])
            tr1_header = selector.xpath('//*[text()="案件状态"]/../../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="案件状态"]/../../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(qzzx_keys, self._extract_replace(header))
                if key:
                    qzzx_keys_new[key] = self._extract_replace(tr2_body[i])

        # 解析住房公积金参缴记录
        regex = r'<b>住房公积金参缴记录(.*?)<!--社保'
        selector = self.html2selector(regex, response.text)
        zfgjj_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Area": "参缴地",
            "RegisterDate": "参缴日期",
            "FirstMonth": "初缴月份",
            "ToMonth": "缴至月份",
            "State": "缴费状态",
            "Pay": "月缴存额",
            "OwnPercent": "个人缴存比例",
            "ComPercent": "单位缴存比例",
            "Organname": "缴费单位",
            "GetTime": "信息更新日期"
        }
        zfgjj_keys_new = {}.fromkeys(zfgjj_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[text()="参缴地"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="参缴地"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(zfgjj_keys, self._extract_replace(header))
                if key:
                    zfgjj_keys_new[key] = self._extract_replace(tr2_body[i])
            tr1_header = selector.xpath('//*[text()="缴费单位"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="缴费单位"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(zfgjj_keys, self._extract_replace(header))
                if key:
                    zfgjj_keys_new[key] = self._extract_replace(tr2_body[i])

        # 养老保险金缴存记录
        regex = r'<b>养老保险金缴存记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        ylbxj_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Area": "参保地",
            "RegisterDate": "参保日期",
            "MonthDuration": "累计缴费月数",
            "WorkDate": "参加工作月份",
            "State": "缴费状态",
            "OwnBasicMoney": "个人缴费基数",
            "Money": "本月缴费金额",
            "GetTime": "信息更新日期",
            "Organname": "缴费单位",
            "PauseReason": "中断或终止缴费原因"
        }
        ylbxj_keys_new = {}.fromkeys(ylbxj_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[text()="参保地"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="参保地"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(ylbxj_keys, self._extract_replace(header))
                if key:
                    ylbxj_keys_new[key] = self._extract_replace(tr2_body[i])
            tr1_header = selector.xpath('//*[text()="缴费单位"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="缴费单位"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(ylbxj_keys, self._extract_replace(header))
                if key:
                    ylbxj_keys_new[key] = self._extract_replace(tr2_body[i])

        # 养老保险金发放记录
        regex = r'<b>养老保险金发放记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        ylbxjff_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Area": "发放地",
            "RetireType": "离退休类别",
            "RetiredDate": "离退休月份",
            "WorkDate": "参加工作月份",
            "Money": "本月实发养老金",
            "PauseReason": "停发原因",
            "Organname": "原单位名称",
            "GetTime": "信息更新日期"
        }
        ylbxjff_keys_new = {}.fromkeys(ylbxjff_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[text()="发放地"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="发放地"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(ylbxjff_keys, self._extract_replace(header))
                if key:
                    ylbxjff_keys_new[key] = self._extract_replace(tr2_body[i])
            tr1_header = selector.xpath('//*[text()="原单位名称"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="原单位名称"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(ylbxjff_keys, self._extract_replace(header))
                if key:
                    ylbxjff_keys_new[key] = self._extract_replace(tr2_body[i])

        # 低保救助记录
        regex = r'<b>低保救助记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        dbjz_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "PersonnelType": "人员类别",
            "Area": "所在地",
            "Organname": "工作单位",
            "Money": "家庭月收入",
            "RegisterDate": "申请日期",
            "PassDate": "批准日期",
            "GetTime": "信息更新日期"
        }
        dbjz_keys_new = {}.fromkeys(dbjz_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[text()="家庭月收入"]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[text()="家庭月收入"]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(dbjz_keys, self._extract_replace(header))
                if key:
                    dbjz_keys_new[key] = self._extract_replace(tr2_body[i])

        # 执业资格记录
        regex = r'<b>执业资格记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        zyzg_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "CompetencyName": "执业资格名称",
            "Grade": "等级",
            "AwardDate": "获得日期",
            "EndDate": "到期日期",
            "RevokeDate": "吊销日期",
            "Organname": "颁发机构",
            "Area": "机构所在地"
        }
        zyzg_keys_new = {}.fromkeys(zyzg_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[contains(text(), "执业资格名称")]/../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[contains(text(), "执业资格名称")]/../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(zyzg_keys, self._extract_replace(header))
                if key:
                    zyzg_keys_new[key] = self._extract_replace(tr2_body[i])

        # 行政奖励记录
        regex = r'<b>行政奖励记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        xzjl_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Organname": "奖励机构",
            "Content": "奖励内容",
            "BeginDate": "生效日期",
            "EndDate": "截止日期"
        }
        xzjl_keys_new = {}.fromkeys(xzjl_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[contains(text(), "奖励机构")]/../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[contains(text(), "奖励机构")]/../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(xzjl_keys, self._extract_replace(header))
                if key:
                    xzjl_keys_new[key] = self._extract_replace(tr2_body[i])

        # 车辆交易和抵押记录
        regex = r'<b>车辆交易和抵押记录(.*?)<!--电信缴费-->'
        selector = self.html2selector(regex, response.text)
        cljy_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "EngineCode": "发动机号",
            "LicenseCode": "车牌号码",
            "Brand": "品牌",
            "CarType": "车辆类型",
            "UseCharacter": "使用性质",
            "State": "车辆状态",
            "PledgeFlag": "抵押标记",
            "GetTime": "信息更新日期"
        }
        cljy_keys_new = {}.fromkeys(cljy_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[contains(text(), "车牌号码")]/../../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[contains(text(), "车牌号码")]/../../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(cljy_keys, self._extract_replace(header))
                if key:
                    cljy_keys_new[key] = self._extract_replace(tr2_body[i])

        # 电信缴费记录
        regex = r'<b>电信缴费记录(.*?)<!--本人声明-->'
        selector = self.html2selector(regex, response.text)
        dxjfjl_keys = {
            "ReportNo": "报告编号",
            "SerialNo": "流水号",
            "Organname": "电信运营商",
            "Type": "业务类型",
            "RegisterDate": "业务开通日期",
            "State": "当前缴费状态",
            "ArrearMoney": "当前欠费金额",
            "ArrearMonths": "当前欠费月数",
            "GetTime": "记账年月",
            "Status24": "24个月缴费状态"
        }
        dxjfjl_keys_new = {}.fromkeys(dxjfjl_keys, "")
        if selector.response.text:
            tr1_header = selector.xpath('//*[contains(text(), "电信运营商")]/../../../../td').xpath('string()')
            tr2_body = selector.xpath(
                '//*[contains(text(), "电信运营商")]/../../../../following-sibling::tr[1]/td').xpath('string()')
            for (i, header) in enumerate(tr1_header):
                key = self.get_keys(dxjfjl_keys, self._extract_replace(header))
                if key:
                    dxjfjl_keys_new[key] = self._extract_replace(tr2_body[i])
            tr2_body = selector.xpath(
                '//*[contains(text(), "最近24个月缴费记录")]/../../../../following-sibling::tr[1]/td[position()>1]').xpath('string()').extract()
            dxjfjl_keys_new["Status24"] = "".join(tr2_body)

        result["ReportData"]["PartList"].append({
            "ChapterList": [
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "Organname": "主管税务机关",
                            "ReportNo": "报告编号",
                            "Revenuedate": "欠税统计日期",
                            "SerialNo": "流水号",
                            "TaxArreaAmount": "欠税总额"
                        },
                        "ClassLabel": "欠税记录",
                        "ClassName": "jbo.crq.icr.ICRTaxArrear"
                    },
                    "Id": "4.1",
                    "JboClass": "jbo.crq.icr.ICRTaxArrear",
                    "Content": content_list,
                    "Label": "欠税记录",
                    "Multi": True,
                    "Name": "TaxArrear",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "CaseReason": "案由",
                            "CaseResult": "判决/调解结果",
                            "CaseValidatedate": "判决/调解生效日期",
                            "ClosedType": "结案方式",
                            "Court": "立案法院",
                            "RegisterDate": "立案日期",
                            "ReportNo": "报告编号",
                            "SerialNo": "流水号",
                            "SuitObject": "诉讼标的",
                            "SuitObjectMoney": "诉讼标的金额"
                        },
                        "ClassLabel": "民事判决记录",
                        "ClassName": "jbo.crq.icr.ICRCivilJudgement"
                    },
                    "Id": "4.2",
                    "JboClass": "jbo.crq.icr.ICRCivilJudgement",
                    "Label": "民事判决记录",
                    "Multi": True,
                    "Name": "CivilJudgement",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": qzzx_keys,
                        "ClassLabel": "强制执行记录",
                        "ClassName": "jbo.crq.icr.ICRForceExecution"
                    },
                    "Id": "4.3",
                    "JboClass": "jbo.crq.icr.ICRForceExecution",
                    "Content": [
                      qzzx_keys_new
                    ],
                    "Label": "强制执行记录",
                    "Multi": True,
                    "Name": "ForceExecution",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": {
                            "BeginDate": "生效日期",
                            "Content": "处罚内容",
                            "EndDate": "截止日期",
                            "Money": "处罚金额",
                            "Organname": "处罚机构",
                            "ReportNo": "报告编号",
                            "Result": "行政复议结果",
                            "SerialNo": "流水号"
                        },
                        "ClassLabel": "行政处罚记录",
                        "ClassName": "jbo.crq.icr.ICRAdminPunishment"
                    },
                    "Id": "4.4",
                    "JboClass": "jbo.crq.icr.ICRAdminPunishment",
                    "Label": "行政处罚记录",
                    "Multi": True,
                    "Name": "AdminPunishment",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": zfgjj_keys,
                        "ClassLabel": "住房公积金参缴记录",
                        "ClassName": "jbo.crq.icr.ICRAccFund"
                    },
                    "Id": "4.5",
                    "JboClass": "jbo.crq.icr.ICRAccFund",
                    "Content":[
                        zfgjj_keys_new
                    ],
                    "Label": "住房公积金参缴记录",
                    "Multi": True,
                    "Name": "AccFund",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": ylbxj_keys,
                        "ClassLabel": "养老保险金缴存记录",
                        "ClassName": "jbo.crq.icr.ICREndowmentInsuranceDeposit"
                    },
                    "Id": "4.6",
                    "JboClass": "jbo.crq.icr.ICREndowmentInsuranceDeposit",
                    "Content": [
                        ylbxj_keys_new
                    ],
                    "Label": "养老保险金缴存记录",
                    "Multi": True,
                    "Name": "EndowmentInsuranceDeposit",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": ylbxjff_keys,
                        "ClassLabel": "养老保险金发放记录",
                        "ClassName": "jbo.crq.icr.ICREndowmentInsuranceDeliver"
                    },
                    "Id": "4.7",
                    "JboClass": "jbo.crq.icr.ICREndowmentInsuranceDeliver",
                    "Content": [
                        ylbxjff_keys_new
                    ],
                    "Label": "养老保险金发放记录",
                    "Multi": True,
                    "Name": "EndowmentInsuranceDeliver",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": dbjz_keys,
                        "ClassLabel": "低保救助记录",
                        "ClassName": "jbo.crq.icr.ICRSalvation"
                    },
                    "Id": "4.8",
                    "JboClass": "jbo.crq.icr.ICRSalvation",
                    "Content": [
                        dbjz_keys_new
                    ],
                    "Label": "低保救助记录",
                    "Multi": True,
                    "Name": "Salvation",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": zyzg_keys,
                        "ClassLabel": "执业资格记录",
                        "ClassName": "jbo.crq.icr.ICRCompetence"
                    },
                    "Id": "4.9",
                    "JboClass": "jbo.crq.icr.ICRCompetence",
                    "Content": [
                        zyzg_keys_new
                    ],
                    "Label": "执业资格记录",
                    "Multi": True,
                    "Name": "Competence",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": xzjl_keys,
                        "ClassLabel": "行政奖励记录",
                        "ClassName": "jbo.crq.icr.ICRAdminAward"
                    },
                    "Id": "4.10",
                    "JboClass": "jbo.crq.icr.ICRAdminAward",
                    "Content": [
                        xzjl_keys_new
                    ],
                    "Label": "行政奖励记录",
                    "Multi": True,
                    "Name": "AdminAward",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": cljy_keys,
                        "ClassLabel": "车辆交易和抵押记录",
                        "ClassName": "jbo.crq.icr.ICRVehicle"
                    },
                    "Id": "4.11",
                    "JboClass": "jbo.crq.icr.ICRVehicle",
                    "Content": [
                        cljy_keys_new
                    ],
                    "Label": "车辆交易和抵押记录",
                    "Multi": True,
                    "Name": "Vehicle",
                    "Properties": {
                        "MULTI": "true"
                    }
                },
                {
                    "BizObjectClass": {
                        "Attributes": dxjfjl_keys,
                        "ClassLabel": "电信缴费记录",
                        "ClassName": "jbo.crq.icr.ICRTelPayment"
                    },
                    "Id": "4.12",
                    "JboClass": "jbo.crq.icr.ICRTelPayment",
                    "Content": [
                        dxjfjl_keys_new
                    ],
                    "Label": "电信缴费记录",
                    "Multi": True,
                    "Name": "TelPayment",
                    "Properties": {
                        "MULTI": "true"
                    }
                }
            ],
            "Id": "4",
            "Label": "公共信息明细",
            "Multi": False,
            "Name": "PublicInfo"
        })
        return result

    def _parse_announce_info(self, response, result):
        """
        6、解析声明信息
        :param response:
        :param result:
        :return:
        """
        result["ReportData"]["PartList"].append({
                "ChapterList": [
                    {
                        "BizObjectClass": {
                            "Attributes": {
                                "Account": "业务号",
                                "Content": "本人声明",
                                "GetTime": "添加日期",
                                "ReportNo": "报告编号",
                                "SerialNo": "流水号",
                                "Type": "声明类型"
                            },
                            "ClassLabel": "贷款本人声明",
                            "ClassName": "jbo.crq.icr.ICRAnnounceInfo"
                        },
                        "Id": "5.1",
                        "JboClass": "jbo.crq.icr.ICRAnnounceInfo",
                        "Label": "本人声明",
                        "Multi": True,
                        "Name": "AnnounceInfo",
                        "Properties": {
                            "MULTI": "true"
                        }
                    },
                    {
                        "BizObjectClass": {
                            "Attributes": {
                                "Account": "业务号",
                                "Content": "异议标注",
                                "GetTime": "添加日期",
                                "ReportNo": "报告编号",
                                "SerialNo": "流水号",
                                "Type": "异议类型"
                            },
                            "ClassLabel": "贷款异议标注",
                            "ClassName": "jbo.crq.icr.ICRDissentInfo"
                        },
                        "Id": "5.2",
                        "JboClass": "jbo.crq.icr.ICRDissentInfo",
                        "Label": "异议标注",
                        "Multi": True,
                        "Name": "DissentInfo",
                        "Properties": {
                            "MULTI": "true"
                        }
                    }
                ],
                "Id": "5",
                "Label": "声明信息",
                "Multi": False,
                "Name": "Announce"
            })
        return result

    def _parse_query_record(self, response, result):
        """
        7、解析查询记录
        :param response:
        :param result:
        :return:
        """
        PartList = result["ReportData"]["PartList"]
        ChapterList = []
        # 解析贷记卡
        regex = r'<!--查询记录-->(.*?)<!--报告说明-->'
        selector = self.html2selector(regex, response.text)
        if selector.response.text:
            # 解析查询记录汇总
            query_pool = selector.xpath('//table[not(@border)]/*/tr[position()>2]/td//text()')
            # 贷款审批（最近1个月内的查询机构数）
            orgSum1 = self._extract_replace(query_pool[0], ',')
            # 信用卡审批（最近1个月内的查询机构数）
            orgSum2 = self._extract_replace(query_pool[1], ',')
            # 贷款审批（最近1个月内的查询次数）
            recordSum1 = self._extract_replace(query_pool[2], ',')
            # 信用卡审批（最近1个月内的查询次数）
            recordSum2 = self._extract_replace(query_pool[3], ',')
            # 本人查询（最近1个月内的查询次数）
            recordSum3 = self._extract_replace(query_pool[4], ',') if len(query_pool) == 8 else ""
            # 贷后管理（最近2年内的查询次数）
            towYearRecordSum1 = self._extract_replace(query_pool[5], ',') if len(query_pool) == 8 else self._extract_replace(query_pool[4], ',')
            # 担保资格审查（最近2年内的查询次数）
            towYearRecordSum2 = self._extract_replace(query_pool[6], ',') if len(query_pool) == 8 else self._extract_replace(query_pool[5], ',')
            # 特约商户实名审（最近2年内的查询次数）
            towYearRecordSum3 = self._extract_replace(query_pool[7], ',') if len(query_pool) == 8 else self._extract_replace(query_pool[6], ',')
            ChapterList.append({
                "BizObjectClass": {
                    "Attributes": {
                        "ReportNo": "报告编号",
                        "orgSum1": "最近1个月内的查询机构数(贷款审批)",
                        "orgSum2": "最近1个月内的查询机构数(信用卡审批)",
                        "recordSum1": "最近1个月内的查询次数(贷款审批)",
                        "recordSum2": "最近1个月内的查询次数(信用卡审批)",
                        "recordSum3": "最近1个月内的查询次数(本人查询)",
                        "towYearRecordSum1": "最近2年内的查询次数(贷后管理)",
                        "towYearRecordSum2": "最近2年内的查询次数(担保资格审查)",
                        "towYearRecordSum3": "最近2年内的查询次数(特约商户实名审查)"
                    },
                    "ClassLabel": "查询记录汇总",
                    "ClassName": "jbo.crq.icr.ICRRecordSummary"
                },
                "Content": [
                    {
                        "ReportNo": self.ReportNo,
                        "orgSum1": int(orgSum1) if orgSum1 else "",
                        "orgSum2": int(orgSum2) if orgSum2 else "",
                        "recordSum1": int(recordSum1) if recordSum1 else "",
                        "recordSum2": int(recordSum2) if recordSum2 else "",
                        "recordSum3": int(recordSum3) if recordSum3 else "",
                        "towYearRecordSum1": int(towYearRecordSum1) if towYearRecordSum1 else "",
                        "towYearRecordSum2": int(towYearRecordSum2) if towYearRecordSum2 else "",
                        "towYearRecordSum3": int(towYearRecordSum3) if towYearRecordSum3 else ""
                    }
                ],
                "Id": "6.1",
                "JboClass": "jbo.crq.icr.ICRRecordSummary",
                "Label": "查询记录汇总",
                "Multi": False,
                "Name": "RecordSummary",
                "Properties": {
                    "MULTI": "false"
                }
            })

            # 解析信贷审批查询记录明细
            Content = []
            query_record = selector.xpath('//table[@border]/*/tr[position()>1]')
            for record in query_record:
                # 查询日期
                QueryDate = self._extract_replace(record.xpath('td//text()')[1])
                # 查询操作员
                Querier = self._extract_replace(record.xpath('td//text()')[2])
                # 查询原因
                QueryReason = self._extract_replace(record.xpath('td//text()')[3])
                Content.append({
                    "Querier": Querier,
                    "QueryDate": QueryDate,
                    "QueryReason": QueryReason,
                    "ReportNo": self.ReportNo
                })

            ChapterList.append({
                "BizObjectClass": {
                    "Attributes": {
                        "Querier": "查询操作员",
                        "QueryDate": "查询日期",
                        "QueryReason": "查询原因",
                        "ReportNo": "报告编号",
                        "SerialNo": "流水号"
                    },
                    "ClassLabel": "信贷审批查询记录明细",
                    "ClassName": "jbo.crq.icr.ICRRecordDetail"
                },
                "Content": Content,
                "Id": "6.2",
                "JboClass": "jbo.crq.icr.ICRRecordDetail",
                "Label": "信贷审批查询记录明细",
                "Multi": True,
                "Name": "RecordDetail",
                "Properties": {
                    "MULTI": "true"
                }
            })

            PartList.append({
                "ChapterList": ChapterList,
                "Id": "6",
                "Label": "查询记录",
                "Multi": False,
                "Name": "QueryRecord"
            })
        return result

    def parse(self, response):
        result = dict()
        result = self._parse_report_base(response, result)
        result = self._parse_report_personal(response, result)
        result = self._parse_report_summary(response, result)
        result = self._parse_report_loan_detail(response, result)
        result = self._parse_common_info(response, result)
        result = self._parse_announce_info(response, result)
        result = self._parse_query_record(response, result)

        item = ZhengxinBankItem()
        item["report_no"] = result["ReportNo"]
        item["real_name"] = result["ReportDescribe"]["Name"]
        item["identification_number"] = result["ReportDescribe"]["CertNo"]
        item["report_time"] = result["ReportDescribe"]["ReportCreateTime"]
        item["detail"] = result

        yield item