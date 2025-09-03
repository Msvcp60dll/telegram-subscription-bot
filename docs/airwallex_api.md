# Airwallex Payment API Reference

**Version**: Latest  
**Last Updated**: 2025-09-03  
**Official Documentation**: https://www.airwallex.com/docs/api

## Table of Contents
1. [Authentication and API Setup](#authentication-and-api-setup)
2. [Creating Payment Links](#creating-payment-links)
3. [Webhook Configuration](#webhook-configuration)
4. [Signature Verification](#signature-verification)
5. [Payment Status Checking](#payment-status-checking)
6. [Error Handling](#error-handling)

## Authentication and API Setup

### Environment URLs
```python
# Production
BASE_URL = "https://api.airwallex.com"

# Demo/Sandbox
BASE_URL = "https://api-demo.airwallex.com"
```

### Basic Authentication Setup
```python
import requests
import json
from typing import Optional, Dict, Any

class AirwallexClient:
    def __init__(
        self,
        api_key: str,
        client_id: str,
        bearer_token: str,
        environment: str = "demo"
    ):
        self.api_key = api_key
        self.client_id = client_id
        self.bearer_token = bearer_token
        
        # Set base URL based on environment
        if environment == "production":
            self.base_url = "https://api.airwallex.com"
        else:
            self.base_url = "https://api-demo.airwallex.com"
        
        # Configure headers
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "x-client-id": self.client_id
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Generic request method with error handling"""
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params
            )
            
            # Raise exception for bad status codes
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Handle specific HTTP errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid authentication credentials")
            elif response.status_code == 400:
                error_data = response.json()
                raise ValidationError(f"Validation error: {error_data}")
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise APIError(f"API error: {e}")
                
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error: {e}")
```

### Authentication Token Management
```python
import time
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, client_id: str, api_key: str):
        self.client_id = client_id
        self.api_key = api_key
        self.token = None
        self.token_expires_at = None
    
    def get_token(self) -> str:
        """Get valid token, refreshing if necessary"""
        
        if self.token and self.token_expires_at > datetime.now():
            return self.token
        
        # Refresh token
        self.token = self._refresh_token()
        self.token_expires_at = datetime.now() + timedelta(hours=1)
        
        return self.token
    
    def _refresh_token(self) -> str:
        """Refresh authentication token"""
        
        response = requests.post(
            "https://api-demo.airwallex.com/api/v1/authentication/token",
            headers={
                "x-api-key": self.api_key,
                "x-client-id": self.client_id
            }
        )
        
        response.raise_for_status()
        return response.json()["token"]
```

## Creating Payment Links

### Fixed Amount Payment Link
```python
def create_fixed_payment_link(
    self,
    amount: float,
    currency: str,
    title: str,
    description: Optional[str] = None,
    customer_email: Optional[str] = None,
    reference: Optional[str] = None,
    expires_in_hours: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a payment link with a fixed amount
    
    Args:
        amount: Payment amount
        currency: Currency code (USD, EUR, GBP, etc.)
        title: Title for the payment
        description: Optional description
        customer_email: Pre-fill customer email
        reference: Your internal reference
        expires_in_hours: Link expiration time
    
    Returns:
        Payment link details including URL
    """
    
    endpoint = "/api/v1/payment_links/create"
    
    # Calculate expiration if specified
    expires_at = None
    if expires_in_hours:
        expires_at = (
            datetime.now() + timedelta(hours=expires_in_hours)
        ).isoformat()
    
    payload = {
        "amount": amount,
        "currency": currency,
        "title": title,
        "reusable": False,
        "collectable_shopper_info": {
            "phone_number": True,
            "shipping_address": False,
            "message": True,
            "reference": bool(reference)
        }
    }
    
    # Add optional fields
    if description:
        payload["description"] = description
    
    if customer_email:
        payload["customer_email"] = customer_email
    
    if reference:
        payload["reference"] = reference
    
    if expires_at:
        payload["expires_at"] = expires_at
    
    response = self._make_request("POST", endpoint, data=payload)
    
    return {
        "id": response["id"],
        "url": response["url"],
        "amount": response["amount"],
        "currency": response["currency"],
        "status": response["status"],
        "created_at": response["created_at"],
        "expires_at": response.get("expires_at")
    }
```

### Flexible Amount Payment Link
```python
def create_flexible_payment_link(
    self,
    title: str,
    supported_currencies: List[str],
    default_currency: str = "USD",
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a payment link where customer enters the amount
    
    Args:
        title: Title for the payment
        supported_currencies: List of supported currency codes
        default_currency: Default currency to display
        min_amount: Minimum allowed amount
        max_amount: Maximum allowed amount
        description: Optional description
    
    Returns:
        Payment link details including URL
    """
    
    endpoint = "/api/v1/payment_links/create"
    
    payload = {
        "supported_currencies": supported_currencies,
        "default_currency": default_currency,
        "title": title,
        "reusable": True,
        "collectable_shopper_info": {
            "phone_number": True,
            "shipping_address": False,
            "message": True,
            "reference": True
        }
    }
    
    # Add optional fields
    if description:
        payload["description"] = description
    
    if min_amount:
        payload["min_amount"] = min_amount
    
    if max_amount:
        payload["max_amount"] = max_amount
    
    response = self._make_request("POST", endpoint, data=payload)
    
    return response
```

### Update Payment Link
```python
def update_payment_link(
    self,
    payment_link_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Update an existing payment link
    
    Args:
        payment_link_id: ID of the payment link to update
        title: New title
        description: New description
        active: Activate/deactivate the link
    
    Returns:
        Updated payment link details
    """
    
    endpoint = f"/api/v1/payment_links/{payment_link_id}"
    
    payload = {}
    
    if title is not None:
        payload["title"] = title
    
    if description is not None:
        payload["description"] = description
    
    if active is not None:
        payload["active"] = active
    
    response = self._make_request("PATCH", endpoint, data=payload)
    
    return response
```

### Deactivate Payment Link
```python
def deactivate_payment_link(self, payment_link_id: str) -> bool:
    """
    Deactivate a payment link
    
    Args:
        payment_link_id: ID of the payment link
    
    Returns:
        Success status
    """
    
    endpoint = f"/api/v1/payment_links/{payment_link_id}/deactivate"
    
    try:
        self._make_request("POST", endpoint)
        return True
    except Exception as e:
        print(f"Failed to deactivate payment link: {e}")
        return False
```

## Webhook Configuration

### Webhook Event Handler
```python
from typing import Callable
import hmac
import hashlib

class WebhookHandler:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.handlers = {}
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific event type"""
        self.handlers[event_type] = handler
    
    def process_webhook(
        self,
        body: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Process incoming webhook
        
        Args:
            body: Raw request body (JSON string)
            headers: Request headers including signature
        
        Returns:
            Processing result
        """
        
        # Verify signature
        if not self._verify_signature(body, headers):
            raise SignatureVerificationError("Invalid webhook signature")
        
        # Parse webhook data
        data = json.loads(body)
        event_type = data.get("type")
        
        # Find and execute handler
        handler = self.handlers.get(event_type)
        if handler:
            return handler(data)
        else:
            print(f"No handler for event type: {event_type}")
            return {"status": "ignored"}
```

### Common Webhook Event Handlers
```python
# Payment Intent Succeeded Handler
async def handle_payment_succeeded(data: Dict[str, Any]):
    """Handle successful payment notification"""
    
    payment_intent = data["data"]
    
    # Extract relevant information
    payment_info = {
        "id": payment_intent["id"],
        "amount": payment_intent["amount"],
        "currency": payment_intent["currency"],
        "customer_email": payment_intent.get("customer_email"),
        "reference": payment_intent.get("reference"),
        "status": payment_intent["status"],
        "created_at": payment_intent["created_at"]
    }
    
    # Process payment (update database, send confirmation, etc.)
    await process_successful_payment(payment_info)
    
    return {"status": "processed"}

# Payment Failed Handler
async def handle_payment_failed(data: Dict[str, Any]):
    """Handle failed payment notification"""
    
    payment_intent = data["data"]
    error_message = payment_intent.get("last_payment_error", {}).get("message")
    
    # Log failure
    print(f"Payment {payment_intent['id']} failed: {error_message}")
    
    # Notify customer
    await notify_payment_failure(
        payment_intent["customer_email"],
        error_message
    )
    
    return {"status": "processed"}

# Refund Completed Handler
async def handle_refund_completed(data: Dict[str, Any]):
    """Handle refund completion notification"""
    
    refund = data["data"]
    
    # Update database
    await mark_payment_refunded(
        payment_id=refund["payment_intent_id"],
        refund_id=refund["id"],
        amount=refund["amount"]
    )
    
    return {"status": "processed"}
```

### Webhook Endpoint Setup (Flask Example)
```python
from flask import Flask, request, jsonify

app = Flask(__name__)
webhook_handler = WebhookHandler(webhook_secret="your_webhook_secret")

# Register handlers
webhook_handler.register_handler(
    "payment_intent.succeeded",
    handle_payment_succeeded
)
webhook_handler.register_handler(
    "payment_intent.payment_failed",
    handle_payment_failed
)

@app.route("/webhook", methods=["POST"])
def webhook_endpoint():
    """Webhook endpoint for Airwallex notifications"""
    
    try:
        # Get raw body and headers
        body = request.get_data(as_text=True)
        headers = dict(request.headers)
        
        # Process webhook
        result = webhook_handler.process_webhook(body, headers)
        
        return jsonify(result), 200
        
    except SignatureVerificationError as e:
        return jsonify({"error": "Invalid signature"}), 401
        
    except Exception as e:
        print(f"Webhook processing error: {e}")
        return jsonify({"error": "Processing failed"}), 500
```

## Signature Verification

### Webhook Signature Verification
```python
import hmac
import hashlib

def _verify_signature(
    self,
    body: str,
    headers: Dict[str, str]
) -> bool:
    """
    Verify webhook signature
    
    Args:
        body: Raw request body (JSON string)
        headers: Request headers
    
    Returns:
        True if signature is valid
    """
    
    # Extract timestamp and signature from headers
    timestamp = headers.get("x-timestamp")
    signature = headers.get("x-signature")
    
    if not timestamp or not signature:
        return False
    
    # Prepare the value to digest
    # Concatenate: timestamp + body
    value_to_digest = f"{timestamp}{body}"
    
    # Compute HMAC with SHA-256
    expected_signature = hmac.new(
        self.webhook_secret.encode(),
        value_to_digest.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature, expected_signature)
```

### Enhanced Signature Verification with Timing Attack Protection
```python
import time

def verify_webhook_with_timestamp(
    self,
    body: str,
    headers: Dict[str, str],
    max_age_seconds: int = 300
) -> bool:
    """
    Verify webhook signature with timestamp validation
    
    Args:
        body: Raw request body
        headers: Request headers
        max_age_seconds: Maximum age of webhook in seconds
    
    Returns:
        True if signature is valid and not expired
    """
    
    timestamp = headers.get("x-timestamp")
    signature = headers.get("x-signature")
    
    if not timestamp or not signature:
        return False
    
    # Check timestamp age
    try:
        timestamp_int = int(timestamp)
        current_time = int(time.time())
        
        if abs(current_time - timestamp_int) > max_age_seconds:
            print("Webhook timestamp too old")
            return False
    
    except ValueError:
        return False
    
    # Verify signature
    value_to_digest = f"{timestamp}{body}"
    
    expected_signature = hmac.new(
        self.webhook_secret.encode(),
        value_to_digest.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Use constant-time comparison
    return hmac.compare_digest(signature, expected_signature)
```

## Payment Status Checking

### Get Payment Link Status
```python
def get_payment_link(self, payment_link_id: str) -> Dict[str, Any]:
    """
    Get payment link details and status
    
    Args:
        payment_link_id: ID of the payment link
    
    Returns:
        Payment link details including status
    """
    
    endpoint = f"/api/v1/payment_links/{payment_link_id}"
    
    response = self._make_request("GET", endpoint)
    
    return {
        "id": response["id"],
        "url": response["url"],
        "status": response["status"],
        "amount": response.get("amount"),
        "currency": response.get("currency"),
        "payment_intents": response.get("payment_intents", []),
        "created_at": response["created_at"],
        "updated_at": response["updated_at"]
    }
```

### List Payment Links with Filters
```python
def list_payment_links(
    self,
    status: Optional[str] = None,
    created_after: Optional[datetime] = None,
    created_before: Optional[datetime] = None,
    limit: int = 20,
    page: int = 1
) -> Dict[str, Any]:
    """
    List payment links with optional filters
    
    Args:
        status: Filter by status (active, inactive, expired)
        created_after: Filter by creation date
        created_before: Filter by creation date
        limit: Number of results per page
        page: Page number
    
    Returns:
        List of payment links and pagination info
    """
    
    endpoint = "/api/v1/payment_links"
    
    params = {
        "limit": limit,
        "page": page
    }
    
    if status:
        params["status"] = status
    
    if created_after:
        params["created_after"] = created_after.isoformat()
    
    if created_before:
        params["created_before"] = created_before.isoformat()
    
    response = self._make_request("GET", endpoint, params=params)
    
    return response
```

### Check Payment Intent Status
```python
def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
    """
    Get payment intent details
    
    Args:
        payment_intent_id: ID of the payment intent
    
    Returns:
        Payment intent details including status
    """
    
    endpoint = f"/api/v1/payment_intents/{payment_intent_id}"
    
    response = self._make_request("GET", endpoint)
    
    return {
        "id": response["id"],
        "amount": response["amount"],
        "currency": response["currency"],
        "status": response["status"],
        "payment_method": response.get("payment_method"),
        "customer": response.get("customer"),
        "created_at": response["created_at"],
        "confirmed_at": response.get("confirmed_at")
    }
```

## Error Handling

### Custom Exception Classes
```python
class AirwallexError(Exception):
    """Base exception for Airwallex API errors"""
    pass

class AuthenticationError(AirwallexError):
    """Authentication failed"""
    pass

class ValidationError(AirwallexError):
    """Request validation failed"""
    pass

class RateLimitError(AirwallexError):
    """Rate limit exceeded"""
    pass

class APIError(AirwallexError):
    """Generic API error"""
    pass

class NetworkError(AirwallexError):
    """Network communication error"""
    pass

class SignatureVerificationError(AirwallexError):
    """Webhook signature verification failed"""
    pass
```

### Comprehensive Error Handler
```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ErrorHandler:
    @staticmethod
    def handle_api_error(
        error: Exception,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Handle API errors with logging and user-friendly messages
        
        Args:
            error: The exception that occurred
            context: Additional context for logging
        
        Returns:
            Error response dict
        """
        
        error_response = {
            "success": False,
            "error_type": type(error).__name__,
            "message": str(error),
            "user_message": "An error occurred. Please try again."
        }
        
        if isinstance(error, AuthenticationError):
            logger.error(f"Authentication failed: {error}", extra=context)
            error_response["user_message"] = "Authentication failed. Please check credentials."
            
        elif isinstance(error, ValidationError):
            logger.warning(f"Validation error: {error}", extra=context)
            error_response["user_message"] = "Invalid request data provided."
            
        elif isinstance(error, RateLimitError):
            logger.warning(f"Rate limit exceeded: {error}", extra=context)
            error_response["user_message"] = "Too many requests. Please wait and try again."
            
        elif isinstance(error, NetworkError):
            logger.error(f"Network error: {error}", extra=context)
            error_response["user_message"] = "Network error. Please check your connection."
            
        else:
            logger.error(f"Unexpected error: {error}", extra=context)
            error_response["user_message"] = "An unexpected error occurred."
        
        return error_response
```

### Retry Logic with Exponential Backoff
```python
import time
from typing import Callable, Any

def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
) -> Any:
    """
    Retry function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
    
    Returns:
        Function result
    
    Raises:
        Last exception if all retries fail
    """
    
    delay = base_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
            
        except (NetworkError, RateLimitError) as e:
            last_exception = e
            
            if attempt < max_retries:
                # Calculate next delay with exponential backoff
                delay = min(delay * exponential_base, max_delay)
                
                # Add jitter to prevent thundering herd
                jitter = delay * 0.1 * (0.5 - random.random())
                actual_delay = delay + jitter
                
                logger.info(f"Retry {attempt + 1}/{max_retries} after {actual_delay:.2f}s")
                time.sleep(actual_delay)
            else:
                logger.error(f"All retries failed: {e}")
    
    raise last_exception
```

## Complete Implementation Example

```python
import asyncio
from datetime import datetime, timedelta

class AirwallexPaymentService:
    def __init__(self, config: Dict[str, str]):
        self.client = AirwallexClient(
            api_key=config["api_key"],
            client_id=config["client_id"],
            bearer_token=config["bearer_token"],
            environment=config.get("environment", "demo")
        )
        
        self.webhook_handler = WebhookHandler(
            webhook_secret=config["webhook_secret"]
        )
        
        self._setup_webhook_handlers()
    
    def _setup_webhook_handlers(self):
        """Setup webhook event handlers"""
        
        self.webhook_handler.register_handler(
            "payment_intent.succeeded",
            self.handle_payment_success
        )
        
        self.webhook_handler.register_handler(
            "payment_intent.payment_failed",
            self.handle_payment_failure
        )
    
    async def create_subscription_payment(
        self,
        user_id: int,
        plan: str,
        amount: float,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Create payment link for subscription"""
        
        try:
            # Create payment link
            payment_link = await asyncio.to_thread(
                self.client.create_fixed_payment_link,
                amount=amount,
                currency=currency,
                title=f"Subscription - {plan} Plan",
                description=f"Monthly subscription for {plan} plan",
                reference=f"sub_{user_id}_{plan}",
                expires_in_hours=24
            )
            
            # Store payment link in database
            await self.store_payment_link(
                user_id=user_id,
                payment_link_id=payment_link["id"],
                amount=amount,
                plan=plan
            )
            
            return {
                "success": True,
                "payment_url": payment_link["url"],
                "expires_at": payment_link["expires_at"]
            }
            
        except Exception as e:
            return ErrorHandler.handle_api_error(e, {
                "user_id": user_id,
                "plan": plan
            })
    
    async def handle_payment_success(self, data: Dict[str, Any]):
        """Handle successful payment webhook"""
        
        payment_intent = data["data"]
        reference = payment_intent.get("reference", "")
        
        # Parse reference
        if reference.startswith("sub_"):
            parts = reference.split("_")
            user_id = int(parts[1])
            plan = parts[2]
            
            # Activate subscription
            await self.activate_subscription(
                user_id=user_id,
                plan=plan,
                payment_id=payment_intent["id"]
            )
            
            # Send confirmation
            await self.send_payment_confirmation(
                user_id=user_id,
                amount=payment_intent["amount"],
                currency=payment_intent["currency"]
            )
    
    async def handle_payment_failure(self, data: Dict[str, Any]):
        """Handle failed payment webhook"""
        
        payment_intent = data["data"]
        
        # Log failure
        logger.error(f"Payment failed: {payment_intent}")
        
        # Notify user
        reference = payment_intent.get("reference", "")
        if reference.startswith("sub_"):
            user_id = int(reference.split("_")[1])
            await self.notify_payment_failure(user_id)
```

## Best Practices

1. **Always use HTTPS** for webhook endpoints
2. **Verify webhook signatures** before processing
3. **Implement idempotency** for webhook handlers
4. **Use exponential backoff** for retries
5. **Log all API interactions** for debugging
6. **Store payment references** for reconciliation
7. **Handle partial failures** gracefully
8. **Test in sandbox** before production
9. **Monitor webhook delivery** success rates
10. **Implement proper error handling** for all API calls

## Rate Limits

- API calls are rate-limited per account
- Implement exponential backoff for rate limit errors
- Cache frequently accessed data when possible
- Batch operations where supported

## Additional Resources

- Official API Documentation: https://www.airwallex.com/docs/api
- Payment Links Guide: https://www.airwallex.com/docs/payments__payment-links-api
- Webhook Events: https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events
- Integration Guide: https://www.airwallex.com/docs/payments__integrate-with-payment-links-api