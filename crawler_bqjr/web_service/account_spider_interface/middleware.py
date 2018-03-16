from django.conf import settings
from django.http import HttpResponseForbidden
from oauthlib.oauth2 import Server

from oauth2_provider.oauth2_backends import OAuthLibCore
from oauth2_provider.oauth2_validators import OAuth2Validator


class AccessTokenMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 正式环境下要检查AccessToken
        if not settings.DEBUG:
            if "account_spider" in request.path:
                authorization = request.META.get("HTTP_AUTHORIZATION", "")
                token = request.GET.get("token", "")
                authorization_session = request.session.get("authorization")
                if token:
                    request.META["HTTP_AUTHORIZATION"] = "Bearer %s" % token
                    request.session['authorization'] = "Bearer %s" % token
                elif authorization:
                    request.session['authorization'] = authorization
                elif authorization_session:
                    request.META["HTTP_AUTHORIZATION"] = authorization_session
                validator = OAuth2Validator()
                core = OAuthLibCore(Server(validator))
                valid, oauthlib_req = core.verify_request(request, scopes=[])
                if not valid:
                    return HttpResponseForbidden()
                request.resource_owner = oauthlib_req.user

        return self.get_response(request)
