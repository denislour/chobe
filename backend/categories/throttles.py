from accounts.throttles import IPThrottle


class CategoryReadThrottle(IPThrottle):
    scope = "category_read"
