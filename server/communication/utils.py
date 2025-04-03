import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings


class CloudinaryHelper:
    @staticmethod
    def configure():
        """
        Configure Cloudinary with settings
        """
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE["dh22uuija"],
            api_key=settings.CLOUDINARY_STORAGE["349497593716885"],
            api_secret=settings.CLOUDINARY_STORAGE["dgib6KclQIU08uYnT4Vdr4EPeT8"],
        )

    @staticmethod
    def upload_image(file, folder="app_images", **kwargs):
        """
        Upload image to Cloudinary with advanced options
        """
        upload_options = {
            "folder": folder,
            "resource_type": "image",
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
            print(f"Cloudinary Upload Error: {e}")
            return None

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
            **kwargs,
        }

        try:
            result = cloudinary.uploader.upload(file, **upload_options)
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "thumbnail": result.get("thumbnail", None),
            }
        except cloudinary.exceptions.Error as e:
            print(f"Cloudinary Video Upload Error: {e}")
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
            print(f"Cloudinary Deletion Error: {e}")
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
