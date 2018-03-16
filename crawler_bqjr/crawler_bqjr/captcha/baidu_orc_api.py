# -*- coding: utf-8 -*-

from io import BytesIO
from random import choice
from traceback import print_exc

from PIL import Image
from aip import AipOcr

BAIDU_ACCOUNT = [
    {"app_id": "10520557", "api_key": "R2VBkUgoXozCQEeEKaF6D8qe", "secret_key": "lKiti5009MvKGG5cD6invpUOf1IU0n8B"},
    {"app_id": "10523868", "api_key": "pav9YZHEeYYVgZKLY1P9TwxB", "secret_key": "pRMxP9uOk4Il2fm1HMjeiInEYRbRNAxp"},
    {"app_id": "10520916", "api_key": "SA7SYuKoBiwRvpTe7fzlV0hE", "secret_key": "qPCWz2MsZfOn6v9h5p3ULBjYvGABLNWt"},
    {"app_id": "10523877", "api_key": "3BnUqgQLoLKk7ns1WX2aFUHO", "secret_key": "hD9T5F0ZFUkpj4AvhUjhqXqKAlpY9iqQ"},
    {"app_id": "10519104", "api_key": "dlq2BDxXbOxsQxLlhGNlqxa7", "secret_key": "QLCST5XGWsmqRjEQOfPodknObrWm5BLn"},
    {"app_id": "10523897", "api_key": "eBr4MdT7xxm7wNMMlkqqtoCj", "secret_key": "ATX9PR2mc2IdmT9wGm633LoAlQCeblTj"},
    {"app_id": "10524437", "api_key": "Tc9iQRC7bmEMsPqY5L7Dww8g", "secret_key": "rjykhSWhlduZcK4G4H0bMBO8Gzg9xG64"},
    {"app_id": "10524475", "api_key": "yRW9vAQfXhKCa5Q4Krm95EM2", "secret_key": "KDxzrjHEgR3cYmRnqWUDC9xkB4OVVVeM"},
    {"app_id": "10524504", "api_key": "MgjRcgs4bc7Md4i8GaUid9bO", "secret_key": "FB3CCmPWbNKXSzMcxkL6au7uW2URCvMw"},
    {"app_id": "10524544", "api_key": "EtGQAGkMT2yMA81hrbXF7CMt", "secret_key": "mhY0FY5XNkbGibt4cqldU6WGyM3hd56X"},
    {"app_id": "10524589", "api_key": "WPXZIn9Lve9oOym8Ep4UIEm4", "secret_key": "Afn2FUL2rMIO3Fn0Lj9SXQlXrFCN1H8k"},
]


class BadCaptchaFormat(Exception):
    pass


def baidu_orc(captcha_body, accurate=True):
    try:
        options = {
            'detect_direction': 'true',
            'language_type': 'CHN_ENG',
        }

        for i in range(3):
            account = choice(BAIDU_ACCOUNT)
            aipOcr = AipOcr(account["app_id"], account["api_key"], account["secret_key"])

            if not isinstance(captcha_body, bytes):
                raise BadCaptchaFormat

            if accurate:
                # 高精度识别
                result = aipOcr.basicAccurate(captcha_body, options)
            else:
                # 普通识别
                result = aipOcr.basicGeneral(captcha_body, options)

            if 'error_code' not in result:
                return [i["words"] for i in result["words_result"]]
    except Exception:
        print_exc()

    return None


def convert_pic(pic_content):
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


if __name__ == '__main__':
    with open(r"f:\1.jpg", "rb") as f:
        c = convert_pic(f.read())
        print(baidu_orc(c))
