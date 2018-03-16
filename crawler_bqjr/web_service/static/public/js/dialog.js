// dialog
var dialog = {
    // 错误弹出层
    error: function (message) {
        layer.open({
            content: message,
            skin: 'msg',
            time: 10 	//10秒后自动关闭
        });
    },

    notice: function (message, url, btn_text) {
        layer.open({
            content: message,
            btn: btn_text || "确定",
            style: 'width:90%;',
            shadeClose: false,
            yes: function () {
                location.href = url;
            }
        });
    }
};

function get_success_dialog_msg(msg) {
    return '<span class="rheadli_span1"><span class="rheadli_span21"><img src="/static/public/images/reg_img03.png" class="rheadli_img3"/></span></span>' + msg;
}

function get_error_dialog_msg(msg) {
    return '<span class="rheadli_span1"><span class="rheadli_span23" ><img src="/static/public/images/error.png" class="rheadli_img4"/></span></span>' + msg;
}