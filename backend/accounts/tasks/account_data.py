from django.tasks import task

from accounts.services import account_data


@task
def build_account_data_export(job_id: str) -> int:
    return account_data.build_account_data_export(job_id)


@task
def delete_account_data(job_id: str) -> int:
    return account_data.delete_account_data(job_id)
