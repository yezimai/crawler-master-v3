class CaptcherInvalidException(Exception):
    def __init__(self):
        super(CaptcherInvalidException, self).__init__()

    def __str__(self):
        return "验证码错误"


class InvalidWebpageException(Exception):
    def __init__(self, url):
        super(InvalidWebpageException, self).__init__()
        self.url = url

    def __str__(self):
        return "网页不可用错误[" + self.url + "]"


class LoginException(Exception):
    def __init__(self, url):
        super(LoginException, self).__init__()
        self.url = url

    def __str__(self):
        return "登录页面不可用错误[" + self.url + "]"


class HttpStatusException(Exception):
    def __init__(self):
        super(HttpStatusException, self).__init__()

    def __str__(self):
        return "HTTP请求不可用错误[" + self.url + "]"
