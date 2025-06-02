"""
AzamPay Integration Module for Pona Health

This module handles all AzamPay payment processing functionality.
"""

import os
import json
import logging
import requests
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='azampay.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('azampay')

# AzamPay API Configuration
AZAMPAY_CLIENT_ID = "84729511-6899-4e29-9d6d-3cca444a8c2c"
AZAMPAY_SECRET_KEY = "J1gxAW4i0lO1tv07/g+KHrOuSeBRJTbOj9KN/Fuw5aCdMLKWzWgRBAMhPFkyVHZcCHb7NsfUG50NkFOeeFRIE6b4il+JCb40+Syg5ZR3GZyWQlHzzUoAvIXC8aK2Y487AmAI3DtVkP3Qf2gUKoWkeRP370thg4/mfN/EKAysuB8M0El7U91X0B3RpYEQBWwvCsjgpBOa7YiRdFcBhdlfkv9dkK1+BISHxkFdfzSO7EvMIuwSS7hycVwQpJUqNYNmFi+lgrVDvYmChMWzqk+cULQpR8YNylgycCw/HnJujL2TplqYMxNkIf+MVoLVS44f5R3emdJH/WjOpj09UaUr5DVCgyDZ+B+MnNhVkmVt0QhcYTcgODABmXkB42+RxiVBj8CWjmHg6QoMld36F4PQraeWFPRFxWSFK2n/hFQxBqPdndGp28Kv5s/2qtsHbQlXWI9yBCgW6BR9joOhpPnSHfo1vgQ2bxI8SH/rmKJx3NE++GKgNCeJHqjLXVWlHCAWd1OBugrpx1p15yS7TReD4Eg3pGLmMMFVvyP4dd0Hu809u3NBAMM6TPRUiFJWuptlHcC161Y82bIETW+n123yeOJMwrRay7YLtjJ5CTUMnzvgd/G28ZcxEXuin5d/Ryu23uXhmpblrRHLtPaBX6S/Ix6INgRhHar4dAxz8nwAFKc="

# API Endpoints
AZAMPAY_BASE_URL = "https://sandbox.azampay.co.tz"  # Use sandbox for testing
AZAMPAY_TOKEN_URL = f"{AZAMPAY_BASE_URL}/AppRegistration/GenerateToken"
AZAMPAY_CHECKOUT_URL = f"{AZAMPAY_BASE_URL}/azampay/api/v1/payments/mno/checkout"

# Callback URL for payment notifications
CALLBACK_URL = "https://ponahealth.com/api/payments/azampay/callback"

def get_auth_token():
    """
    Get authentication token from AzamPay API
    """
    logger.info("Requesting authentication token from AzamPay")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "appName": "Pona Health",
        "clientId": AZAMPAY_CLIENT_ID,
        "clientSecret": AZAMPAY_SECRET_KEY
    }
    
    # Log the request details for debugging
    logger.info(f"Token request URL: {AZAMPAY_TOKEN_URL}")
    logger.info(f"Token request payload structure: {list(payload.keys())}")
    
    try:
        logger.debug(f"Token request payload: {json.dumps(payload)}")
        response = requests.post(AZAMPAY_TOKEN_URL, json=payload, headers=headers)
        logger.debug(f"Token response status: {response.status_code}")
        logger.debug(f"Token response body: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            logger.info("Successfully obtained authentication token")
            return token_data.get("data", {}).get("accessToken")
        else:
            logger.error(f"Failed to get authentication token. Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        logger.exception(f"Exception during token request: {str(e)}")
        return None

def process_payment(payment_data):
    """
    Process payment through AzamPay
    
    Args:
        payment_data (dict): Payment information including:
            - amount: Payment amount
            - phone: Customer phone number
            - name: Customer name
            - provider: Payment provider (e.g., 'Airtel', 'Tigo', 'Mpesa')
            - reference: Unique payment reference
    
    Returns:
        dict: Payment processing result
    """
    logger.info(f"Processing payment: {json.dumps(payment_data)}")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        logger.error("Cannot process payment: Failed to obtain authentication token")
        return {"success": False, "message": "Authentication failed"}
    
    # Prepare payment request
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Format phone number (remove leading zero if present)
    phone = payment_data.get("phone", "")
    if phone.startswith("0"):
        phone = "255" + phone[1:]
    elif not phone.startswith("255"):
        phone = "255" + phone
    
    # Map provider names to AzamPay expected values
    provider_mapping = {
        "Airtel": "Airtel",
        "AirtelMoney": "Airtel",
        "Tigo": "Tigo",
        "TigoPesa": "Tigo",
        "Mpesa": "Mpesa",
        "M-Pesa": "Mpesa",
        "Halotel": "Halotel",
        "HaloPesa": "Halotel"
    }
    
    provider = provider_mapping.get(payment_data.get("provider", ""), payment_data.get("provider", ""))
    
    # Generate unique transaction ID if not provided
    transaction_id = payment_data.get("reference", f"PONA-{int(time.time())}")
    
    payload = {
        "accountNumber": phone,
        "amount": payment_data.get("amount", 0),
        "currency": "TZS",
        "externalId": transaction_id,
        "provider": provider,
        "additionalProperties": {
            "property1": None,
            "property2": None
        },
        "callbackUrl": CALLBACK_URL
    }
    
    try:
        logger.debug(f"Payment request payload: {json.dumps(payload)}")
        logger.debug(f"Payment request headers: {json.dumps(headers)}")
        
        response = requests.post(AZAMPAY_CHECKOUT_URL, json=payload, headers=headers)
        
        logger.debug(f"Payment response status: {response.status_code}")
        logger.debug(f"Payment response body: {response.text}")
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Payment request successful for transaction {transaction_id}")
            return {
                "success": True,
                "message": "Payment request sent successfully",
                "transaction_id": transaction_id,
                "response": response.json()
            }
        else:
            logger.error(f"Payment request failed. Status: {response.status_code}, Response: {response.text}")
            return {
                "success": False,
                "message": f"Payment request failed: {response.text}",
                "status_code": response.status_code
            }
    except Exception as e:
        logger.exception(f"Exception during payment processing: {str(e)}")
        return {"success": False, "message": f"Payment processing error: {str(e)}"}

def verify_payment(transaction_id):
    """
    Verify payment status for a given transaction
    
    Args:
        transaction_id (str): Transaction ID to verify
        
    Returns:
        dict: Payment verification result
    """
    logger.info(f"Verifying payment for transaction: {transaction_id}")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        logger.error("Cannot verify payment: Failed to obtain authentication token")
        return {"success": False, "message": "Authentication failed"}
    
    # Prepare verification request
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    verification_url = f"{AZAMPAY_BASE_URL}/azampay/api/v1/payments/status/{transaction_id}"
    
    try:
        logger.debug(f"Verification request URL: {verification_url}")
        response = requests.get(verification_url, headers=headers)
        
        logger.debug(f"Verification response status: {response.status_code}")
        logger.debug(f"Verification response body: {response.text}")
        
        if response.status_code == 200:
            verification_data = response.json()
            logger.info(f"Payment verification successful for transaction {transaction_id}")
            return {
                "success": True,
                "status": verification_data.get("status", "UNKNOWN"),
                "data": verification_data
            }
        else:
            logger.error(f"Payment verification failed. Status: {response.status_code}, Response: {response.text}")
            return {
                "success": False,
                "message": f"Verification failed: {response.text}",
                "status_code": response.status_code
            }
    except Exception as e:
        logger.exception(f"Exception during payment verification: {str(e)}")
        return {"success": False, "message": f"Verification error: {str(e)}"}

def handle_callback(callback_data):
    """
    Handle payment callback from AzamPay
    
    Args:
        callback_data (dict): Callback data from AzamPay
        
    Returns:
        dict: Processed callback result
    """
    logger.info(f"Received payment callback: {json.dumps(callback_data)}")
    
    try:
        # Extract relevant information from callback
        transaction_id = callback_data.get("externalId", "")
        status = callback_data.get("status", "")
        message = callback_data.get("message", "")
        
        logger.info(f"Payment callback for transaction {transaction_id}: Status={status}, Message={message}")
        
        # Process based on status
        if status.upper() == "SUCCESS":
            logger.info(f"Payment successful for transaction {transaction_id}")
            return {
                "success": True,
                "transaction_id": transaction_id,
                "status": "SUCCESS",
                "message": "Payment completed successfully"
            }
        else:
            logger.warning(f"Payment not successful for transaction {transaction_id}: {message}")
            return {
                "success": False,
                "transaction_id": transaction_id,
                "status": status,
                "message": message
            }
    except Exception as e:
        logger.exception(f"Exception during callback processing: {str(e)}")
        return {"success": False, "message": f"Callback processing error: {str(e)}"}

# Test function to validate integration
def test_payment():
    """
    Test payment integration with AzamPay
    """
    logger.info("Running test payment")
    
    test_data = {
        "amount": 5000,
        "phone": "0687511886",
        "name": "SHABANI BUSEGA",
        "provider": "Airtel",
        "reference": f"TEST-{int(time.time())}"
    }
    
    result = process_payment(test_data)
    logger.info(f"Test payment result: {json.dumps(result)}")
    return result

# If this module is run directly, perform a test payment
if __name__ == "__main__":
    test_payment()
