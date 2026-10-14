from hashlib import sha256

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class IPThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginIPThrottle(IPThrottle):
    scope = "login_ip"


class LoginAccountThrottle(SimpleRateThrottle):
    scope = "login_account"
    identifier_field = "username"

    def get_cache_key(self, request, view):
        if not isinstance(request.data, dict):
            return None
        return self.key_for_identifier(request.data.get(self.identifier_field, ""))

    def key_for_identifier(self, identifier):
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


class AccountMutationThrottle(UserRateThrottle):
    scope = "account_mutation"

    def allow_request(self, request, view):
        return request.method in ("GET", "HEAD", "OPTIONS") or super().allow_request(
            request, view
        )

class HistoryThrottle(UserRateThrottle):
    scope = "viewing_history"


class AccountDataExportThrottle(UserRateThrottle):
    scope = "data_export"

    def allow_request(self, request, view):
        return request.method != "POST" or super().allow_request(request, view)
