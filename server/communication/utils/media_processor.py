from .cloudinary_helper import CloudinaryHelper
import logging

# Set up logging
logger = logging.getLogger(__name__)


class MediaProcessor:
    @staticmethod
    def upload_image(file, **kwargs):
        """
        Upload image to Cloudinary
        """
        try:
            result = CloudinaryHelper.upload_image(file, **kwargs)
            return result.get("url")
        except Exception as e:
            logger.error(f"Error in MediaProcessor.upload_image: {str(e)}")
            raise

    @staticmethod
    def upload_video(file, **kwargs):
        """
        Upload video to Cloudinary and return URL and thumbnail
        """
        try:
            result = CloudinaryHelper.upload_video(file, **kwargs)
            return {
                "video_url": result.get("url"),
                "thumbnail_url": result.get("thumbnail"),
                "public_id": result.get("public_id"),
            }
        except Exception as e:
            logger.error(f"Error in MediaProcessor.upload_video: {str(e)}")
            raise

    @staticmethod
    def upload_audio(file, **kwargs):
        """
        Upload audio to Cloudinary
        """
        try:
            # Audio should use video resource type in Cloudinary, not raw
            result = CloudinaryHelper.upload_audio(file, **kwargs)
            return result.get("url")
        except Exception as e:
            logger.error(f"Error in MediaProcessor.upload_audio: {str(e)}")
            raise

    @staticmethod
    def upload_document(file, **kwargs):
        """
        Upload document to Cloudinary
        """
        try:
            # Use raw resource type for documents
            result = CloudinaryHelper.upload_image(
                file, resource_type="raw", folder="app_documents", **kwargs
            )
            return result.get("url")
        except Exception as e:
            logger.error(f"Error in MediaProcessor.upload_document: {str(e)}")
            raise
