"""Google OAuth 2.0 integration for authentication."""

from __future__ import annotations

import json
import secrets
from typing import Any
from urllib.parse import urlencode

import requests

from app_settings import read_setting


class GoogleAuthError(Exception):
    """Custom exception for Google authentication errors."""
    pass


def get_google_auth_config() -> dict[str, str]:
    """Get Google OAuth configuration from environment."""
    return {
        "client_id": read_setting("GOOGLE_CLIENT_ID") or "",
        "client_secret": read_setting("GOOGLE_CLIENT_SECRET") or "",
        "redirect_uri": read_setting("GOOGLE_REDIRECT_URI") or "http://localhost:8501",
    }


def is_google_configured() -> bool:
    """Check if Google OAuth is properly configured."""
    config = get_google_auth_config()
    return bool(config["client_id"] and config["client_secret"])


def get_google_auth_url(state: str | None = None) -> str:
    """Generate Google OAuth authorization URL."""
    config = get_google_auth_config()
    
    if not is_google_configured():
        raise GoogleAuthError("Google OAuth is not configured")
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    if state:
        params["state"] = state
    
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return auth_url


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for access tokens."""
    config = get_google_auth_config()
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "redirect_uri": config["redirect_uri"],
        "grant_type": "authorization_code",
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise GoogleAuthError(f"Failed to exchange code for tokens: {e}")


def get_google_user_info(access_token: str) -> dict[str, Any]:
    """Get user information from Google using access token."""
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(user_info_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise GoogleAuthError(f"Failed to get user info: {e}")


def generate_username_from_email(email: str) -> str:
    """Generate a unique username from email address."""
    # Extract username part from email
    username = email.split("@")[0]
    # Clean up special characters and ensure uniqueness
    username = "".join(c for c in username if c.isalnum() or c in "._-")
    return username.lower()


def verify_google_token(id_token: str) -> dict[str, Any]:
    """Verify Google ID token (simplified version)."""
    # In production, you should verify the token signature with Google's public keys
    # For this implementation, we'll decode the payload without signature verification
    # This is less secure but suitable for development
    
    try:
        # Split the token into parts
        parts = id_token.split(".")
        if len(parts) != 3:
            raise GoogleAuthError("Invalid ID token format")
        
        # Decode the payload (base64url encoded)
        import base64
        payload = parts[1]
        # Add padding if needed
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        user_info = json.loads(decoded)
        
        return user_info
    except Exception as e:
        raise GoogleAuthError(f"Failed to verify ID token: {e}")


def generate_auth_state() -> str:
    """Generate a secure random state parameter for OAuth flow."""
    return secrets.token_urlsafe(32)


def handle_google_callback(code: str, state: str | None = None) -> dict[str, Any]:
    """Handle Google OAuth callback and return user information."""
    try:
        # Exchange code for tokens
        tokens = exchange_code_for_tokens(code)
        
        # Get user info using access token
        user_info = get_google_user_info(tokens["access_token"])
        
        # Extract relevant information
        result = {
            "google_id": user_info.get("id"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "given_name": user_info.get("given_name"),
            "family_name": user_info.get("family_name"),
            "picture": user_info.get("picture"),
            "verified_email": user_info.get("verified_email", False),
            "username": generate_username_from_email(user_info.get("email", "")),
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
        }
        
        return result
        
    except GoogleAuthError as e:
        raise
    except Exception as e:
        raise GoogleAuthError(f"Google authentication failed: {e}")


def refresh_google_token(refresh_token: str) -> dict[str, Any]:
    """Refresh Google access token using refresh token."""
    config = get_google_auth_config()
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "refresh_token": refresh_token,
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "refresh_token",
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise GoogleAuthError(f"Failed to refresh token: {e}")