"""
auth.py - Authentication & OTP Dispatch Engine for ScholarCritic.
Uses MongoDB Atlas for credential storage & Gmail SMTP for OTP emails.
"""

import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
import bcrypt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

load_dotenv()

# MongoDB Client singleton
_mongo_client = None


def get_db():
    """Returns connected MongoDB Atlas database instance."""
    global _mongo_client
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI is missing from environment.")
    
    if _mongo_client is None:
        _mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
    
    return _mongo_client["scholar_critic"]


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, hashed_pw: str) -> bool:
    """Verifies a plain-text password against stored bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed_pw.encode("utf-8"))


def generate_otp() -> str:
    """Generates a secure 6-digit numeric OTP."""
    return f"{random.randint(100000, 999999)}"


def send_otp_email(recipient_email: str, otp_code: str) -> bool:
    """
    Sends a styled HTML email with the 6-digit verification OTP via Gmail SMTP.
    """
    smtp_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("MAIL_PORT", "587"))
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")

    if not mail_username or not mail_password:
        raise ValueError("Gmail credentials missing in environment.")

    # Build HTML Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔐 Your ScholarCritic Verification Code: {otp_code}"
    msg["From"] = f"ScholarCritic Security <{mail_username}>"
    msg["To"] = recipient_email

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #070D18; color: #FFFFFF; margin: 0; padding: 30px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #131E33; border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 36px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .header {{ text-align: center; margin-bottom: 24px; }}
            .logo {{ font-size: 24px; font-weight: 800; color: #FFFFFF; text-decoration: none; }}
            .logo strong {{ color: #FA5A4B; }}
            .title {{ font-size: 20px; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; text-align: center; }}
            .subtext {{ color: #94A3B8; font-size: 14px; text-align: center; line-height: 1.5; margin-bottom: 28px; }}
            .otp-box {{ background: #070D18; border: 2px dashed #FA5A4B; border-radius: 12px; padding: 18px; text-align: center; margin: 20px 0; }}
            .otp-code {{ font-size: 38px; font-weight: 800; letter-spacing: 10px; color: #FA5A4B; font-family: monospace; }}
            .warning {{ font-size: 12px; color: #64748B; text-align: center; margin-top: 24px; line-height: 1.4; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">~ Scholar<strong>Critic</strong></div>
            </div>
            <div class="title">Verify Your Sign-In</div>
            <div class="subtext">Use the following 6-digit One-Time Password (OTP) to complete your authentication for ScholarCritic.</div>
            <div class="otp-box">
                <div class="otp-code">{otp_code}</div>
            </div>
            <div class="subtext" style="color: #F8FAFC;">This code will expire in <strong>10 minutes</strong>. Do not share it with anyone.</div>
            <div class="warning">If you did not request this code, you can safely disregard this email.</div>
        </div>
    </body>
    </html>
    """

    part = MIMEText(html_content, "html")
    msg.attach(part)

    # Dispatch through SMTP
    server = smtplib.SMTP(smtp_server, smtp_port, timeout=12)
    server.starttls()
    server.login(mail_username, mail_password)
    server.sendmail(mail_username, recipient_email, msg.as_string())
    server.quit()
    return True


def authenticate_or_register_step1(email: str, password: str, is_signup: bool = False) -> Tuple[bool, str]:
    """
    Step 1: Validates credentials (or registers new user), generates 6-digit OTP,
    stores in MongoDB with 10-minute expiry, and emails the OTP.
    """
    clean_email = email.strip().lower()
    if not clean_email or "@" not in clean_email:
        return False, "Please provide a valid email address."

    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."

    db = get_db()
    users_col = db["users"]
    user = users_col.find_one({"email": clean_email})

    if is_signup:
        if user:
            return False, "An account with this email already exists. Please Sign In."
        # Hash password and create initial record
        pw_hash = hash_password(password)
        otp = generate_otp()
        expiry = datetime.utcnow() + timedelta(minutes=10)

        users_col.insert_one({
            "email": clean_email,
            "password_hash": pw_hash,
            "current_otp": otp,
            "otp_expiry": expiry,
            "is_verified": False,
            "created_at": datetime.utcnow()
        })
    else:
        # Sign In mode
        if not user:
            return False, "No account found with this email. Please Sign Up first."

        if not check_password(password, user["password_hash"]):
            return False, "Incorrect password. Please try again."

        # Generate fresh OTP
        otp = generate_otp()
        expiry = datetime.utcnow() + timedelta(minutes=10)

        users_col.update_one(
            {"email": clean_email},
            {"$set": {"current_otp": otp, "otp_expiry": expiry}}
        )

    # Send the OTP email
    try:
        send_otp_email(clean_email, otp)
    except Exception as e:
        return False, f"Failed to send verification email: {str(e)}"

    return True, f"OTP sent to {clean_email}"


def verify_otp_step2(email: str, entered_otp: str) -> Tuple[bool, str]:
    """
    Step 2: Verifies the entered OTP against MongoDB and checks expiry.
    """
    clean_email = email.strip().lower()
    clean_otp = entered_otp.strip()

    db = get_db()
    users_col = db["users"]
    user = users_col.find_one({"email": clean_email})

    if not user:
        return False, "User not found. Please sign in again."

    saved_otp = user.get("current_otp")
    otp_expiry = user.get("otp_expiry")

    if not saved_otp or not otp_expiry:
        return False, "No active OTP request found. Please request a new code."

    if datetime.utcnow() > otp_expiry:
        return False, "The OTP has expired. Please request a new one."

    if saved_otp != clean_otp:
        return False, "Invalid OTP code. Please check your inbox and try again."

    # Clear OTP on success and mark verified
    users_col.update_one(
        {"email": clean_email},
        {
            "$set": {"is_verified": True, "last_login": datetime.utcnow()},
            "$unset": {"current_otp": "", "otp_expiry": ""}
        }
    )

    return True, "Authentication successful."


def resend_otp(email: str) -> Tuple[bool, str]:
    """Resends a new 6-digit OTP to the registered user."""
    clean_email = email.strip().lower()
    db = get_db()
    user = db["users"].find_one({"email": clean_email})

    if not user:
        return False, "Account not found."

    otp = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=10)

    db["users"].update_one(
        {"email": clean_email},
        {"$set": {"current_otp": otp, "otp_expiry": expiry}}
    )

    try:
        send_otp_email(clean_email, otp)
        return True, "A fresh OTP code has been sent to your email."
    except Exception as e:
        return False, f"Error sending email: {str(e)}"
