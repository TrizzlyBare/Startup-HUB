import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)


class CloudinaryHelper:
    @staticmethod
    def configure():
        """
        Configure Cloudinary with settings
        """
        try:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
                api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
            )
            logger.info("Cloudinary configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Cloudinary: {str(e)}")
            raise

    @staticmethod
    def upload_image(file, folder="app_images", **kwargs):
        """
        Upload image to Cloudinary with advanced options
        """
        upload_options = {
            "folder": folder,
            "resource_type": (
                "image"
                if "resource_type" not in kwargs
                else kwargs.pop("resource_type")
            ),
            "transformation": [
                {"quality": "auto:good"},  # Automatic quality optimization
                {"width": "auto", "crop": "scale"},  # Responsive scaling
            ],
            **kwargs,
        }

        try:
            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "version": result["version"],
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Upload Error: {e}")
            raise Exception(f"Cloudinary Upload Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during image upload: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")

    @staticmethod
    def upload_video(file, folder="app_videos", **kwargs):
        """
        Upload video to Cloudinary with advanced options
        """
        upload_options = {
            "folder": folder,
            "resource_type": "video",
            "transformation": [
                {"width": 640, "crop": "limit"},  # Maximum width
                {"quality": "auto:good"},  # Quality optimization
            ],
            "eager": [
                # Generate thumbnail
                {"width": 320, "height": 180, "crop": "fill", "format": "jpg"}
            ],
            **kwargs,
        }

        try:
            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "thumbnail": (
                    result.get("eager", [{}])[0].get("secure_url")
                    if result.get("eager")
                    else None
                ),
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Video Upload Error: {e}")
            raise Exception(f"Cloudinary Video Upload Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during video upload: {str(e)}")
            raise Exception(f"Failed to upload video: {str(e)}")

    @staticmethod
    def upload_audio(file, folder="app_audio", **kwargs):
        """
        Upload audio to Cloudinary
        """
        upload_options = {
            "folder": folder,
            "resource_type": "video",  # Audio uses video resource type in Cloudinary
            **kwargs,
        }

        try:
            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Audio Upload Error: {e}")
            raise Exception(f"Cloudinary Audio Upload Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during audio upload: {str(e)}")
            raise Exception(f"Failed to upload audio: {str(e)}")

    @staticmethod
    def delete_resource(public_id, resource_type="image"):
        """
        Delete a resource from Cloudinary
        """
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            return result["result"] == "ok"
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Deletion Error: {e}")
            return False

    @staticmethod
    def generate_transformation_url(
        public_id, width=None, height=None, crop="scale", quality="auto"
    ):
        """
        Generate a transformed URL for an image
        """
        transformation = []

        if width:
            transformation.append({"width": width, "crop": crop})

        if height:
            transformation.append({"height": height, "crop": crop})

        transformation.append({"quality": quality})

        return cloudinary.CloudinaryImage(public_id).build_url(
            transformation=transformation
        )
