function refresh_crawling_status() {
    window.setTimeout(ask_crawling_status, 1000);
}

var tip_time;
function tip(html, time) {
    var $box = $('div#bodyTip');
    if (html === false) {
        $box.hide();
    } else {
        html = html === 'loading' ? '<div class="loading-wrap"><i class="loading-ico"></i><div class="loading-text">正在加载数据，请稍候...</div></div>' : html;
        $('div#bodyTipmain').html(html);
        $box.show();
    }
    if (time) {
        tip_time && clearTimeout(tip_time);
        tip_time = setTimeout(function () {
            $box.hide();
        }, time);
    }
}

var crawling_page_time;
function show_crawling_page(html, time) {
    var $box = $('div#pageTip');
    if (html === false) {
        $box.hide();
    } else {
        html = html === 'loading' ? '<div class="waitcon"><div class="waitcontent"><img src="/static/public/images/wait_img.gif" class="wait_img"/><p class="wait_p">请耐心等待~<br/>我正在为您努力加载数据~</p></div></div>' : html;
        $box.html(html).show();
    }
    if (time) {
        crawling_page_time && clearTimeout(crawling_page_time);
        crawling_page_time = setTimeout(function () {
            $box.hide();
        }, time);
    }
}

var sms_btn_times = 61;
function show_sms_btn(btn_id, reset_time) {
    sms_btn_times--;
    var sms_btn = $("#" + btn_id);
    sms_btn.val("重新获取(" + sms_btn_times + ")").removeClass("btn_1").addClass("btn_2").prop('disabled', true);
    if (sms_btn_times === 0) {
        sms_btn.val("重新获取").removeClass("btn_2").addClass("btn_1").prop('disabled', false);
        sms_btn_times = reset_time;
        return;
    }
    setTimeout("show_sms_btn('" + btn_id + "', " + reset_time + ")", 1000);
}

function ajax_with_tip(url, data, ok_status_callback, fail_status_callback) {
    tip("loading");
    $.ajax({
        url: url,
        data: data,
        type: 'POST',
        dataType: 'json',
        timeout: 30000,
        traditional: true,
        cache: false,
        complete: function (XMLHttpRequest, textStatus) {
            tip(false);
        },
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            dialog.error("执行失败，请重试");
        },
        success: function (data) {
            if (data.status === 'ok') {
                ok_status_callback(data);
            } else {
                dialog.error("执行异常：" + data.msg);
                console.log(data.msg);
                if (fail_status_callback) {
                    fail_status_callback(data);
                }
            }
        }
    });
}

var start_time = null;
function ajax_crawl_user(ajax_data) {
    tip("loading");
    $.ajax({
        url: "/account_spider/crawl_account",
        data: ajax_data,
        type: 'POST',
        dataType: 'json',
        timeout: 30000,
        traditional: true,
        cache: false,
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            tip(false);
            dialog.error("执行失败，请重试");
        },
        success: function (data) {
            if (data.status === "ok") {
                var now = new Date();
                start_time = now.getTime();
                refresh_crawling_status();
            } else {
                tip(false);
                dialog.error("执行异常：" + data.msg);
                console.log(data.msg);
            }
        }
    });
}

function send_msg_to_parent(data) {
    data['customer_id'] = customer_id;
    data['serial_no'] = serial_no;
    window.parent.postMessage(data, '*');
}

function log_crawling_time() {
    var now = new Date();
    console.log('爬取耗时：' + ((now.getTime() - start_time) / 1000) + '秒');
}

function ajax_crawling_status(ajax_data, crawling_status_callback) {
    tip("loading");
    $.ajax({
        url: "/account_spider/get_user_crawling_status",
        data: ajax_data,
        type: 'POST',
        dataType: 'json',
        timeout: 30000,
        traditional: true,
        cache: false,
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            refresh_crawling_status();
            console.log("刷新失败");
        },
        success: function (data) {
            if (data.status === 'ok') {
                var crawling_status = data.crawling_status;
                if (crawling_status === "crawling") {  // 正在爬取
                    refresh_crawling_status();
                } else if (crawling_status === "login") {  //登录成功
                    refresh_crawling_status();

                    show_crawling_page("loading");
                    send_msg_to_parent(data, customer_id, serial_no);
                } else if (crawling_status === "done") {  //完成
                    tip(false);

                    log_crawling_time();

                    send_msg_to_parent(data, customer_id, serial_no);  // 通知父窗口

                    dialog.notice(get_success_dialog_msg('恭喜你，认证通过！'),
                                   window.location.pathname + window.location.search);
                } else if (crawling_status === "error") {  //出错
                    tip(false);

                    send_msg_to_parent(data, customer_id, serial_no);  // 通知父窗口

                    dialog.notice(get_error_dialog_msg(data.crawling_msg),
                                   window.location.pathname + window.location.search, "朕知道了");
                } else if (crawling_status === "crawling") {
                    refresh_crawling_status();
                } else {
                    if (crawling_status_callback) {
                        crawling_status_callback(data);
                    }
                    tip(false);
                }
            } else {
                refresh_crawling_status();
                console.log("刷新异常：" + data.msg);
            }
        }
    });
}

function submit_captcha_code(data) {
    tip("loading");
    $.ajax({
        url: "/account_spider/submit_captcha_code",
        data: data,
        type: 'POST',
        dataType: 'json',
        timeout: 30000,
        traditional: true,
        cache: false,
        error: function (XMLHttpRequest, textStatus, errorThrown) {
            tip(false);
            dialog.error('执行失败，请重试');
        },
        success: function (data) {
            if (data.status === "ok") {
                refresh_crawling_status();
            } else {
                tip(false);
                dialog.error('执行异常，请重试：' + data.msg);
                console.log(data.msg);
            }
        }
    });
}

function check_phone(phone) {
    return /^1\d{10}$/.test(phone);
}

//检测身份证号码正确性
function checkIdcard(idcard) {
    var area = {
        11: "北京",
        12: "天津",
        13: "河北",
        14: "山西",
        15: "内蒙古",
        21: "辽宁",
        22: "吉林",
        23: "黑龙江",
        31: "上海",
        32: "江苏",
        33: "浙江",
        34: "安徽",
        35: "福建",
        36: "江西",
        37: "山东",
        41: "河南",
        42: "湖北",
        43: "湖南",
        44: "广东",
        45: "广西",
        46: "海南",
        50: "重庆",
        51: "四川",
        52: "贵州",
        53: "云南",
        54: "西藏",
        61: "陕西",
        62: "甘肃",
        63: "青海",
        64: "宁夏",
        65: "新疆",
        71: "台湾",
        81: "香港",
        82: "澳门",
        91: "国外"
    };

    if (area[parseInt(idcard.substr(0, 2))] == null) {
        return "身份证地区非法!";
    }
    switch (idcard.length) {
        case 15:
            return "身份证号码出生日期超出范围或含有非法字符!";
        case 18:
            var ereg = "";
            if (parseInt(idcard.substr(6, 4)) % 4 === 0 || (parseInt(idcard.substr(6, 4)) % 100 === 0 && parseInt(idcard.substr(6, 4)) % 4 === 0)) {
                ereg = /^[1-9][0-9]{5}[1|2][0|9][0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))[0-9]{3}[0-9Xx]$/;
            } else {
                ereg = /^[1-9][0-9]{5}[1|2][0|9][0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))[0-9]{3}[0-9Xx]$/;
            }
            if (ereg.test(idcard)) {
                var idcard_array = idcard.split("");
                var S = (parseInt(idcard_array[0]) + parseInt(idcard_array[10])) * 7 + (parseInt(idcard_array[1]) + parseInt(idcard_array[11])) * 9 + (parseInt(idcard_array[2]) + parseInt(idcard_array[12])) * 10 + (parseInt(idcard_array[3]) + parseInt(idcard_array[13])) * 5 + (parseInt(idcard_array[4]) + parseInt(idcard_array[14])) * 8 + (parseInt(idcard_array[5]) + parseInt(idcard_array[15])) * 4 + (parseInt(idcard_array[6]) + parseInt(idcard_array[16])) * 2 + parseInt(idcard_array[7]) + parseInt(idcard_array[8]) * 6 + parseInt(idcard_array[9]) * 3;
                var Y = S % 11;
                var M = "F";
                var JYM = "10X98765432";
                M = JYM.substr(Y, 1);
                if (M === idcard_array[17].toUpperCase())
                    return "ok";
                else
                    return "身份证号码校验错误!";
            }
            else
                return "身份证号码出生日期超出范围或含有非法字符!";
        default:
            return "身份证号码位数不对!";
    }
}

//手机号验证
jQuery.validator.addMethod("mobileFormart", function (value, element) {
    return this.optional(element) || /^1\d{10}$/.test(value);
}, "请输入正确的手机号码");

//身份号验证
jQuery.validator.addMethod("idcard", function (value, element) {
    //var idType;
    //if(element.name == 'PHIdNo'){
    //	idType = $('[name="PHIdNoType"]');
    //}else{
    //	idType = $('[name="IdNoType"]');
    //}
    //return this.optional(element) || (idType.val() !== 'IDcard') || checkIdcard(value) == 'ok';
    return this.optional(element) || checkIdcard(value) === 'ok';	//只验证身份证号码只保留这一行即可
}, "请输入正确的证件号码");

function start_btn_enable() {
    $('.btn1').css('display', 'block');
    $('.btn2').hide();
}

function start_btn_disable() {
    $('.btn1').hide();
    $('.btn2').css('display', 'block');
}