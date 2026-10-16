from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class ShopImageUploadHandler(FileUploadHandler):
    def __init__(self, request):
        super().__init__(request)
        self.total = 0

    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if start + len(raw_data) > 2 * 1024 * 1024 or self.total > 4 * 1024 * 1024:
            self.request.shop_upload_error = {
                self.field_name: ["Use images smaller than 2 MiB each."]
            }
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None
