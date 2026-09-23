from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """Filesystem storage for protected assets with no client-facing URL."""

    @property
    def base_url(self):
        return None

    def url(self, name):
        # Protected media is served only by authenticated/authorized Django
        # endpoints. Returning an empty value also keeps admin widgets from
        # generating a direct public-media link.
        return ''
