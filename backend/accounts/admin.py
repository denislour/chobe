from django.contrib import admin

from accounts.models import User
from backoffice.admin import UserAdmin as ThemedUserAdmin


@admin.register(User)
class UserAdmin(ThemedUserAdmin):
    pass
