/**
 * Created by think on 2017/6/7.
 */

// 获取图片验证码
function get_vcode() {
    ajax_with_tip("/account_spider/xuexin_get_pic_vcode/", "", function (the_data) {
        swal({
                title: "",
                text: "<img id='capcha_img' src='data:image/jpg;base64," + the_data.pic
                       + "'/><br><a href='#' onclick='change_capcha()'>看不清楚？点击换一张</a>",
                html: true,
                type: "input",
                showCancelButton: true,
                closeOnConfirm: false,
                showLoaderOnConfirm: true,
                animation: "slide-from-top",
                inputPlaceholder: "请输入验证码"
              },
              function (captch) {
                var ajax_data = {
                    "mphone": $("input#mphone").val(),
                    "captch": captch
                };
                ajax_with_tip("/account_spider/xuexin_get_vcode/", ajax_data, function (data) {
                    var result = data.result;
                    if (result.status === "2") {
                        swal("success", result.tips, "success");
                    } else {
                        change_capcha();
                        swal.showInputError(result.tips);
                        return false;
                    }
                });
              });
    });

    return true;
}

function check_mobile() {
    var ajax_data = $("form#reg_form").serialize();
    ajax_with_tip("/account_spider/xuexin_check_mobile/", ajax_data, function (data) {
        if (data.result === "false") {
            dialog.error("该手机已经注册");
        } else {
            dialog.error("手机号可用");
        }
    });
}

function change_capcha() {
    ajax_with_tip("/account_spider/xuexin_get_pic_vcode/", "", function (data) {
        $("img#capcha_img").attr("src", "data:image/jpg;base64," + data.pic);
    });
}
