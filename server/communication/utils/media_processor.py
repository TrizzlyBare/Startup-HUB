from .cloudinary_helper import CloudinaryHelper


class MediaProcessor:
    @staticmethod
    def upload_image(file, **kwargs):
        """
        Upload image to Cloudinary
        """
        result = CloudinaryHelper.upload_image(file, **kwargs)
        if result:
            return result.get("url")
        return None

    @staticmethod
    def upload_video(file, **kwargs):
        """
        Upload video to Cloudinary and return URL and thumbnail
        """
        result = CloudinaryHelper.upload_video(file, **kwargs)
        if result:
            return {
                "video_url": result.get("url"),
                "thumbnail_url": result.get("thumbnail"),
            }
        return None

    @staticmethod
    def upload_audio(file, **kwargs):
        """
        Upload audio to Cloudinary
        """
        # Using raw resource type for audio files
        result = CloudinaryHelper.upload_image(
            file, resource_type="raw", folder="app_audio", **kwargs
        )
        if result:
            return result.get("url")
        return None
