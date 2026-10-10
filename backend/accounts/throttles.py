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

    def get_cache_key(self, request, view):
        if not isinstance(request.data, dict):
            return None
        username = request.data.get("username", "")
        if not isinstance(username, str) or not username.strip():
            return None
        ident = sha256(username.strip().casefold().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
