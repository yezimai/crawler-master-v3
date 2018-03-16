# -*- coding: utf-8 -*-

from math import ceil
from random import random as rand_0_1
from zipfile import ZipFile, ZIP_DEFLATED
from os.path import getsize as get_file_size

from requests import Session
from requests_toolbelt import MultipartEncoder

from global_utils import json_loads

YINDING_HOST = "http://222.171.144.245:8090/"
KWARGS = {"timeout": 6,
          }
ONE_MB = 1048576


class LoginFailedException(Exception):
    pass


class UploadFailedException(Exception):
    pass


def __do_img_upload(_session, file, file_size, batch="1"):
    data = {"name": file.name,
            "chunk": "0",
            "chunks": str(ceil(file_size / ONE_MB)),
            }
    resp = _session.post(YINDING_HOST + "base/resource.upload.do?size=0&batch=",
                         data, files={"file": (file.name, file, "application/x-zip-compressed")})
    print(resp.text)
    return


def __do_img_upload2(_session, file, file_size, batch="1"):
    data = MultipartEncoder(
        fields={'name': file.name,
                'chunk': '0',
                'chunks': str(ceil(file_size / ONE_MB)),
                'file': (file.name, file, "application/x-zip-compressed")},
        boundary="---------------------------9718571010145"
    )
    _session.headers['Content-Type'] = data.content_type
    resp = _session.post(YINDING_HOST + "base/resource.upload.do?size=0&batch=", data)
    return


def _do_img_upload(_session, batch="1", file_path=""):
    file_path = "test2.txt"
    file_name = file_path.rsplit(".", maxsplit=1)[0] + ".zip"
    with ZipFile(file_name, 'w', ZIP_DEFLATED, allowZip64=False) as zip_file:
        zip_file.write(file_path)

    file_size = get_file_size(file_name)
    with open(file_name, "rb") as f:
        _session.headers["Referer"] = YINDING_HOST + "base/custInfo.getUpload.do?random=" \
                                      + str(rand_0_1())

        # 判断资源是否上传过
        data = {"objName": file_name,
                "size": str(file_size),
                }
        resp = _session.post(YINDING_HOST + "base/custInfo.queryResourceName.do", data, **KWARGS)
        if resp.status_code != 200:
            raise UploadFailedException("判断资源非200")

        flag = resp.text.split(",", 1)[0]
        if flag == "-1":
            raise UploadFailedException("资源命名错误，请删除后重新上传")
        elif flag == "-2":
            raise UploadFailedException("该文件已上完成，请选择其它")
        elif flag.startswith("goOn"):
            raise UploadFailedException("资源未上传完整")
        elif flag != "1":
            raise UploadFailedException("未知错误: " + flag)

        # 上传图片
        __do_img_upload(_session, f, file_size, batch)

        # 向数据库中存入资源总大小
        data = {"objName": file_name + "-" + batch,
                "size": str(file_size),
                }
        resp = _session.post(YINDING_HOST + "base/resource.changeFileSize.do", data, **KWARGS)
        if resp.status_code != 200:
            raise UploadFailedException("存入资源返回非200")

        # 进行文件解析
        data = {"custInfo.uploadBatch": batch,
                "objName": file_name,
                }
        resp = _session.post(YINDING_HOST + "base/base/custInfo.anaPicInfo.do", data, **KWARGS)
        if resp.status_code != 200:
            raise UploadFailedException("文件解析返回非200")
        elif resp.text != "SUCCESS":
            raise UploadFailedException(resp.text)


def do_img_upload():
    with Session() as _session:
        try:
            _session.headers["Referer"] = YINDING_HOST + "login/initLogin.goInit.do"
            _session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0"
            _session.headers["Accept-Language"] = "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3"
            _session.post(YINDING_HOST + "login/initLogin.loginOut.do")

            data = {"userInfo.userName": "ceshi2",
                    "userInfo.password": "123456",
                    }
            resp = _session.post(YINDING_HOST + "login/initLogin.validationUser.do",
                                 data, **KWARGS)
            if resp.status_code != 200:
                raise LoginFailedException("验证用户返回非200")

            json_data = json_loads(resp.text)
            if json_data["resultType"] != "SUCCESS":
                raise LoginFailedException(resp.text)

            data = {"userName": "ceshi2",
                    "password": "123456",
                    }
            resp = _session.post(YINDING_HOST + "login/initLogin.loginSystem.do",
                                 data, **KWARGS)
            if resp.status_code != 200:
                raise LoginFailedException("登录返回非200")
            elif "退出登录" not in resp.text:
                raise LoginFailedException("登录失败")

            _do_img_upload(_session)
        finally:
            # 退出登录
            resp = _session.post(YINDING_HOST + "login/initLogin.loginOut.do")


if __name__ == '__main__':
    do_img_upload()
