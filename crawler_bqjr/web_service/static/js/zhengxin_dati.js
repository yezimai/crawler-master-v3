/**
 * Created by BQ0391 on 2017/9/4.
 */
var st = {};

$(function () {
    $('.logtime_btn3').on('click', function () {
        $.ajax({
            type: "post",
            url: "/account_spider/zhengxin/submit_question/",
            data: {'st': st},
            success: function(data) {
                if (data.status === 'ok') {
                    dialog.notice(get_success_dialog_msg(data.msg), '/account_spider/zhengxin/login_choose/');
                } else {
                    dialog.notice(get_error_dialog_msg(data.msg), '/account_spider/zhengxin/login_choose/');
                }
            }
        });
    });
});

$(function () {
    $('#sub_btn_passwd').on('click', function () {
         $.ajax({
            type: "post",
            url: "/account_spider/zhengxin/back_submit_passwd_question/",
            data: {'dict': st},
            success: function(data) {
                if (data.status === 'ok') {
                    dialog.notice(get_success_dialog_msg(data.msg), '/account_spider/zhengxin/login_choose/');
                } else {
                    dialog.notice(get_error_dialog_msg(data.msg), '/account_spider/zhengxin/login_choose/');
                }
            }
        });
    });
});

function setValue(n, obj) {
    // 如果 val 被忽略
    if (typeof obj === "undefined") {
        // 删除属性
        delete st['key[' + n + '].options'];
    }
    else {
        // 添加 或 修改
        st['key[' + n + '].options'] = obj.value;
    }
}

var countdown = 60 * 10;

function settime() {
    if (countdown === 0) {
        dialog.notice(get_error_dialog_msg("答题超时"), '/account_spider/zhengxin/login_choose/', "朕知道了");
        //countdown = 60;
    } else {
        $('#minute_show').html('<s></s>' + checkTime(countdown / 60) + ' :');
        $('#second_show').html('<s></s>' + checkTime(countdown % 60) + '');
        countdown--;
    }
    setTimeout(settime, 1000);
}

$(function () {
    settime();
});

function checkTime(i) { //将0-9的数字前面加上0，例1变为01
    if (i < 10) {
        i = "0" + i;
    }
    return i;
}