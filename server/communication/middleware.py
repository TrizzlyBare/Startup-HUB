from django.utils.deprecation import MiddlewareMixin
import cloudinary


class CloudinaryConfigMiddleware(MiddlewareMixin):
    """
    Middleware to ensure Cloudinary is configured for every request
    """

    def process_request(self, request):
        cloudinary.config(
            cloud_name="dnggowads",
            api_key="437578293728877",
            api_secret="5u4gxfznYm3mgzTEWDxDejF-BBY",
        )
        return None
