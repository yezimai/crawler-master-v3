# -*- coding: utf-8 -*-

from base64 import b64encode, b64decode
from binascii import b2a_hex, a2b_hex
from rsa import PublicKey, PrivateKey, encrypt, decrypt


class RsaUtil(object):
    """
    RSA加解密工具类
    """
    def __init__(self, key_is_hex=False):
        self.__pub_key = None  # 公钥对象
        self.__priv_key = None  # 私钥对象
        self._key_is_hex = key_is_hex  # 公钥私钥默认为base64编码

    def __set_pubkey(self, pubkey):
        """
        设置公钥
        :param pubkey:
        :return:
        """
        if self._key_is_hex:
            b_str = a2b_hex(pubkey)
            pubkey = b64encode(b_str)
        pkl = self._convert_key(pubkey)
        modulus = int(pkl[0], 16)
        exponent = int(pkl[1], 16)
        self.__pub_key = PublicKey(modulus, exponent)

    def __set_privkey(self, priv_key):
        """
        设置私钥
        :param priv_key:
        :return:
        """
        if self._key_is_hex:
            b_str = a2b_hex(priv_key)
            priv_key = b64encode(b_str)
        pkl = self._convert_key(priv_key, is_pubkey=False)
        n = int(pkl[0], 16)
        e = int(pkl[1], 16)
        d = int(pkl[2], 16)
        p = int(pkl[3], 16)
        q = int(pkl[4], 16)
        self.__priv_key = PrivateKey(n, e, d, p, q)

    def _convert_key(self, key, is_pubkey=True):
        """
        转换key
        :param is_pubkey:
        :return:
        """
        b_str = b64decode(key)

        if len(b_str) % 128 == 0:
            n = b2a_hex(b_str)
            e = b'10001'
            return n, e

        # 按位转换成16进制
        hex_str = "".join(hex(x)[2:].rjust(2, '0') for x in b_str)

        # 找到模数和指数的开头结束位置
        if is_pubkey:
            # 转换公钥
            n_start = 29 * 2
            e_start = 159 * 2
            n_len = 128 * 2
            e_len = 3 * 2

            n = hex_str[n_start:n_start + n_len]
            e = hex_str[e_start:e_start + e_len]

            return n, e
        else:
            # 转换私钥
            n_start = 11 * 2
            e_start = 141 * 2
            d_start = 147 * 2
            p_start = 278 * 2
            q_start = 345 * 2

            n_len = 128 * 2
            e_len = 3 * 2
            d_len = 128 * 2
            p_len = 64 * 2
            q_len = 64 * 2

            n = hex_str[n_start:n_start + n_len]
            e = hex_str[e_start:e_start + e_len]
            d = hex_str[d_start:d_start + d_len]
            p = hex_str[p_start:p_start + p_len]
            q = hex_str[q_start:q_start + q_len]

            return n, e, d, p, q

    def encrypt(self, text, pubkey, get_hex=False):
        """
        加密(公钥加密)
        :param text:
        :param pubkey:
        :param get_hex:
        :return:
        """
        self.__set_pubkey(pubkey)
        crypto = encrypt(text.encode("utf-8"), self.__pub_key)
        if get_hex:
            return str(b2a_hex(crypto))[2:-1]
        else:
            return b64encode(crypto).decode("utf-8")

    def decrypt(self, msg, priv_key, is_hex=False):
        """
        解密(私钥解密)
        :param msg:
        :param priv_key:
        :param is_hex:
        :return:
        """
        self.__set_privkey(priv_key)
        content = a2b_hex(msg) if is_hex else b64decode(msg)
        message = decrypt(content, self.__priv_key).decode("utf-8")
        return message


class RsaNoPadding(object):
    """
    RSA-无填充加密
    """
    def __init__(self, pubkey):
        self._pubkey = pubkey
        self._e = '10001'

    def __modpow(self, b, e, m):
        result = 1
        while e > 0:
            if e & 1:
                result = (result * b) % m
            e = e >> 1
            b = (b * b) % m
        return result

    def _str_to_int(self, string):
        n = 0
        for char in string:
            n = n << 8
            n += ord(char)
        return n

    def encrypt(self, msg):
        result = self.__modpow(self._str_to_int(msg), int(self._e, 16), int(self._pubkey, 16))
        return hex(result).lower()[2:]


if __name__ == '__main__':
    pubkey = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCh5Nk2GLiyQFMIU+h3OEA4UeFbu3dCH5sjd/sLTxxvwjXq7JLqJbt2rCIdzpAXOi4jL+FRGQnHaxUlHUBZsojnCcHvhrz2knV6rXNogt0emL7f7ZMRo8IsQGV8mlKIC9xLnlOQQdRNUssmrROrCG99wpTRRNZjOmLvkcoXdeuaCQIDAQAB'
    privkey = 'MIICWwIBAAKBgQCh5Nk2GLiyQFMIU+h3OEA4UeFbu3dCH5sjd/sLTxxvwjXq7JLqJbt2rCIdzpAXOi4jL+FRGQnHaxUlHUBZsojnCcHvhrz2knV6rXNogt0emL7f7ZMRo8IsQGV8mlKIC9xLnlOQQdRNUssmrROrCG99wpTRRNZjOmLvkcoXdeuaCQIDAQABAoGAUTcJ1H6QYTOts9bMHsrERLymzir8R9qtLBzrfp/gRxxpigHGLdph8cWmk8dlN5HDRXmmkdV6t2S7xdOnzZen31lcWe0bIzg0SrFiUEOtg3Lwxzw2Pz0dKwg4ZUooGKpcIU6kEpbC2UkjBV4+2E6P1DXuhdgTyHoUA3ycxOdjCAUCQQCyjTzGPXFoHq5TmiJyVd4VXNyCXGU0ZuQayt6nPN8Gd5CcEb2S4kggzPXQcd90FO0kHfZV6+PGTrc2ZUuz5uwPAkEA6B3lmEmiZsJS/decLzWR0T1CXaFGwTjBQbHXJ0RziAfkuy+VwSmhvrW/ipk5xbREr5rKx3jVI2PzVOvLw7NgZwJAbUsvDFnH9WfyZZJPy5TsID97awCLoovozM2phM0p55eAmUfyttp0ND/BqBpMIY49qoH8q5N9FYJRe6Z9tF2B2QJAQBEocw039xcB4zCk2l713YQEEmXWarSomuJkWWFKZiyPlJ8Ava0pCMOPl8jNKmWkY7fc6ovOgJMw8aqXtm+HVwJAerJeUEDez2djG5pIF6aCV0bP3fhQUq8OQCgGF5Qzo9CnqvYreGpYKPJGVixAsEPCiLzJRhy1XfFona6VRXIIxw=='
    my_rsa = RsaUtil(key_is_hex=False)
    msg = '1234567890abcdef'
    en_msg = my_rsa.encrypt(msg, pubkey=pubkey, get_hex=True)
    de_msg = my_rsa.decrypt(en_msg, priv_key=privkey, is_hex=True)
    print(en_msg, de_msg, sep='\n')

    en_msg = my_rsa.encrypt(msg, pubkey=pubkey, get_hex=False)
    de_msg = my_rsa.decrypt(en_msg, priv_key=privkey, is_hex=False)
    print(en_msg, de_msg, sep='\n')

    my_rsa = RsaUtil(key_is_hex=True)
    pubkey = '30819f300d06092a864886f70d010101050003818d0030818902818100a1e4d93618b8b240530853e87738403851e15bbb77421f9b2377fb0b4f1c6fc235eaec92ea25bb76ac221dce90173a2e232fe1511909c76b15251d4059b288e709c1ef86bcf692757aad736882dd1e98bedfed9311a3c22c40657c9a52880bdc4b9e539041d44d52cb26ad13ab086f7dc294d144d6633a62ef91ca1775eb9a090203010001'
    privkey = '3082025b02010002818100a1e4d93618b8b240530853e87738403851e15bbb77421f9b2377fb0b4f1c6fc235eaec92ea25bb76ac221dce90173a2e232fe1511909c76b15251d4059b288e709c1ef86bcf692757aad736882dd1e98bedfed9311a3c22c40657c9a52880bdc4b9e539041d44d52cb26ad13ab086f7dc294d144d6633a62ef91ca1775eb9a090203010001028180513709d47e906133adb3d6cc1ecac444bca6ce2afc47daad2c1ceb7e9fe0471c698a01c62dda61f1c5a693c7653791c34579a691d57ab764bbc5d3a7cd97a7df595c59ed1b2338344ab1625043ad8372f0c73c363f3d1d2b0838654a2818aa5c214ea41296c2d94923055e3ed84e8fd435ee85d813c87a14037c9cc4e7630805024100b28d3cc63d71681eae539a227255de155cdc825c653466e41acadea73cdf0677909c11bd92e24820ccf5d071df7414ed241df655ebe3c64eb736654bb3e6ec0f024100e81de59849a266c252fdd79c2f3591d13d425da146c138c141b1d72744738807e4bb2f95c129a1beb5bf8a9939c5b444af9acac778d52363f354ebcbc3b3606702406d4b2f0c59c7f567f265924fcb94ec203f7b6b008ba28be8cccda984cd29e797809947f2b6da74343fc1a81a4c218e3daa81fcab937d1582517ba67db45d81d90240401128730d37f71701e330a4da5ef5dd84041265d66ab4a89ae26459614a662c8f949f00bdad2908c38f97c8cd2a65a463b7dcea8bce809330f1aa97b66f875702407ab25e5040decf67631b9a4817a6825746cfddf85052af0e402806179433a3d0a7aaf62b786a5828f246562c40b043c288bcc9461cb55df1689dae95457208c7'
    en_msg = my_rsa.encrypt(msg, pubkey=pubkey, get_hex=False)
    de_msg = my_rsa.decrypt(en_msg, priv_key=privkey, is_hex=False)
    print(en_msg, de_msg, sep='\n')
