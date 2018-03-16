# coding:utf-8

from base64 import b64encode, b64decode
from binascii import b2a_hex, a2b_hex
from traceback import print_exc

from Crypto.Cipher import DES3


class TripleDES(object):
    """
    3des加解密工具类
    """

    def __init__(self, key, mode=None, iv=None):
        self.__key = key[:24] if isinstance(key, bytes) else key[:24].encode('utf-8')
        self.__mode = mode or DES3.MODE_ECB  # 默认为ECB模式
        self.__iv = iv or self.__key  # IV默认为key

    def encrypt(self, text, get_hex=False):
        """
        加密函数
        :param text:
        :param get_hex:
        :return:
        """
        try:
            text = text.encode('utf-8') if isinstance(text, str) else text
            if self.__mode == DES3.MODE_ECB:
                cryptor = DES3.new(self.__key, self.__mode)
            else:
                cryptor = DES3.new(self.__key, self.__mode, self.__iv)

            # 填充方式pkcs5
            length = 8
            mod_num = len(text) % length
            add_num = (length - mod_num) if mod_num != 0 else 0
            pad_byte = chr(add_num).encode()
            text = text + (pad_byte * add_num)

            ciphertext = cryptor.encrypt(text)
            if get_hex:
                # 把加密后的字符串转化为16进制字符串
                return b2a_hex(ciphertext).decode('utf-8')
            else:
                # 把加密后的字符串转化为base64字符串
                return b64encode(ciphertext).decode('utf-8')
        except Exception:
            print("[-]3DES加密失败")
            print_exc()
            return

    def decrypt(self, text, is_hex=False):
        """
        解密
        :param text:
        :param is_hex:
        :return:
        """
        try:
            text = text.encode('utf-8') if isinstance(text, str) else text
            if self.__mode == DES3.MODE_ECB:
                cryptor = DES3.new(self.__key, self.__mode)
            else:
                cryptor = DES3.new(self.__key, self.__mode, self.__iv)

            if is_hex:
                plain_text = cryptor.decrypt(a2b_hex(text))
            else:
                plain_text = cryptor.decrypt(b64decode(text))

            return self.__byte_unpad(plain_text)
        except Exception:
            print("[-]3DES解密失败")
            print_exc()
            return

    def __byte_unpad(self, text, byte_align_len=8):
        count = len(text)
        mod_num = count % byte_align_len
        assert mod_num == 0
        text = text.decode()
        lastChar = text[-1]
        lastLen = ord(lastChar)
        lastChunk = text[-lastLen:]
        if lastChunk == chr(lastLen) * lastLen:
            return text[:-lastLen]
        return text


if __name__ == '__main__':
    key = "1234567`90koiuyhgtfrdewsaqaqsqde"
    iv = b"\x00\x00\x00\x00\x00\x00\x00\x00"
    pc = TripleDES(key=key, iv=iv)  # 初始化密钥
    e = pc.encrypt("0123456789ABCDEF", get_hex=False)
    d = pc.decrypt(e, is_hex=False)
    print(e, d)

    pc = TripleDES(key=key, iv=iv, mode=DES3.MODE_CBC)
    e = pc.encrypt("0123456789ABCDEF", get_hex=True)
    d = pc.decrypt(e, is_hex=True)
    print(e, d)

    en_msg = "b5720f816f50db5eb94116fd795b9f770f4af1f252692aa8c138f0e8150856db0b52b7c8000a7be699aabc4ab106f380f9e488a10e8269792beb5b46a667cdf32e20cf7649e74841dcfc49d871e100bda5b005efdca1abf6d8f95b802b6db01dc0bc44d9f75be7b899fcac6bf3674bff51429cb76f9ea218fa2bad0b88a6c6c80d9edbb96f284e26c08a514ffe89869973b1d297873df3042f7fed5cff21498279cee5c1521deab082083b21bbdbcdcbe94fb492867d0f86912d64f9c0f7b7fdbc8723631c786d726343715ab993e8c8ba9630ecd7036830c6f03589566deec1471ba7d6155989dd3a53a9b3c1ccd0bad11d2fca6cde4061"
    pc = TripleDES(key=key, iv=iv, mode=DES3.MODE_CBC)
    d = pc.decrypt(en_msg, is_hex=True)
    print(d)

    en_msg = "2966aa9f9a149371483724b75dc53d50ad1ebceb8d1c521b1478d58d6d2f44018b9735096b65cb807124ed62bf144c688e95d15f9aa0ca07398b3c2a4f80af4ab7a1e89da828d993122ac6455d234a7459ce049c8dc84499558aa7004936521d90e4186ee19dee629bfb8ea84464390615b46546e13792b6772289417cfb5580b35660f30af368863258bcec93064da345e0a6d80aa0b28ee82bb6bdd932c7649f9d79ba777b3af783a34a0655557ce2a5fbcdf2f8b40bff801aa71118fd13beb55aa27ed650d098ed85f30c93529b7ebbab192f6cdcff13043f9803ed9a0fdf5754fd86a0c537a4c76e75a2aee00cc7bf2c84f3302a1a6a36b0fa9fb3d56ef3b175d5ef714ad0794eddaab8b165fe273a1b25ebb3516a6bb9b6a9a0e1cbf23c0b24948b941d7e31a148c588093d3e953256bfb7b858f9ba82b40cc1cd2a297dc76b1ca3fca203ce9a71bd08cefe8a336b42d1d76dca988e"
    pc = TripleDES(key=key, iv=iv, mode=DES3.MODE_CBC)
    d = pc.decrypt(en_msg, is_hex=True)
    print(d)
