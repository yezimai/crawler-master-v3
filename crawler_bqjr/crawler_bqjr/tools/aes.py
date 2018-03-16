# -*- coding: utf-8 -*-

from base64 import b64encode, b64decode
from binascii import b2a_hex, a2b_hex
from Crypto.Cipher import AES


class AesUtil(object):
    """
    AES加解密工具类
    """
    def __init__(self, key, mode=None, iv=None):
        self.__key = key if isinstance(key, bytes) else key.encode('utf-8')
        self.__mode = mode or AES.MODE_ECB  # 默认为ECB模式
        self.__iv = iv or self.__key  # IV默认为key

    def encrypt(self, text, get_hex=False):
        """
        加密函数，如果text不是16的倍数(加密文本text必须为16的倍数),那就补足为16的倍数
        :param text:
        :param get_hex:
        :return:
        """
        text = text.encode('utf-8') if isinstance(text, str) else text
        if self.__mode == AES.MODE_ECB:
            cryptor = AES.new(self.__key, self.__mode)
        else:
            cryptor = AES.new(self.__key, self.__mode, self.__iv)

        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度
        length = 16
        mod_num = len(text) % length
        add = (length - mod_num) if mod_num != 0 else 0
        text = text + (b'\0' * add)
        ciphertext = cryptor.encrypt(text)

        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        if get_hex:
            # 把加密后的字符串转化为16进制字符串
            return b2a_hex(ciphertext).decode('utf-8')
        else:
            # 把加密后的字符串转化为base64字符串
            return b64encode(ciphertext).decode('utf-8')

    def decrypt(self, text, is_hex=False):
        """
        解密
        :param text:
        :param is_hex:
        :return:
        """
        text = text.encode('utf-8') if isinstance(text, str) else text
        if self.__mode == AES.MODE_ECB:
            cryptor = AES.new(self.__key, self.__mode)
        else:
            cryptor = AES.new(self.__key, self.__mode, self.__iv)

        if is_hex:
            plain_text = cryptor.decrypt(a2b_hex(text))
        else:
            plain_text = cryptor.decrypt(b64decode(text))

        return self.__byte_unpad(plain_text.decode("utf-8"))

    def __byte_unpad(self, text, byte_align_len=16):
        count = len(text)
        mod_num = count % byte_align_len
        assert mod_num == 0
        lastChar = text[-1]
        lastLen = ord(lastChar)
        lastChunk = text[-lastLen:]
        if lastChunk == chr(lastLen) * lastLen:
            return text[:-lastLen]
        return text


if __name__ == '__main__':
    pc = AesUtil('1234567812345678')  # 初始化密钥
    e = pc.encrypt("0123456789ABCDEF", get_hex=True)
    d = pc.decrypt(e, is_hex=True)
    print(e, d)

    e = pc.encrypt("0123456789ABCDEF")
    d = pc.decrypt(e)
    print(e, d)

    pc = AesUtil('1234567812345678', mode=AES.MODE_CBC)
    e = pc.encrypt("0123456789ABCDEF", get_hex=True)
    d = pc.decrypt(e, is_hex=True)
    print(e, d)

    pc = AesUtil('1234567812345678', mode=AES.MODE_CBC, iv=b'1234567812345678')
    e = pc.encrypt("0123456789ABCDEF")
    d = pc.decrypt(e)
    print(e, d)
