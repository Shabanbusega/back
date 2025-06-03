"""
Minimal Flask application for AzamPay payment processing
"""

from flask import Flask, jsonify, request
import datetime
import json
import logging
import requests
import time
import uuid
import re
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('minimal_payment_app')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# AzamPay API Configuration
AZAMPAY_CLIENT_ID = "84729511-6899-4e29-9d6d-3cca444a8c2c"
AZAMPAY_SECRET_KEY = "J1gxAW4i0lO1tv07/g+KHrOuSeBRJTbOj9KN/Fuw5aCdMLKWzWgRBAMhPFkyVHZcCHb7NsfUG50NkFOeeFRIE6b4il+JCb40+Syg5ZR3GZyWQlHzzUoAvIXC8aK2Y487AmAI3DtVkP3Qf2gUKoWkeRP370thg4/mfN/EKAysuB8M0El7U91X0B3RpYEQBWwvCsjgpBOa7YiRdFcBhdlfkv9dkK1+BISHxkFdfzSO7EvMIuwSS7hycVwQpJUqNYNmFi+lgrVDvYmChMWzqk+cULQpR8YNylgycCw/HnJujL2TplqYMxNkIf+MVoLVS44f5R3emdJH/WjOpj09UaUr5DVCgyDZ+B+MnNhVkmVt0QhcYTcgODABmXkB42+RxiVBj8CWjmHg6QoMld36F4PQraeWFPRFxWSFK2n/hFQxBqPdndGp28Kv5s/2qtsHbQlXWI9yBCgW6BR9joOhpPnSHfo1vgQ2bxI8SH/rmKJx3NE++GKgNCeJHqjLXVWlHCAWd1OBugrpx1p15yS7TReD4Eg3pGLmMMFVvyP4dd0Hu809u3NBAMM6TPRUiFJWuptlHcC161Y82bIETW+n123yeOJMwrRay7YLtjJ5CTUMnzvgd/G28ZcxEXuin5d/Ryu23uXhmpblrRHLtPaBX6S/Ix6INgRhHar4dAxz8nwAFKc="

# API Endpoints
AZAMPAY_BASE_URL = "https://sandbox.azampay.co.tz"  # Use sandbox for testing
AZAMPAY_TOKEN_URL = f"{AZAMPAY_BASE_URL}/AppRegistration/GenerateToken"
AZAMPAY_CHECKOUT_URL = f"{AZAMPAY_BASE_URL}/azampay/api/v1/payments/mno/checkout"

# Callback URL for payment notifications
CALLBACK_URL = "https://ponahealth.com/api/payments/azampay/callback"

@app.route('/')
def index():
    return "Pona Health Minimal Payment API Server"
    
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "Minimal Payment API server is running",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def get_azampay_token():
    """
    Get authentication token from AzamPay API
    """
    logger.info("Requesting AzamPay token")
    
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
        logger.exception(f"Error getting AzamPay token: {str(e)}")
        return None

@app.route('/api/payments/azampay/checkout', methods=['POST', 'OPTIONS'])
def azampay_checkout():
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        logger.info(f"AzamPay checkout request received: {data}")
        
        payment_id = str(uuid.uuid4())
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Extract payment details
        name = data.get('name')
        phone = data.get('phone')
        payment_method = data.get('payment_method', '').lower()
        
        # Handle amount with robust string-to-float conversion
        try:
            # Get amount as string first
            amount_raw = data.get('amount', '0')
            logger.info(f"Raw amount received: {amount_raw}, type: {type(amount_raw)}")
            
            # Convert to string if it's not already
            amount_str = str(amount_raw)
            
            # Remove all non-numeric characters except decimal point
            import re
            # First replace comma with dot if it might be a decimal separator
            if ',' in amount_str and '.' not in amount_str:
                amount_str = amount_str.replace(',', '.')
            
            # Then remove all remaining non-numeric characters
            amount_str = re.sub(r'[^\d.]', '', amount_str)
            logger.info(f"Sanitized amount string: {amount_str}")
            
            # Convert to float
            amount = float(amount_str)
            logger.info(f"Converted amount to float: {amount}")
        except Exception as e:
            logger.error(f"Amount conversion error: {str(e)} for input: {data.get('amount')}")
            return jsonify({
                'success': False,
                'message': f"Invalid amount format: {data.get('amount')}"
            }), 400
            
        package_type = data.get('package_type', 'single')
        doctor_type = data.get('doctor_type', 'general')
        is_emergency = data.get('is_emergency', False)
        country = data.get('country', 'Tanzania')
        
        # Map payment method to AzamPay provider with comprehensive normalization
        # First normalize the payment method string
        payment_method_normalized = payment_method.lower().replace(' ', '').replace('-', '').replace('_', '')
        logger.info(f"Normalized payment method: {payment_method_normalized} from original: {payment_method}")
        
        # Comprehensive mapping of all possible variations
        provider_map = {
            # M-Pesa variations
            'mpesa': 'Mpesa',
            'm-pesa': 'Mpesa',
            'mpesatz': 'Mpesa',
            'm-pesatz': 'Mpesa',
            'mpesatanzania': 'Mpesa',
            
            # Tigo variations
            'tigo': 'Tigo',
            'tigopesa': 'Tigo',
            'tigo-pesa': 'Tigo',
            'tigomoney': 'Tigo',
            'tigo-money': 'Tigo',
            
            # Airtel variations
            'airtel': 'Airtel',
            'airtelmoney': 'Airtel',
            'airtel-money': 'Airtel',
            'airteltanzania': 'Airtel',
            'airteltz': 'Airtel',
            
            # Halo Pesa variations
            'halo': 'Halopesa',
            'halopesa': 'Halopesa',
            'halo-pesa': 'Halopesa',
            'halopesatz': 'Halopesa'
        }
        
        # Try to get provider from normalized map first
        provider = provider_map.get(payment_method_normalized)
        
        # If not found in normalized map, try original (for backward compatibility)
        if not provider:
            provider = provider_map.get(payment_method.lower())
            
        if not provider:
            return jsonify({
                'success': False,
                'message': f'Unsupported payment method: {payment_method}'
            }), 400
        
        # Get authentication token
        token = get_azampay_token()
        if not token:
            logger.error("Failed to authenticate with AzamPay")
            return jsonify({
                'success': False,
                'message': 'Failed to authenticate with AzamPay'
            }), 400
        
        # Format phone number (remove leading zero if present)
        if phone.startswith("0"):
            phone = "255" + phone[1:]
        elif not phone.startswith("255"):
            phone = "255" + phone
        
        # Generate unique transaction ID
        transaction_id = f"PONA-{int(time.time())}"
        
        # Prepare payment request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        payload = {
            "accountNumber": phone,
            "amount": amount,
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
                
                # Save payment record to database (simplified for minimal app)
                payment_record = {
                    'payment_id': payment_id,
                    'transaction_id': transaction_id,
                    'name': name,
                    'phone': phone,
                    'amount': amount,
                    'payment_method': payment_method,
                    'provider': provider,
                    'status': 'pending',
                    'created_at': now
                }
                
                logger.info(f"Payment record created: {payment_record}")
                
                return jsonify({
                    'success': True,
                    'message': 'Payment request sent successfully',
                    'transaction_id': transaction_id,
                    'payment_id': payment_id
                })
            else:
                logger.error(f"Payment request failed. Status: {response.status_code}, Response: {response.text}")
                return jsonify({
                    'success': False,
                    'message': f"Payment failed: {response.text}"
                }), 400
        except Exception as e:
            logger.exception(f"Error processing payment: {str(e)}")
            return jsonify({
                'success': False,
                'message': f"Payment failed: {str(e)}"
            }), 500
    except Exception as e:
        logger.exception(f"Error in checkout: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/payments/azampay/callback', methods=['POST'])
def azampay_callback():
    try:
        data = request.json
        logger.info(f"Received AzamPay callback: {data}")
        
        # Extract relevant information
        transaction_id = data.get('externalId', '')
        status = data.get('status', '')
        message = data.get('message', '')
        
        # Process based on status
        if status.upper() == 'SUCCESS':
            # Update payment status (simplified for minimal app)
            logger.info(f"Payment successful for transaction {transaction_id}")
            return jsonify({
                'success': True,
                'message': 'Callback processed successfully'
            })
        else:
            logger.warning(f"Payment not successful for transaction {transaction_id}: {message}")
            return jsonify({
                'success': False,
                'message': f'Payment failed: {message}'
            })
    except Exception as e:
        logger.exception(f"Error processing callback: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
