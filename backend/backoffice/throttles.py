from accounts.throttles import LoginAccountThrottle, LoginIPThrottle


class AdminLoginIPThrottle(LoginIPThrottle):
    scope = "admin_login_ip"


class AdminLoginAccountThrottle(LoginAccountThrottle):
    scope = "admin_login_account"

    def get_cache_key(self, request, view):
        return self.key_for_identifier(request.POST.get("username", ""))
