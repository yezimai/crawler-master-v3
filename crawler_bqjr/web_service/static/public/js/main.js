$(function () {
    //输入框右侧清空按钮操作
    $('.inval1').focus(function () {
        if ($(this).parent('.rconli').find('.rconli_del')) {
            $(this).parent('.rconli').find('.rconli_del').show();
        }
    }).blur(function () {
        if ($(this).parent('.rconli').find('.rconli_del')) {
            if ($(this).val() === '') {
                $(this).parent('.rconli').find('.rconli_del').hide();
            }
        }
    });

    $('.rconli_del').click(function () {
        $(this).parent('.rconli').find('.inval1').val('');
    });
});