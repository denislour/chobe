class CacheRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "cache"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "django_cache":
            return "cache"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "django_cache":
            return db == "cache"
        if db == "cache":
            return False
        return None
