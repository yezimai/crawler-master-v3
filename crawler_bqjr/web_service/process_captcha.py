# -*- coding: UTF-8 -*-

from re import compile as re_compile
from string import digits, ascii_letters

from PIL import Image, ImageEnhance, ImageFilter
from piltesseract import get_text_from_image

blank_pattern = re_compile(r"\s")
all_chars = digits + ascii_letters


def enhancer_img(img):
    enhancer = ImageEnhance.Contrast(img)  # 加强效果
    return enhancer.enhance(2)  # 加强效果


def del_img_noise(img):
    new_im = img.filter(ImageFilter.MedianFilter())  # 去噪
    return enhancer_img(new_im)  # 加强效果


def convert_img_2_baw(img):
    return img.convert('L')  # 转化为灰度图片(黑白图片)


def recognize_captcha_by_tesseract(img, digits_only=False, letters_only=False, del_noise=False):
    if digits_only:
        whitelist = digits
    elif letters_only:
        whitelist = ascii_letters
    else:
        whitelist = all_chars

    img = convert_img_2_baw(img)
    if del_noise:
        img = del_img_noise(img)

    text = get_text_from_image(img, tessedit_char_whitelist=whitelist)
    return blank_pattern.sub("", text)


def recognize_captcha_from_file(file, **kwargs):
    with Image.open(file) as f:
        return recognize_captcha_by_tesseract(f, **kwargs)


if __name__ == '__main__':
    with open(r"static\captcha\test.jpg", "rb") as img:
        print(recognize_captcha_from_file(img))
