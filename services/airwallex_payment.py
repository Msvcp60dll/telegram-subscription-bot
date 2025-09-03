"""
Airwallex Payment Service
Handles card payments via Airwallex Payment Links API
"""

import os
import json
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import aiohttp
import asyncio
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class AirwallexPaymentService:
    """Service for handling Airwallex payment operations"""
    
    def __init__(self, client_id: str = None, api_key: str = None, webhook_secret: str = None):
        """Initialize Airwallex service with credentials"""
        self.client_id = client_id or os.getenv("AIRWALLEX_CLIENT_ID")
        self.api_key = api_key or os.getenv("AIRWALLEX_API_KEY")
        self.webhook_secret = webhook_secret or os.getenv("AIRWALLEX_WEBHOOK_SECRET", "")
        
        # Set base URL based on environment (use production API)
        self.base_url = os.getenv("AIRWALLEX_BASE_URL", "https://api.airwallex.com")
        self.auth_url = urljoin(self.base_url, "/api/v1/authentication/login")
        self.payment_links_url = urljoin(self.base_url, "/api/v1/pa/payment_links/create")
        
        # Token management
        self.access_token = None
        self.token_expires_at = None
        self.session = None
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
        logger.info(f"Airwallex service initialized with base URL: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def initialize(self):
        """Initialize the service and authenticate"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        await self.authenticate()
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Airwallex API and get access token"""
        if not self.client_id or not self.api_key:
            logger.error("Missing Airwallex credentials")
            return False
        
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return True
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            headers = {
                "Content-Type": "application/json",
                "x-client-id": self.client_id,
                "x-api-key": self.api_key
            }
            
            async with self.session.post(self.auth_url, headers=headers) as response:
                if response.status == 201:
                    data = await response.json()
                    self.access_token = data.get("token")
                    
                    # Token expires in 1 hour, refresh 5 minutes before
                    expires_in = data.get("expires_at", 3600)
                    self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                    
                    logger.info("Successfully authenticated with Airwallex")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Authentication failed: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def create_payment_link(
        self,
        amount: float,
        currency: str = "USD",
        customer_email: str = None,
        customer_name: str = None,
        telegram_id: int = None,
        telegram_username: str = None,
        plan_id: str = None,
        plan_name: str = None,
        expires_in_hours: int = 24,
        webhook_url: str = None
    ) -> Tuple[bool, Dict]:
        """
        Create a payment link for subscription purchase
        
        Returns:
            Tuple of (success: bool, result: dict)
            On success: result contains 'url', 'id', 'status'
            On failure: result contains 'error'
        """
        
        # Ensure we're authenticated
        if not await self.authenticate():
            return False, {"error": "Authentication failed"}
        
        try:
            # Prepare payment link request
            payload = {
                "amount": amount,
                "currency": currency,
                "title": f"Subscription: {plan_name or 'Premium Access'}",
                "description": f"Telegram bot subscription for {plan_name or 'premium access'}",
                "reusable": False,
                "status": "ACTIVE",
                
                # Customer information
                "customer_email": customer_email,
                "customer_name": customer_name or f"User_{telegram_id}",
                
                # Metadata for tracking
                "metadata": {
                    "telegram_id": str(telegram_id) if telegram_id else "",
                    "telegram_username": telegram_username or "",
                    "plan_id": plan_id or "",
                    "plan_name": plan_name or "",
                    "created_at": datetime.now().isoformat()
                },
                
                # Expiry
                "expires_at": (datetime.now() + timedelta(hours=expires_in_hours)).isoformat() + "Z",
                
                # Optional: collect additional info
                "collectable_shopper_info": {
                    "phone_number": False,
                    "shipping_address": False,
                    "message": False,
                    "reference": False
                }
            }
            
            # Add webhook URL if provided
            if webhook_url:
                payload["notification_url"] = webhook_url
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            # Create payment link with retry logic
            for attempt in range(self.max_retries):
                try:
                    async with self.session.post(
                        self.payment_links_url,
                        json=payload,
                        headers=headers
                    ) as response:
                        response_data = await response.json()
                        
                        if response.status in [200, 201]:
                            logger.info(f"Payment link created: {response_data.get('id')}")
                            return True, {
                                "url": response_data.get("url"),
                                "id": response_data.get("id"),
                                "status": response_data.get("status"),
                                "expires_at": response_data.get("expires_at"),
                                "amount": response_data.get("amount"),
                                "currency": response_data.get("currency")
                            }
                        elif response.status == 401:
                            # Token expired, re-authenticate
                            logger.info("Token expired, re-authenticating...")
                            self.access_token = None
                            if await self.authenticate():
                                headers["Authorization"] = f"Bearer {self.access_token}"
                                continue
                            else:
                                return False, {"error": "Re-authentication failed"}
                        else:
                            error_msg = response_data.get("message", "Unknown error")
                            logger.error(f"Payment link creation failed: {error_msg}")
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(self.retry_delay * (attempt + 1))
                                continue
                            
                            return False, {"error": error_msg}
                
                except aiohttp.ClientError as e:
                    logger.error(f"Network error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return False, {"error": f"Network error: {str(e)}"}
            
            return False, {"error": "Max retries exceeded"}
            
        except Exception as e:
            logger.error(f"Unexpected error creating payment link: {e}")
            return False, {"error": str(e)}
    
    async def get_payment_link_status(self, payment_link_id: str) -> Tuple[bool, Dict]:
        """
        Check the status of a payment link
        
        Returns:
            Tuple of (success: bool, result: dict)
        """
        
        if not await self.authenticate():
            return False, {"error": "Authentication failed"}
        
        try:
            url = urljoin(self.base_url, f"/api/v1/pa/payment_links/{payment_link_id}")
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return True, {
                        "id": data.get("id"),
                        "status": data.get("status"),
                        "amount": data.get("amount"),
                        "currency": data.get("currency"),
                        "payment_intent_id": data.get("payment_intent_id"),
                        "metadata": data.get("metadata", {})
                    }
                else:
                    error_text = await response.text()
                    return False, {"error": f"Failed to get status: {error_text}"}
                    
        except Exception as e:
            logger.error(f"Error checking payment link status: {e}")
            return False, {"error": str(e)}
    
    def verify_webhook_signature(self, webhook_id: str, timestamp: str, signature: str) -> bool:
        """
        Verify Airwallex webhook signature
        
        Args:
            webhook_id: The webhook-id from headers
            timestamp: The webhook-timestamp from headers
            signature: The webhook-signature from headers
        
        Returns:
            bool: True if signature is valid
        """
        
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True  # Allow in development
        
        try:
            # Construct the payload string
            payload = f"{webhook_id}.{timestamp}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    async def process_webhook(self, webhook_data: Dict) -> Tuple[bool, Dict]:
        """
        Process Airwallex webhook notification
        
        Returns:
            Tuple of (success: bool, result: dict)
        """
        
        try:
            event_type = webhook_data.get("name")
            event_data = webhook_data.get("data", {})
            
            logger.info(f"Processing webhook event: {event_type}")
            
            if event_type == "payment_intent.succeeded":
                # Payment successful
                payment_intent = event_data.get("object", {})
                return True, {
                    "event": "payment_success",
                    "payment_intent_id": payment_intent.get("id"),
                    "amount": payment_intent.get("amount"),
                    "currency": payment_intent.get("currency"),
                    "metadata": payment_intent.get("metadata", {}),
                    "customer_id": payment_intent.get("customer_id"),
                    "payment_link_id": payment_intent.get("payment_link_id")
                }
                
            elif event_type == "payment_intent.failed":
                # Payment failed
                payment_intent = event_data.get("object", {})
                return True, {
                    "event": "payment_failed",
                    "payment_intent_id": payment_intent.get("id"),
                    "error": payment_intent.get("last_payment_error", {}).get("message"),
                    "metadata": payment_intent.get("metadata", {})
                }
                
            elif event_type == "payment_link.expired":
                # Payment link expired
                payment_link = event_data.get("object", {})
                return True, {
                    "event": "link_expired",
                    "payment_link_id": payment_link.get("id"),
                    "metadata": payment_link.get("metadata", {})
                }
                
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True, {"event": "unhandled", "type": event_type}
                
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False, {"error": str(e)}
    
    async def cancel_payment_link(self, payment_link_id: str) -> bool:
        """
        Cancel/deactivate a payment link
        
        Returns:
            bool: True if successful
        """
        
        if not await self.authenticate():
            return False
        
        try:
            url = urljoin(self.base_url, f"/api/v1/pa/payment_links/{payment_link_id}")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}"
            }
            
            payload = {"status": "INACTIVE"}
            
            async with self.session.patch(url, json=payload, headers=headers) as response:
                if response.status in [200, 204]:
                    logger.info(f"Payment link {payment_link_id} cancelled")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to cancel payment link: {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error cancelling payment link: {e}")
            return False