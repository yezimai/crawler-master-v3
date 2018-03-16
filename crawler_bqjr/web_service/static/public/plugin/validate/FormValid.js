/**
 * Created by FormValid on 2016/08/22
 */
$(function(){
	
	//登录页面
	$("#adm_log").validate({
      	rules : {
			Adminname : { //用户名验证
				required : true, 
			},
			Password : { //密码验证
				required : true, 
				rangelength:[6,16]
			},
			VerifiCode :{		//验证码
				required : true,
			},
		},		
		messages : {
			Adminname : {
				required : '管理员名称不得为空！',
			},
			Password : {
				required : '密码不能为空！',
				rangelength : '密码在6到16位之间！',
			},
			VerifiCode :{
				required : '验证码不得为空！',
			},
		},
		onfocusout : function (element, event) {
			//$('.error').empty();
			$(element).valid();
		},
    });



	
	//页面
	
	
	
	
	
	
	
	
	
	
	
	//{}对象方式验证表单
	/*
	var insRules = {
		rules : {
			username : { //用户名验证
				required : true, 
				rangelength:[6,16]
			},
			password : { //密码验证
				required : true, 
				rangelength:[6,16]
			},
			yzm :{		//验证码
				required : true,
			},
		},		
		messages : {
			username : {
				required : '用户名不得为空！',
				rangelength : '用户名在6到16位之间！',
			},
			password : {
				required : '密码不能为空！',
				rangelength : '密码在6到16位之间！',
			},
			yzm :{
				required : '验证码不得为空！',
			},
			},
		
		onfocusout : function (element, event) {
			$('.error').empty();
			$(element).valid();
		},
	};
	$('#login').validate(insRules);	//执行验证
	*/
	
})