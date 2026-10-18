from rest_framework.exceptions import APIException


class VersionConflict(APIException):
    status_code = 409
    default_detail = "This page has changed. Reload the latest values and try again."
