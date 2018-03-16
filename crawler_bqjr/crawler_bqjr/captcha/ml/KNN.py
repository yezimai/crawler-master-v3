from io import BytesIO
from os import listdir

import numpy as np
from PIL import Image
from bs4 import BeautifulSoup
from requests import get as http_get

from global_utils import json_loads, json_dumps


######################################################
# 将图像转化成向量
######################################################
def image_to_array(image):
    r, g, b = image.split()  # rgb通道分离
    # 注意：下面一定要reshpae(5400)使其变为一维数组，否则拼接的数据会出现错误，导致无法恢复图片
    r_arr = np.array(r).reshape(5400)
    g_arr = np.array(g).reshape(5400)
    b_arr = np.array(b).reshape(5400)
    # 行拼接，类似于接火车；最终结果：共n行，一行3072列，为一张图片的rgb值
    result = np.concatenate((r_arr, g_arr, b_arr))
    return result


######################################################
# 计算图像矩阵的模
######################################################
def get_knn_distance(image):
    data_1 = image_to_array(image)
    data_2 = np.ones(data_1.shape) * 128
    # 图像矩阵减去128降低计算规模
    delta = data_1 - data_2
    # 计算欧式距离
    distance = np.sum(delta ** 2) ** 0.5
    return distance


######################################################
# 计算某一文件夹下所有文件的训练数据
######################################################
def get_train_data_from_directory(directory_path):
    result = {}
    file_path_arr = listdir(directory_path)
    for file_path in file_path_arr:
        with Image.open("\\".join((directory_path, file_path))) as image:
            distance = get_knn_distance(image)
            distance = int(distance)

            image.show()
            # 输入验证码
            label = input("请输入验证码：")
            label = label.strip()
            result[str(distance)] = (distance, label, file_path)
    return result


######################################################
# 以json的形式存储训练数据到文件中
######################################################
def store_train_data(data, filepath):
    with open(filepath, "w") as train_data_file:
        train_data_file.write(json_dumps(data))


######################################################
# 从京东官网下载验证码并计算图片的值再存储到文件中
######################################################
def load_and_store_train_data(captcha_store_directory, train_data_path, loop_count=1):
    with open(train_data_path, "r") as train_data_file:
        result = train_data_file.read()
        result = json_loads(result)

    size = len(result) + 1
    for i in range(loop_count):
        resp = http_get("https://passport.jd.com/new/login.aspx")
        soup = BeautifulSoup(resp.text, "html.parser")
        auth_code_input = soup.select_one("#JD_Verification1")
        image_url = auth_code_input["src2"]
        resp = http_get("https:%s" % image_url)
        with Image.open(BytesIO(resp.content)) as image:
            knn_distance = get_knn_distance(image)
            knn_distance = str(float('%.2f' % knn_distance))

            if knn_distance not in result:
                image.save("%s/captcha_%d.jpg" % (captcha_store_directory, size))
                image.show()
                # 输入验证码
                label = input("请输入验证码：")
                label = label.strip()
                result[knn_distance] = (knn_distance, label, "captcha_%d.jpg" % size)
                size += 1

    with open(train_data_path, "w") as train_data_file:
        train_data_file.write(json_dumps(result))

    # if __name__ == "__main__":
    load_and_store_train_data("F:\work\公司文档\爬虫\京东验证码",
                              "F:\software\pycharm\workspace\crawler\crawler_bqjr\crawler_bqjr\spiders\\b2c_ecommerce_spiders\\train_data.json",
                              20)
