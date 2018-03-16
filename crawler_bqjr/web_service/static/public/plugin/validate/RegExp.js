/**
 * Created by RegExp on 2016/08/22
 */

$(function(){

// 判断整数value是否等于0
    jQuery.validator.addMethod("isIntEqZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value==0;
    }, "整数必须为0");

// 判断整数value是否大于0
    jQuery.validator.addMethod("isIntGtZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value>0;
    }, "整数必须大于0");

// 判断整数value是否大于或等于0
    jQuery.validator.addMethod("isIntGteZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value>=0;
    }, "整数必须大于或等于0");

// 判断整数value是否不等于0
    jQuery.validator.addMethod("isIntNEqZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value!=0;
    }, "整数必须不等于0");

// 判断整数value是否小于0
    jQuery.validator.addMethod("isIntLtZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value<0;
    }, "整数必须小于0");

// 判断整数value是否小于或等于0
    jQuery.validator.addMethod("isIntLteZero", function(value, element) {
         value=parseInt(value);
         return this.optional(element) || value<=0;
    }, "整数必须小于或等于0");

// 判断浮点数value是否等于0
    jQuery.validator.addMethod("isFloatEqZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value==0;
    }, "浮点数必须为0");

// 判断浮点数value是否大于0
    jQuery.validator.addMethod("isFloatGtZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value>0;
    }, "浮点数必须大于0");

// 判断浮点数value是否大于或等于0
    jQuery.validator.addMethod("isFloatGteZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value>=0;
    }, "浮点数必须大于或等于0");

// 判断浮点数value是否不等于0
    jQuery.validator.addMethod("isFloatNEqZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value!=0;
    }, "浮点数必须不等于0");

// 判断浮点数value是否小于0
    jQuery.validator.addMethod("isFloatLtZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value<0;
    }, "浮点数必须小于0");

// 判断浮点数value是否小于或等于0
    jQuery.validator.addMethod("isFloatLteZero", function(value, element) {
         value=parseFloat(value);
         return this.optional(element) || value<=0;
    }, "浮点数必须小于或等于0");

// 判断浮点型
    jQuery.validator.addMethod("isFloat", function(value, element) {
         return this.optional(element) || /^[-\+]?\d+(\.\d+)?$/.test(value);
    }, "只能包含数字、小数点等字符");

// 匹配integer
    jQuery.validator.addMethod("isInteger", function(value, element) {
         return this.optional(element) || (/^[-\+]?\d+$/.test(value) && parseInt(value)>=0);
    }, "匹配integer");

// 判断数值类型，包括整数和浮点数
    jQuery.validator.addMethod("isNumber", function(value, element) {
         return this.optional(element) || /^[-\+]?\d+$/.test(value) || /^[-\+]?\d+(\.\d+)?$/.test(value);
    }, "匹配数值类型，包括整数和浮点数");

// 只能输入[0-9]数字
    jQuery.validator.addMethod("isDigits", function(value, element) {
         return this.optional(element) || /^\d+$/.test(value);
    }, "只能输入0-9数字");

// 判断中文字符
    jQuery.validator.addMethod("isChinese", function(value, element) {
         return this.optional(element) || /^[\u0391-\uFFE5]+$/.test(value);
    }, "只能包含中文字符。");

// 判断英文字符
    jQuery.validator.addMethod("isEnglish", function(value, element) {
         return this.optional(element) || /^[A-Za-z]+$/.test(value);
    }, "只能包含英文字符。");

// 中文字两个字节
    jQuery.validator.addMethod("byteRangeLength", function(value, element, param) {
        var length = value.length;
        for(var i = 0; i < value.length; i++){
            if(value.charCodeAt(i) > 127){
                length++;
            }
        }
        return this.optional(element) || ( length >= param[2] && length <= param[20] );
    }, $.validator.format("请确保输入的值在{2}-{20}个字节之间(一个中文字算2个字节)"));

// 匹配密码，以字母开头，长度在6-12之间，只能包含字符、数字和下划线。
    jQuery.validator.addMethod("isPwd", function(value, element) {
         return this.optional(element) || /^[a-zA-Z]\\w{6,12}$/.test(value);
    }, "以字母开头，长度在6-12之间，只能包含字符、数字和下划线。");

// IP地址验证
    jQuery.validator.addMethod("ip", function(value, element) {
      return this.optional(element) || /^(([1-9]|([1-9]\d)|(1\d\d)|(2([0-4]\d|5[0-5])))\.)(([1-9]|([1-9]\d)|(1\d\d)|(2([0-4]\d|5[0-5])))\.){2}([1-9]|([1-9]\d)|(1\d\d)|(2([0-4]\d|5[0-5])))$/.test(value);
    }, "请填写正确的IP地址。");

// 字符验证，只能包含中文、英文、数字、下划线等字符。
    jQuery.validator.addMethod("stringCheck", function(value, element) {
         return this.optional(element) || /^[a-zA-Z0-9\u4e00-\u9fa5-_]+$/.test(value);
    }, "只能包含中文、英文、数字、下划线等字符");

// 姓名验证
    jQuery.validator.addMethod("isName", function(value, element) {
        var name =  /^([\u4e00-\u9fa5·]{2,20})$/;
        return this.optional(element) || (name.test(value));
    }, '请正确填写您的姓名！');

// 字符验证
    jQuery.validator.addMethod("stringCheck", function(value, element) {
        return this.optional(element) || /^[\u0391-\uFFE5\w]+$/.test(value);
    }, "只能包括中文字、英文字母、数字和下划线");

// 特殊字符验证
    jQuery.validator.addMethod("isSpecial_forAddress", function(value, element) {
        var reg =  /[%'"(),，{}’“”#~!！（）【】`;]/;
        if(reg.test(value)){
            return false;
        }else{
            return true;
        }
        //return this.optional(element) || (reg.test(value));
    }, '请不要输入特殊字符！');

// 特殊字符验证
    jQuery.validator.addMethod("isSpecial", function(value, element) {
        var reg =  /[%'"(),，{}’“”#~!！（）*=+/\s【】`;]/;
        if(reg.test(value)){
            return false;
        }else{
            return true;
        }
        //return this.optional(element) || (reg.test(value));
    }, '请不要输入特殊字符！');

// 必须以特定字符串开头验证
    jQuery.validator.addMethod("begin", function(value, element, param) {
        var begin = new RegExp("^" + param);
        return this.optional(element) || (begin.test(value));
    }, $.validator.format("必须以 {0} 开头!"));

// 判断是否包含中英文特殊字符，除英文"-_"字符外
    jQuery.validator.addMethod("isContainsSpecialChar", function(value, element) {
         var reg = RegExp(/[(\ )(\`)(\~)(\!)(\@)(\#)(\$)(\%)(\^)(\&)(\*)(\()(\))(\+)(\=)(\|)(\{)(\})(\')(\:)(\;)(\')(',)(\[)(\])(\.)(\<)(\>)(\/)(\?)(\~)(\！)(\@)(\#)(\￥)(\%)(\…)(\&)(\*)(\（)(\）)(\—)(\+)(\|)(\{)(\})(\【)(\】)(\‘)(\；)(\：)(\”)(\“)(\’)(\。)(\，)(\、)(\？)]+/);
         return this.optional(element) || !reg.test(value);
    }, "含有中英文特殊字符");

// 有效期验证
    jQuery.validator.addMethod("isDate", function(value, element) {
        var date= /^([123456789]\d{3})\/(0\d{1}|1[0-2])\/(0\d{1}|[12]\d{1}|3[01])$/;
        return this.optional(element) || (date.test(value));
    }, "请输入格式为: yyyy/mm/dd的有效日期");

//日期必须大于指定日期
    jQuery.validator.addMethod('after',function(value, element){
        var startTime = $(element).attr('compare-date');

        var endTime = value;
        var start=new Date(startTime.replace("-", "/").replace("-", "/"));
        var end=new Date(endTime.replace("-", "/").replace("-", "/"));
        if(end<=start){
            return false;
        }
        return true;
    },"身份证有效期必须大于当前");

// 栋/单元/房间号
    jQuery.validator.addMethod("roomnum", function(value, element) {
        var  roomnum=/^[a-zA-Z0-9][\u4e00-\u9fa5]{1,15}$/;
        return this.optional(element) || (roomnum.test(value));
    }, '请如实根据身份证上户籍地址信息写，无信息统一输入"*"');

// 验证码验证
    jQuery.validator.addMethod("isValicode", function(value, element) {
        var  valicode=/^\d{6}$/;
        return this.optional(element) || (valicode.test(value));
    }, '请输入正确的验证码');

// 区号验证
    jQuery.validator.addMethod("isAreaCode", function(value, element) {
        var  isAreaCode=/^(0|4)[0-9]{2,3}$/;
        return this.optional(element) || (isAreaCode.test(value));
    }, '请输入正确的区号');

// 电话验证
    jQuery.validator.addMethod("isLanNum", function(value, element) {
        var  lannum=/^[2-9][0-9]{6,7}$/;
        return this.optional(element) || (lannum.test(value));
    }, '请输入正确的座机号');

// 分机号验证
    jQuery.validator.addMethod("isExten", function(value, element) {
        var  exten=/^[0-9]{1,4}?$/;
        return this.optional(element) || (exten.test(value));
    }, '请输入正确的分机号');

// 带区号电话号码验证
    jQuery.validator.addMethod("isTel", function(value, element) {
        var tel = /^\d{3,4}-?\d{7,9}$/;    //电话号码格式010-12345678
        return this.optional(element) || (tel.test(value));
    }, "请正确填写您的电话号码");

// 联系电话(手机/电话皆可)验证
    jQuery.validator.addMethod("isPhone", function(value,element) {
        var length = value.length, mobile = /^1\d{10}$/, tel = /^\d{3,4}-?\d{7,9}$/;
        return this.optional(element) || (tel.test(value) || mobile.test(value));
    }, "请正确填写您的联系电话");

//手机验证
    jQuery.validator.addMethod("mobileFormart", function(value, element) {
        var length = value.length, mobile = /^1\d{10}$/;
        return this.optional(element) || (length == 11 && mobile.test(value));
    }, "手机号码格式有误");

// 手机验证2
    jQuery.validator.addMethod("isPhoneNum", function(value, element) {
        var  phonenum=/^(13[0-9]|15[012356789]|17[0-9]|18[0-9]|14[57])[0-9]{8}$/;
        return this.optional(element) || (phonenum.test(value));
    }, '请输入正确的手机号');

// 手机号弱验证
    jQuery.validator.addMethod("isPhoneNumSoft", function(value, element) {
        var  phonenum=/^1[0-9]{10}$/;
        return this.optional(element) || (phonenum.test(value));
    }, '请输入正确的手机号');

//邮箱或手机验证规则
    jQuery.validator.addMethod("EmailTel", function (value, element) {
        var EmailTel = /^[a-z0-9._%-]+@([a-z0-9-]+\.)+[a-z]{2,4}$|^(13[0-9]|15[012356789]|17[0-9]|18[0-9]|14[57])[0-9]{8}$/;
        return this.optional(element) || (EmailTel.test(value));
    }, "格式不对");

//车牌号校验
    jQuery.validator.addMethod("isPlateNo", function (value, element) {
        var re = /^[\u4e00-\u9fa5]{1}[A-Z]{1}[A-Z_0-9]{5}$/;
        return this.optional(element) || (re.test(value));
    }, "格式不对");

//邮箱验证
    jQuery.validator.addMethod("isEmail", function(value, element) {
        var  email=/^[A-Za-z0-9]+([-_.][A-Za-z0-9]+)*@([A-Za-z0-9]+[-.])+[A-Za-z0-9]{2,5}$/;
        return this.optional(element) || (email.test(value));
    }, '请输入正确的邮箱');

//邮政编码验证
    jQuery.validator.addMethod("isZipCode", function(value, element) {
        var code = /^[0-9]{6}$/;
        return this.optional(element) || (code.test(value));
    }, "请正确填写您的邮政编码");

//QQ验证
    jQuery.validator.addMethod("isQQ", function(value, element) {
        var  QQ=/^[1-9][0-9]{5,9}$/;
        return this.optional(element) || (QQ.test(value));
    }, '请输入正确的QQ');

//微信验证
    jQuery.validator.addMethod("isWeChat", function(value, element) {
        var  WeChat=/^[a-zA-Z\d_]{5,20}$/;
        return this.optional(element) || (WeChat.test(value));
    }, '请输入正确的微信');

//银行卡号码验证
    jQuery.validator.addMethod("bank", function(value, element) {
        var length = value.length,
        mobile = /^[0-9]{16,19}$/;
        return this.optional(element) || (length == 16||19 && mobile.test(value));
    }, "银行卡号码格式有误");

//银行卡验证2
    jQuery.validator.addMethod("isBankCard", function(value, element) {
        value = value.replace(/\s/g, "");
        var bank_yz  = /^[0-4|6-9][0-9]{15,18}$/;
        return this.optional(element) || (bank_yz.test(value) );
    }, '请输入正确的银行卡');

//密码验证
    jQuery.validator.addMethod("isPassWord", function(value, element) {
        //强验证
        //var  pw=/^(?=.*\d)(?=.*[a-zA-Z])(?=.*[^a-zA-Z0-9]).{5,18}$/;
        var  pw=/^[a-zA-Z0-9]{5,18}$/;
        return this.optional(element) || (pw.test(value));
    }, '请输入正确的密码');

//不能有空格和回车换行
    jQuery.validator.addMethod("detailAddress", function(value, element) {
        //var  pw=/^(?=.*\d)(?=.*[a-zA-Z])(?=.*[^a-zA-Z0-9]).{5,18}$/;  //强验证
        var  pw=/^[^\r\n\s\\/]*$/;
        return this.optional(element) || (pw.test(value));
    }, '不能有空格和回车换行等');

//年龄
    jQuery.validator.addMethod("age", function(value, element) {
        var age = /^(?:[1-9][0-9]?|1[01][0-9]|120)$/;
        return this.optional(element) || (age.test(value));
    }, "不能超过120岁");

//传真
    jQuery.validator.addMethod("fax",function(value,element){
        var fax = /^(\d{3,4})?[-]?\d{7,8}$/;
        return this.optional(element) || (fax.test(value));
    },"传真格式如：0371-68787027");


//验证企业名称是否重复
    jQuery.validator.addMethod( "checkCompanyName",function(value,element){
        var a=true;
        jQuery.ajax({
            type:"get",
            url:"${contextPath}/tongManager/validatorCompanyName",
            async:false,
            cache:false,
            data:{ toinCompanyName:value,method:"get"},
            dataType:"html",
            scriptCharset:"UTF-8",
            success:function(s){
                if(s=="1"){
                    a=false;
                }
            }
        });
        return a;
    } ,  " <font color='red'>此企业(店)名称已经被占用！请您更换其它名称！</font>" );


// 身份证验证
    jQuery.validator.addMethod("isIdCard", function(value, element) {
        var idCard = /^(^[1-9]\d{7}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}$)|(^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])((\d{4})|\d{3}[Xx])$)$/;
        return this.optional(element) || (idCard.test(value));
    }, "请正确填写您的身份证号码");

//身份证
    jQuery.validator.addMethod("idCard", function (value, element) {
        var isIDCard1=/^[1-9]\d{7}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}$/;//(15位)
        var isIDCard2=/^[1-9]\d{5}[1-9]\d{3}((0\d)|(1[0-2]))(([0|1|2]\d)|3[0-1])\d{3}([0-9]|X)$/;//(18位)
        return this.optional(element) || (isIDCard1.test(value)) || (isIDCard2.test(value));
    }, "格式不对");

//身份证验证
    jQuery.validator.addMethod("idcard", function(value, element) {
        var idType;
            idType = $('[name="IdNoType"]');
            if(element.name == 'PHIdNo'){
                idType = $('[name="PHIdNoType"]');
            }else{
                idType = $('[name="IdNoType"]');
            }
            var isIDCard = idType.val() == 'IDcard' ? true : false;
            return this.optional(element) || !isIDCard || checkIdcard(value) == 'ok';
            //return this.optional(element) || checkIdcard(value) == 'ok';    //只验证身份证号码只保留这一行即可
    }, "请输入正确的18位身份证号码");
    setBirthFn($('[name="IdNo"]'),$('[name="BirthDt"]'),$('[name="IdNoType"]'),$('[name="Sex"]'));

//身份证验证
    $(function (){
        //身份证验证
        jQuery.validator.addMethod("idcard", function(value, element) {
            return this.optional(element) || checkIdcard(value) == 'ok';	//只验证身份证号码只保留这一行即可
        }, "请输入正确的18位身份证号码");

        setBirthFn($('[name="IdNo"]'));

        var insRules = {
            rules : {
                IdNo:{				//证件号码
                    required:true,
                    idcard:true
                }
            },
            messages : {
                IdNo:{
                    required:"身份证号码不能为空",
                }
            },
            onfocusout : function (element, event) {
                $(element).valid();
            }
        };
    });

    // 根据身份证设置生日
    function setBirthFn(fromObj,setObj,aboutObj,sexObj){  //fromObj:IdNo, setObj:BirthDt, aboutObj: IdNoType==IDcard
        var changeBirth = function(){
                if($(aboutObj).val() == 'IDcard' && $(fromObj).valid()){
                    var arr = $(fromObj).val().match(/^\d{6}(\d{4})(\d{2})(\d{2})/);
                    $(setObj).val(arr[1]+'-'+arr[2]+'-'+arr[3]).trigger('change');
                    $(setObj).length > 0 && $(setObj).valid();
                    var sex = parseInt($(fromObj).val().substr(16,1))%2==1?0:1;
                    $(sexObj).val(sex);
                    $(sexObj).length > 0 && $(sexObj).valid();
                }
            },
            disabledBirthSex = function(){
                if($(aboutObj).val() == 'IDcard'){
                    $(setObj).attr('disabled','disabled');
                    $(sexObj).attr('disabled','disabled');
                }else{
                    $(setObj).removeAttr('disabled');
                    $(sexObj).removeAttr('disabled');
                }
            };
        $(fromObj).bind('blur', function(){
            changeBirth();
        });
        $(aboutObj).bind('change', function(){
            changeBirth();
            disabledBirthSex();
        });
        disabledBirthSex();
    }
    // 判断是否证件号重复
    function judgeInsIDNo(IdNo, insData, editIndex){  //IdNo  ,insData:被保险人列表,  editIndex : 编辑的index
        var hasIdNo = false;
        if(insData && insData.length > 0){
            for(var i = 0;i < insData.length; i++){
                if(editIndex !== undefined){
                    if(editIndex != i && IdNo == insData[i]['IdNo']){
                        hasIdNo = true;
                        break;
                    }
                }else{
                    if(IdNo == insData[i]['IdNo']){
                        hasIdNo = true;
                        break;
                    }
                }
            }
        }
        return hasIdNo;
    }
    //检测身份证号码正确性
    function checkIdcard(idcard){
        var Errors=["ok","身份证号码位数不对!","身份证号码出生日期超出范围或含有非法字符!","身份证号码校验错误!","身份证地区非法!"];
        var area={11:"北京",12:"天津",13:"河北",14:"山西",15:"内蒙古",21:"辽宁",22:"吉林",23:"黑龙江",31:"上海",32:"江苏",33:"浙江",34:"安徽",35:"福建",36:"江西",37:"山东",41:"河南",42:"湖北",43:"湖南",44:"广东",45:"广西",46:"海南",50:"重庆",51:"四川",52:"贵州",53:"云南",54:"西藏",61:"陕西",62:"甘肃",63:"青海",64:"宁夏",65:"新疆",71:"台湾",81:"香港",82:"澳门",91:"国外"};
        var idcard,Y,JYM,S,M,idcard_array = [],retflag=false;
        idcard_array = idcard.split("");
        if(area[parseInt(idcard.substr(0,2))]==null)return Errors[4];
        switch(idcard.length){
            case 15:
                return Errors[2];
                break;
            case 18:
                if(parseInt(idcard.substr(6,4)) % 4 == 0 || (parseInt(idcard.substr(6,4))%100 == 0&&parseInt(idcard.substr(6,4))%4 == 0 )){
                    ereg=/^[1-9][0-9]{5}[1|2][0|9][0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|[1-2][0-9]))[0-9]{3}[0-9Xx]$/;
                }else{
                    ereg=/^[1-9][0-9]{5}[1|2][0|9][0-9]{2}((01|03|05|07|08|10|12)(0[1-9]|[1-2][0-9]|3[0-1])|(04|06|09|11)(0[1-9]|[1-2][0-9]|30)|02(0[1-9]|1[0-9]|2[0-8]))[0-9]{3}[0-9Xx]$/;
                }
                if(ereg.test(idcard)){
                    S = (parseInt(idcard_array[0]) + parseInt(idcard_array[10])) * 7 + (parseInt(idcard_array[1]) + parseInt(idcard_array[11])) * 9 + (parseInt(idcard_array[2]) + parseInt(idcard_array[12])) * 10 + (parseInt(idcard_array[3]) + parseInt(idcard_array[13])) * 5 + (parseInt(idcard_array[4]) + parseInt(idcard_array[14])) * 8 + (parseInt(idcard_array[5]) + parseInt(idcard_array[15])) * 4 + (parseInt(idcard_array[6]) + parseInt(idcard_array[16])) * 2 + parseInt(idcard_array[7]) * 1  + parseInt(idcard_array[8]) * 6 + parseInt(idcard_array[9]) * 3 ;
                    Y = S % 11;
                    M = "F";
                    JYM = "10X98765432";
                    M = JYM.substr(Y,1);
                    if(M == idcard_array[17].toUpperCase())
                        return Errors[0];
                    else
                        return Errors[3];
                }
                else
                    return Errors[2];
                break;
            default:
                return Errors[1];
                break;
        }
    }

    var get_id_type = function(type){  //判断证件类型
        if(type == "IDcard"){
            return "身份证";
        }else if(type == "Passport"){
            return "护照";
        }else if(type == "Other"){
            return "其他";
        }
    }
})