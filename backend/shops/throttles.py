from accounts.throttles import IPThrottle


class StorefrontReadThrottle(IPThrottle):
    scope = "shop_read"
