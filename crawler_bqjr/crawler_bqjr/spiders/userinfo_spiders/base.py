# -*- coding: utf-8 -*-

from io import BytesIO
from re import compile as re_compile

from PIL import Image

from crawler_bqjr.captcha.alicloud_orc_api import alicloud_orc
from crawler_bqjr.captcha.baidu_orc_api import baidu_orc
from crawler_bqjr.items.userinfo_items import XuexinItem
from crawler_bqjr.spider_class import AccountSpider
from crawler_bqjr.utils import invert_dict


class UserInfoSpider(AccountSpider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, item_class=XuexinItem, **kwargs)
        self.re_chinese = re_compile(u"[\u4e00-\u9fa5]+")
        replace_key_dict = {
            '姓名': 'real_name',
            '性别': 'sex',
            '出生日期': 'birthday',
            '民族': 'nation',
            '证件号码': 'identification_number',
            '学校名称': "collegeName",
            '层次': "eduLevel",
            '专业': "majorName",
            '学制': 'eduDuration',
            '学历类别': "eduType",
            '学习形式': "studyMode",
            '分院': 'branchCollege',
            '系(所、函授站)': 'department',
            '班级': 'class',
            '学号': "stuNo",
            '入学日期': 'enrollDate',
            '离校日期': 'leaveDate',
            '学籍状态': 'rollStatus',
            '类别': 'eduCategory',
            '证书编号': 'certificateNo',
            '毕业证照片': 'photo',
            '毕(结)业日期': 'leaveDate',
            '毕(结)业': 'rollStatus',
            '校(院)长姓名': 'prexName',
        }
        self.replace_key_dict = replace_key_dict
        self.lack_of_key_dict = invert_dict(replace_key_dict)

    def convert_pic(self, pic_content):
        """
        转换图片为黑白图片，并去水印
        :param pic_content: 转换前的图片二进制数据
        :return: 转换后的图片二进制数据
        """
        with BytesIO(pic_content) as f, Image.open(f) as img, BytesIO() as output:
            # 转为灰度图片
            img = img.convert('L')

            # 二值化处理（去噪）
            threshold = 160
            table = []
            for i in range(256):
                if i < threshold:
                    table.append(0)
                else:
                    table.append(1)

            img = img.point(table, '1')
            img.save(output, format='JPEG')
            return output.getvalue()

    def _re_replace(self, info_dict):
        lack_of_key_dict = self.lack_of_key_dict
        the_keys = set(info_dict.keys())
        all_keys = set(lack_of_key_dict.keys())
        lack_of_keys = all_keys - the_keys

        for key in (the_keys - all_keys):
            most_like_word = key
            max_similarity = 0
            for lack_key in lack_of_keys:
                full_words = lack_of_key_dict[lack_key]
                similarity = len([word for word in key if word in full_words])
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_like_word = lack_key

            try:
                lack_of_keys.remove(most_like_word)
            except KeyError:
                pass

            value = info_dict.pop(key)
            if not self.re_chinese.search(most_like_word):  # key替换成英文
                info_dict[most_like_word] = value

    def _orc_data_2_dict(self, words_list):
        ret_dict = {}
        replace_key_dict = self.replace_key_dict
        for info in words_list:
            try:
                info = info.replace('：', ":", 1)
                k, v = info.split(':', 1)
                k = k.strip().replace('（', '(').replace('（', ')')
                new_k = replace_key_dict.get(k, k)
                v = v.strip()
                ret_dict[new_k] = v if v != '冰' else "*"
            except Exception:
                pass

        self._re_replace(ret_dict)

        return ret_dict

    def _is_something_wrong(self, orc_dict):
        return (("identification_number" in orc_dict
                 and len(orc_dict['identification_number']) not in [18, 15])
                or ("birthday" in orc_dict and len(orc_dict['birthday']) != 11))

    def pic_orc(self, pic_content):
        pic = self.convert_pic(pic_content)

        words_list = baidu_orc(pic)
        use_baidu = True
        if not words_list:
            words_list = alicloud_orc(pic_content)
            use_baidu = False

        orc_dict = self._orc_data_2_dict(words_list)
        if use_baidu and self._is_something_wrong(orc_dict):
            words_list = alicloud_orc(pic_content)
            if words_list:
                orc_dict = self._orc_data_2_dict(words_list)

        return orc_dict
