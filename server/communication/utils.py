import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
import logging
import os
from django.core.exceptions import ValidationError
from io import BytesIO
from PIL import Image

# Set up logging
logger = logging.getLogger(__name__)


class CloudinaryHelper:
    @staticmethod
    def configure():
        """
        Configure Cloudinary with settings from Django settings
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
    def validate_file(file, media_type):
        """
        Validate file size and type
        """
        # Check file size
        if hasattr(file, "size") and file.size > settings.MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE/1024/1024}MB"
            )

        # Check file extension
        if hasattr(file, "name"):
            ext = os.path.splitext(file.name)[1].lower().replace(".", "")
            allowed_extensions = settings.ALLOWED_UPLOAD_EXTENSIONS.get(media_type, [])

            if ext not in allowed_extensions:
                raise ValidationError(
                    f"File extension '{ext}' not allowed. Allowed extensions: {', '.join(allowed_extensions)}"
                )

            return ext
        return None

    @staticmethod
    def upload_image(file, folder="app_images", **kwargs):
        """
        Upload image to Cloudinary with advanced options
        """
        try:
            # Validate file
            ext = CloudinaryHelper.validate_file(file, "image")

            # Optimize image before upload if it's a common format
            if hasattr(file, "content_type") and file.content_type.lower() in [
                "image/jpeg",
                "image/png",
            ]:
                try:
                    img = Image.open(file)
                    output = BytesIO()

                    # Preserve format
                    format = (
                        "JPEG" if file.content_type.lower() == "image/jpeg" else "PNG"
                    )

                    # Save with optimized quality
                    img.save(output, format=format, quality=85, optimize=True)
                    output.seek(0)
                    file = output
                except Exception as e:
                    logger.warning(f"Image optimization failed: {str(e)}")

            upload_options = {
                "folder": folder,
                "resource_type": "image",
                "transformation": [
                    {"quality": "auto:good"},  # Automatic quality optimization
                    {"width": "auto", "crop": "scale"},  # Responsive scaling
                ],
                **kwargs,
            }

            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "version": result["version"],
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Upload Error: {e}")
            raise Exception(f"Cloudinary Upload Error: {e}")
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during image upload: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")

    @staticmethod
    def upload_video(file, folder="app_videos", **kwargs):
        """
        Upload video to Cloudinary with advanced options
        """
        try:
            # Validate file
            CloudinaryHelper.validate_file(file, "video")

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

            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "video_url": result["secure_url"],
                "public_id": result["public_id"],
                "thumbnail_url": (
                    result.get("eager", [{}])[0].get("secure_url", None)
                    if result.get("eager")
                    else None
                ),
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Video Upload Error: {e}")
            raise Exception(f"Cloudinary Video Upload Error: {e}")
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during video upload: {str(e)}")
            raise Exception(f"Failed to upload video: {str(e)}")

    @staticmethod
    def upload_audio(file, folder="app_audio", **kwargs):
        """
        Upload audio to Cloudinary
        """
        try:
            # Validate file
            CloudinaryHelper.validate_file(file, "audio")

            upload_options = {
                "folder": folder,
                "resource_type": "video",  # Audio uses video resource type in Cloudinary
                **kwargs,
            }

            result = cloudinary.uploader.upload(file, **upload_options)
            return result["secure_url"]
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Audio Upload Error: {e}")
            raise Exception(f"Cloudinary Audio Upload Error: {e}")
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during audio upload: {str(e)}")
            raise Exception(f"Failed to upload audio: {str(e)}")

    @staticmethod
    def upload_video(file, folder="app_videos", **kwargs):
        """
        Upload video to Cloudinary with advanced options
        """
        try:
            # Validate file
            CloudinaryHelper.validate_file(file, "video")

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

            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "video_url": result["secure_url"],
                "public_id": result["public_id"],
                "thumbnail_url": (
                    result.get("eager", [{}])[0].get("secure_url", None)
                    if result.get("eager")
                    else None
                ),
            }
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Video Upload Error: {e}")
            return None
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during video upload: {str(e)}")
            return None

    @staticmethod
    def upload_document(file, folder="app_documents", **kwargs):
        """
        Upload document to Cloudinary
        """
        try:
            # Validate file
            CloudinaryHelper.validate_file(file, "document")

            upload_options = {
                "folder": folder,
                "resource_type": "raw",
                **kwargs,
            }

            result = cloudinary.uploader.upload(file, **upload_options)
            return result["secure_url"]
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary Document Upload Error: {e}")
            return None
        except ValidationError as e:
            logger.error(f"Validation Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during document upload: {str(e)}")
            return None

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


class MediaProcessor:
    """
    Utility class for media processing
    """

    @staticmethod
    def upload_image(file):
        return CloudinaryHelper.upload_image(file)

    @staticmethod
    def upload_video(file):
        return CloudinaryHelper.upload_video(file)

    @staticmethod
    def upload_audio(file):
        return CloudinaryHelper.upload_audio(file)

    @staticmethod
    def upload_document(file):
        return CloudinaryHelper.upload_document(file)
