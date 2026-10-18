from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class MarketplaceReadThrottle(SimpleRateThrottle):
    scope = "marketplace_read"

    def get_cache_key(self, request, view):
        ident = (
            request.user.pk
            if request.user.is_authenticated
            else self.get_ident(request)
        )
        return self.cache_format % {"scope": self.scope, "ident": ident}


class MarketplaceMutationThrottle(UserRateThrottle):
    scope = "account_mutation"

    def get_cache_key(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        return super().get_cache_key(request, view)


class ReportThrottle(UserRateThrottle):
    scope = "marketplace_report"

    def get_cache_key(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        return super().get_cache_key(request, view)


class ContactThrottle(SimpleRateThrottle):
    scope = "marketplace_contact"

    def get_cache_key(self, request, view):
        ident = (
            request.user.pk
            if request.user.is_authenticated
            else self.get_ident(request)
        )
        return self.cache_format % {"scope": self.scope, "ident": ident}
