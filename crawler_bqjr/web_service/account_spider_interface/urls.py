# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import views, views_xuexin, views_zhengxin, views_shebao, \
    views_communications, views_jingdong, views_email, views_taobao

urlpatterns = [
    url(r'^crawl_account/?$', views.crawl_account, name="crawl_account"),  # 执行账号爬取
    url(r'^submit_captcha_code/?$', views.submit_captcha_code, name="submit_captcha_code"),  # 提交验证码
    url(r'^get_user_crawling_status/?$', views.get_crawling_status, name="get_user_crawling_status"),  # 获取用户的爬取状态
    url(r'^ask_send_sms_captcha/?$', views.ask_send_sms_captcha, name="ask_send_sms_captcha"),  # 请求需要发送验证码

    url(r'^crawl_communications/?$', views.show_communications_crawler_form, name="show_communications_crawler_form"),  # 显示爬取运营商数据的表单

    url(r'^crawl_5xian1jin/?$', views.show_5xian1jin_crawler_form),  # 显示爬取公积金数据的表单
    url(r'^crawl_bank/?$', views.show_bank_crawler_form),  # 显示爬取银行流水的表单

    url(r'^communications_check/?$', views_communications.check_communications, name="check_communications"),   # 检测号码所属运营商
    url(r'^communications_img_click/?$', views_communications.get_img_captcha, name="get_img_captcha"),  # 获取图片验证码
    url(r'^communications_sms_click/?$', views_communications.get_sms_captcha, name="get_sms_captcha"),  # 获取短信验证码
    url(r'^communications_sms_check_timeout/?$', views_communications.check_sms_timeout, name="check_sms_timeout"),  # 检测短信验证码是否超时
    url(r'^communications_telecom_bills_validation/?$', views_communications.telecom_bills_validation, name="telecom_bills_validation"),  # 电信通话记录验证

    url(r'^crawl_ecommerce_jingdong/?$', views.show_ecommerce_jingdong_crawler_form, name="show_ecommerce_jingdong_crawler_form"),  # 显示爬取京东数据的表单
    url(r'^jingdong_img_click/?$', views_jingdong.get_img_captcha, name="get_jingdong_img_captcha"),  # 京东登录刷新验证码
    url(r'^jingdong_send_sms_code/?$', views_jingdong.send_sms_code, name="jingdong_send_sms_code"),  # 京东登录发送短信验证码
    url(r'^jingdong_find_password_img_click/?$', views_jingdong.get_img_captcha_find_password, name="get_jingdong_find_password_img_captcha"),  # 京东找回密码刷新验证码
    url(r'^jingdong_find_password_step1/?$', views_jingdong.show_jingdong_find_password_form_step1, name="show_jingdong_find_password_form_step1"),  # 显示京东找回密码第一步表单
    url(r'^jingdong_find_password_step2/?$', views_jingdong.show_jingdong_find_password_form_step2, name="show_jingdong_find_password_form_step2"),  # 显示京东找回密码第二步表单
    url(r'^jingdong_find_password_step3/?$', views_jingdong.show_jingdong_find_password_form_step3, name="show_jingdong_find_password_form_step3"),  # 显示京东找回密码第三步表单
    url(r'^jingdong_fill_in_username/?$', views_jingdong.fill_in_username, name="jingdong_fill_in_username"),  # 京东找回密码填写用户名
    url(r'^jingdong_find_password_send_sms_code/?$', views_jingdong.send_sms_code_find_password, name="jingdong_find_password_send_sms_code"),  # 京东找回密码发送短信验证码
    url(r'^jingdong_verify_identify/?$', views_jingdong.verify_identify, name="jingdong_verify_identify"),  # 京东找回密码验证身份
    url(r'^jingdong_update_password/?$', views_jingdong.update_password, name="jingdong_update_password"),  # 京东找回密码更新密码

    url(r'^crawl_ecommerce_taobao/?$', views.show_ecommerce_taobao_crawler_form, name="show_ecommerce_taobao_crawler_form"),  # 显示爬取淘宝数据的表单
    url(r'^taobao_get_qrcode_info/?$', views_taobao.get_qrcode_info, name="taobao_get_qrcode_info"),  # 淘宝获取二维码信息
    url(r'^taobao_ask_qrcode_status/?$', views_taobao.ask_qrcode_status, name="taobao_ask_qrcode_status"),  # 淘宝获取扫描二维码状态
    url(r'^taobao_send_sms_code/?$', views_taobao.send_sms_code, name="taobao_send_sms_code"),  # 淘宝登录发送短信验证码

    url(r'^crawl_ecommerce_alipay/?$', views.show_ecommerce_alipay_crawler_form, name="show_ecommerce_alipay_crawler_form"),  # 显示爬取支付宝数据的表单

    url(r'^crawl_xuexin/?$', views.show_xuexin_crawler_form, name="show_xuexin_crawler_form"),  # 显示爬取学信网数据的表单
    url(r'^crawl_xuexin_reg/?$', views_xuexin.show_xuexin_reg_form, name="show_xuexin_reg_form"),  # 显示学信网登录的的表单
    url(r'^crawl_xuexin_find_password_step1/?$', views_xuexin.show_xuexin_find_password_form_step1, name="show_xuexin_find_password_form_step1"),  # 显示学信网找回密码第一步表单
    url(r'^crawl_xuexin_find_password_step2/?$', views_xuexin.show_xuexin_find_password_form_step2, name="show_xuexin_find_password_form_step2"),  # 显示学信网找回密码第二步表单
    url(r'^crawl_xuexin_update_password/?$', views_xuexin.show_xuexin_update_password_form, name="show_xuexin_update_password_form"),  # 显示学信网修改密码的表单
    url(r'^crawl_xuexin_find_username/?$', views_xuexin.show_xuexin_find_username_form, name="show_xuexin_find_username_form"),  # 显示学信网找回注册名表单
    url(r'^xuexin_reg_request/?$', views_xuexin.xuexin_reg_request, name="xuexin_reg_request"),  # 学信网注册
    url(r'^xuexin_get_vcode/?$', views_xuexin.xuexin_get_vcode, name="xuexin_get_vcode"),  # 学信网获取手机验证码
    url(r'^xuexin_get_pic_vcode/?$', views_xuexin.xuexin_get_pic_vcode, name="xuexin_get_pic_vcode"),  # 学信网获取图片验证码
    url(r'^xuexin_check_mobile/?$', views_xuexin.xuexin_check_mobile, name="xuexin_check_mobile"),  # 学信网检查手机号码是否注册
    url(r'^xuexin_find_password_step1/?$', views_xuexin.xuexin_find_password_step1, name="xuexin_find_password_step1"),  # 学信网找回密码第一步
    url(r'^xuexin_find_password_step2/?$', views_xuexin.xuexin_find_password_step2, name="xuexin_find_password_step2"),  # 学信网找回密码第二步
    url(r'^xuexin_update_password/?$', views_xuexin.xuexin_update_password, name="xuexin_update_password"),  # 学信网修改密码
    url(r'^xuexin_find_username/?$', views_xuexin.xuexin_find_username, name="xuexin_find_username"),  # 学信网找回用户名

    url(r'^crawl_emailbill/?$', views.show_emailbill_crawler_form, name="show_emailbill_crawler_form"),  # 显示爬取邮箱163数据的表单
    url(r'^qq_qrcode_login/?$', views.show_qq_qrcode_login, name="show_qq_qrcode_login"),  # 显示爬取qq的二维码登录
    url(r'^qq_get_qrcode/?$', views_email.qq_get_qrcode, name="qq_get_qrcode"),  # 获取qq二维码
    url(r'^qq_get_qrcode_status/?$', views_email.qq_get_qrcode_status, name="qq_get_qrcode_status"),  # 获取qq二维码状态
    url(r'^sina_get_img_captcha/?$', views_email.get_sina_img_captcha, name="sina_get_img_captcha"),  # 刷新图片验证码
    url(r'^sohu_get_img_captcha/?$', views_email.get_sohu_img_captcha, name="sohu_get_img_captcha"),  # 刷新图片验证码

    url(r'^zhengxin/reg_show/?$', views_zhengxin.show_zhengxin_reg, name='show_zhengxin_reg'),  # 显示人行征信注册第一步
    url(r'^zhengxin/get_captcha_body/?$', views_zhengxin.get_captcha_body, name="zhengxin_get_captcha_body"),  # 获取人行征信注册短信动态码
    url(r'^zhengxin/reg_request/?$', views_zhengxin.zhengxin_reg_request, name="zhengxin_reg_request"),  # 验证输入用户密码
    url(r'^zhengxin/reg2_request/?$', views_zhengxin.zhengxin_reg2_request, name="zhengxin_reg2_request"),  # 详细信息验证请求
    url(r'^zhengxin/user_yanzhen/?$', views_zhengxin.zhengxin_user_yanzhen, name="zhengxin_user_yanzhen"),  # 验证用户名是否存在
    url(r'^zhengxin/get_vcode/?$', views_zhengxin.get_zhengxin_AcvitaveCode, name="zhengxin_get_vcode"),  # 获取手机验证码
    url(r'^zhengxin/login_choose/?$', views_zhengxin.user_choose, name="show_zhengxin_crawler_choose_form"),  # 首页选择(有账号跳转和无账号申请)
    url(r'^zhengxin/login_form/?$', views.show_zhengxin_crawler_form, name="show_zhengxin_crawler_form"),  # 显示爬取征信数据的表单
    url(r'^zhengxin/?$', views_zhengxin.zhenxin_user_login, name="show_zhengxin_login"),  # 自动登录
    url(r'^zhengxin/login/?$', views_zhengxin.login, name="zhengxin_login"),  # 执行登录
    url(r'^zhengxin/option_question/?$', views_zhengxin.option_question, name="option_question"),  # 显示答题页面
    url(r'^zhengxin/option_question_detail/?$', views_zhengxin.option_question_detail, name="option_question_detail"),  # 开始答题
    url(r'^zhengxin/submit_question/?$', views_zhengxin.submit_question, name="submit_question"),  # 提交答题
    url(r'^zhengxin/back_username/?$', views_zhengxin.back_username, name="back_username"),  # 找回登录名
    url(r'^zhengxin/back_chuck_username/?$', views_zhengxin.back_chuck_username, name="back_chuck_username"),  # 找回登录名处理
    url(r'^zhengxin/back_passwd/?$', views_zhengxin.back_passwd, name="back_passwd"),  # 找回密码
    url(r'^zhengxin/back_chuck_passwd/?$', views_zhengxin.back_chuck_passwd, name="back_chuck_passwd"),  # 处理第一步
    url(r'^zhengxin/back_chuck2_passwd/?$', views_zhengxin.back_chuck2_passwd, name="back_chuck2_passwd"),  # 处理第二步
    url(r'^zhengxin/back_phone_vcode/?$', views_zhengxin.back_phone_vcode, name="back_phone_vcode"),  # 获取找回手机验证码
    url(r'^zhengxin/back_submit_passwd_question/?$', views_zhengxin.back_submit_passwd_question, name="back_submit_passwd_question"),  # 提交问题验证密码

    url(r'^shebao/show_index/?$', views_shebao.show_index, name="shebao_index"),  # 社保首页

    url(r'^crawl_nav/?$', views.crawl_nav, name="crawl_nav"),  # 爬虫导航页面
]
