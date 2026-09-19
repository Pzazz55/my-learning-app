"""Email service for sending OTPs and exam reports."""

from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any
from datetime import datetime, timezone

import requests

from app_settings import read_setting


class EmailServiceError(Exception):
    """Custom exception for email service errors."""
    pass


def get_email_config() -> dict[str, str]:
    """Get email configuration from environment."""
    return {
        "provider": read_setting("EMAIL_PROVIDER") or "smtp",  # 'smtp' or 'sendgrid' or 'mailgun'
        "smtp_host": read_setting("SMTP_HOST") or "smtp.gmail.com",
        "smtp_port": int(read_setting("SMTP_PORT") or "587"),
        "smtp_username": read_setting("SMTP_USERNAME") or "",
        "smtp_password": read_setting("SMTP_PASSWORD") or "",
        "from_email": read_setting("FROM_EMAIL") or "noreply@studysprint.com",
        "from_name": read_setting("FROM_NAME") or "Study Sprint",
        "sendgrid_api_key": read_setting("SENDGRID_API_KEY") or "",
        "mailgun_api_key": read_setting("MAILGUN_API_KEY") or "",
        "mailgun_domain": read_setting("MAILGUN_DOMAIN") or "",
    }


def is_email_configured() -> bool:
    """Check if email service is properly configured."""
    config = get_email_config()
    if config["provider"] == "smtp":
        return bool(config["smtp_username"] and config["smtp_password"])
    elif config["provider"] == "sendgrid":
        return bool(config["sendgrid_api_key"])
    elif config["provider"] == "mailgun":
        return bool(config["mailgun_api_key"] and config["mailgun_domain"])
    return False


def send_email_smtp(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Send email using SMTP."""
    config = get_email_config()
    
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{config['from_name']} <{config['from_email']}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add plain text version
        msg.attach(MIMEText(body, "plain"))
        
        # Add HTML version if provided
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_username"], config["smtp_password"])
            server.send_message(msg)
        
        return True
    except Exception as e:
        raise EmailServiceError(f"SMTP email failed: {e}")


def send_email_sendgrid(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Send email using SendGrid API."""
    config = get_email_config()
    
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {config['sendgrid_api_key']}",
        "Content-Type": "application/json",
    }
    
    data = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject,
            }
        ],
        "from": {"email": config["from_email"], "name": config["from_name"]},
        "content": [
            {"type": "text/plain", "value": body}
        ]
    }
    
    if html_body:
        data["content"].append({"type": "text/html", "value": html_body})
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        raise EmailServiceError(f"SendGrid email failed: {e}")


def send_email_mailgun(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Send email using Mailgun API."""
    config = get_email_config()
    
    url = f"https://api.mailgun.net/v3/{config['mailgun_domain']}/messages"
    auth = ("api", config["mailgun_api_key"])
    
    data = {
        "from": f"{config['from_name']} <{config['from_email']}>",
        "to": to_email,
        "subject": subject,
        "text": body,
    }
    
    if html_body:
        data["html"] = html_body
    
    try:
        response = requests.post(url, auth=auth, data=data, timeout=30)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        raise EmailServiceError(f"Mailgun email failed: {e}")


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> bool:
    """Send email using configured provider."""
    if not is_email_configured():
        raise EmailServiceError("Email service is not configured")
    
    config = get_email_config()
    provider = config["provider"]
    
    if provider == "smtp":
        return send_email_smtp(to_email, subject, body, html_body)
    elif provider == "sendgrid":
        return send_email_sendgrid(to_email, subject, body, html_body)
    elif provider == "mailgun":
        return send_email_mailgun(to_email, subject, body, html_body)
    else:
        raise EmailServiceError(f"Unknown email provider: {provider}")


def generate_otp_email(otp: str, expiry_minutes: int = 15) -> tuple[str, str]:
    """Generate OTP email content."""
    subject = "Your Password Reset Code - Study Sprint"
    
    body = f"""
Hello,

You have requested to reset your password for Study Sprint.

Your One-Time Password (OTP) is: {otp}

This code will expire in {expiry_minutes} minutes.

If you did not request this password reset, please ignore this email.

Best regards,
Study Sprint Team
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #ef705c; color: white; padding: 20px; text-align: center; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 5px; }}
        .otp {{ background: #f6c94c; color: #17223a; font-size: 24px; font-weight: bold; 
                padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Study Sprint</h1>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>You have requested to reset your password for Study Sprint.</p>
            
            <div class="otp">{otp}</div>
            
            <p><strong>This code will expire in {expiry_minutes} minutes.</strong></p>
            
            <p>If you did not request this password reset, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Study Sprint. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, body, html_body


def generate_exam_report_email(
    student_name: str,
    subject: str,
    score: int,
    correct_count: int,
    wrong_count: int,
    total_questions: int,
    exam_date: str,
    parent_name: str,
    login_url: str
) -> tuple[str, str]:
    """Generate exam report email content."""
    subject = f"Exam Results for {student_name} - {subject}"
    
    body = f"""
Dear {parent_name},

Great news! {student_name} has completed their {subject} exam.

Here are the results:
- Score: {score}%
- Correct Answers: {correct_count}/{total_questions}
- Wrong Answers: {wrong_count}/{total_questions}
- Exam Date: {exam_date}

To view the detailed results and analysis, please click the link below:

{login_url}

This link will take you to the login page where you can review the complete exam details.

Keep up the great work!

Best regards,
Study Sprint Team
"""
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(120deg, #ef705c 0%, #f6c94c 100%); 
                color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 20px; border-radius: 0 0 10px 10px; }}
        .score-box {{ background: #dff3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .score {{ font-size: 36px; font-weight: bold; color: #17324d; text-align: center; }}
        .details {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .detail-item {{ text-align: center; }}
        .detail-value {{ font-size: 24px; font-weight: bold; color: #ef705c; }}
        .cta-button {{ display: block; background: #ef705c; color: white; text-align: center; 
                      padding: 15px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Exam Results</h1>
        </div>
        <div class="content">
            <h2>Great job, {student_name}!</h2>
            <p>{student_name} has completed their {subject} exam.</p>
            
            <div class="score-box">
                <div class="score">{score}%</div>
                <p style="text-align: center; margin: 0;">Overall Score</p>
            </div>
            
            <div class="details">
                <div class="detail-item">
                    <div class="detail-value">{correct_count}</div>
                    <p>Correct</p>
                </div>
                <div class="detail-item">
                    <div class="detail-value">{wrong_count}</div>
                    <p>Wrong</p>
                </div>
                <div class="detail-item">
                    <div class="detail-value">{total_questions}</div>
                    <p>Total</p>
                </div>
            </div>
            
            <p><strong>Exam Date:</strong> {exam_date}</p>
            
            <a href="{login_url}" class="cta-button">View Detailed Results</a>
            
            <p style="text-align: center; color: #666;">
                Click the button above to view the complete exam analysis and detailed breakdown.
            </p>
        </div>
        <div class="footer">
            <p>&copy; {datetime.now().year} Study Sprint. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return subject, body, html_body


def send_otp_email(to_email: str, otp: str, expiry_minutes: int = 15) -> bool:
    """Send OTP email to user."""
    subject, body, html_body = generate_otp_email(otp, expiry_minutes)
    return send_email(to_email, subject, body, html_body)


def send_exam_report_email(
    to_email: str,
    student_name: str,
    subject: str,
    score: int,
    correct_count: int,
    wrong_count: int,
    total_questions: int,
    exam_date: str,
    parent_name: str,
    login_url: str
) -> bool:
    """Send exam report email to parent."""
    subject, body, html_body = generate_exam_report_email(
        student_name, subject, score, correct_count, wrong_count, 
        total_questions, exam_date, parent_name, login_url
    )
    return send_email(to_email, subject, body, html_body)