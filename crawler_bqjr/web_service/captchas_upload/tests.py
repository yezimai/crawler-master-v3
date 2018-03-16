from requests import post as http_post


def upload_file_2_server(url, file, params=None):
    """
    with open("captcha.jpeg", "rb") as img:
        params = {"file_type": ".jpeg",
                  "website": "qq.com",
                  "username": "the_user",
                  }
        ret = upload_file_2_server("http://127.0.0.1:8000/captcha_upload/upload_file/", img, params)


    ret is a dict: {u'status': u'ok', u'uid': u'b7928a3cc2742193d7d2e9c02fccee56'}
    """
    try:
        files = {'file': file}
        response = http_post(url, data=params, files=files)
        return response.json()
    except Exception:
        from traceback import print_exc
        print_exc()
        return None


if __name__ == '__main__':
    with open("..\\static\\captcha\\test.jpg", "rb") as img:
        params = {"file_type": ".jpeg",
                  "website": "qq.com",
                  "username": "the_user",
                  }
        print(upload_file_2_server("http://127.0.0.1:8000/recognize_captcha/", img, params))
