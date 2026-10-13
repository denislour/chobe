from hashlib import sha256

from rest_framework.throttling import SimpleRateThrottle


class LoginIPThrottle(SimpleRateThrottle):
    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginAccountThrottle(SimpleRateThrottle):
    scope = "login_account"
    identifier_field = "username"

    def get_cache_key(self, request, view):
        if not isinstance(request.data, dict):
            return None
        identifier = request.data.get(self.identifier_field, "")
        if not isinstance(identifier, str) or not identifier.strip():
            return None
        ident = sha256(identifier.strip().casefold().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RegisterIPThrottle(LoginIPThrottle):
    scope = "register_ip"


class ForgotPasswordIPThrottle(LoginIPThrottle):
    scope = "forgot_password_ip"


class ForgotPasswordAccountThrottle(LoginAccountThrottle):
    scope = "forgot_password_account"
    identifier_field = "email"


class ResetPasswordIPThrottle(LoginIPThrottle):
    scope = "reset_password_ip"
