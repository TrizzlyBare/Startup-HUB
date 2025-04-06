from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_join_request_notification(join_request):
    """Send an email notification to the project owner when a user requests to join"""
    project = join_request.project
    requester = join_request.user
    owner = project.user

    # Validate owner has an email
    if not owner.email:
        logger.warning(
            f"Cannot send join request notification: Project owner {owner.username} has no email address"
        )
        return False

    subject = f"New join request for your project: {project.name}"

    # Plain text email content
    plain_message = f"""
    Hi {owner.get_full_name() or owner.username},
    
    {requester.get_full_name() or requester.username} ({requester.username}) has requested to join your project "{project.name}".
    
    Their message: {join_request.message}
    
    To respond to this request, please visit: {settings.FRONTEND_URL}/projects/{project.id}/join-requests
    
    Thank you,
    Startup Hub Team
    """

    # HTML email content
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4a86e8; color: white; padding: 10px; text-align: center; }}
            .content {{ padding: 20px; }}
            .button {{ display: inline-block; background-color: #4a86e8; color: white; 
                     padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            .message-box {{ background-color: #f5f5f5; padding: 10px; border-left: 4px solid #4a86e8; }}
            .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>New Join Request</h2>
            </div>
            <div class="content">
                <p>Hi {owner.get_full_name() or owner.username},</p>
                
                <p><strong>{requester.get_full_name() or requester.username}</strong> ({requester.username}) has requested to join your project <strong>"{project.name}"</strong>.</p>
                
                {"<p><strong>Their message:</strong></p><p class='message-box'>" + join_request.message + "</p>" if join_request.message else ""}
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="{settings.FRONTEND_URL}/projects/{project.id}/join-requests" class="button">View Join Requests</a>
                </p>
            </div>
            <div class="footer">
                <p>This is an automated message from Startup Hub. Please do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            f"Join request notification sent to {owner.email} for project {project.name}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send join request notification: {str(e)}")
        return False
