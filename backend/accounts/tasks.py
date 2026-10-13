from django.core.mail import send_mail
from django.tasks import task

from accounts.models import User


@task
def send_welcome_email(user_id: int) -> int:
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or not user.email:
        return 0
    return send_mail(
        subject="Welcome to Chobe",
        message=f"Hi {user.username},\n\nYour Chobe account is ready. Welcome!",
        from_email=None,
        recipient_list=[user.email],
    )
