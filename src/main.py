import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS
import json
import uuid
import datetime
import gspread
from google.oauth2 import service_account
import random
import string
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["https://ponahealth.com", "https://uedrcgjn.manus.space", "http://localhost:5173", "http://localhost:3000"])
app.secret_key = 'pona_health_secret_key_2025'

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = '/home/ubuntu/upload/pona-health-data-1f299f0b4198.json'
SPREADSHEET_ID = '1N38MVn9tIjtyvOhMcsHCoD5bELE5vmHmau7ZgDtSz1g'

try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    
    # Ensure all required worksheets exist
    worksheet_names = [ws.title for ws in spreadsheet.worksheets()]
    
    if 'payments_info' not in worksheet_names:
        payments_sheet = spreadsheet.add_worksheet(title='payments_info', rows=1000, cols=10)
        payments_sheet.append_row([
            'ID', 'Name', 'Phone', 'Payment Method', 'Amount', 
            'Package Type', 'Doctor Type', 'Emergency', 'Country', 'Timestamp'
        ])
    else:
        payments_sheet = spreadsheet.worksheet('payments_info')
    
    if 'subscriptions' not in worksheet_names:
        subscriptions_sheet = spreadsheet.add_worksheet(title='subscriptions', rows=1000, cols=15)
        subscriptions_sheet.append_row([
            'ID', 'Name', 'Phone', 'Package', 'Doctor Type', 'Country',
            'Start Date', 'End Date', 'Calls Total', 'Calls Used',
            'Coupon Code', 'Status', 'Payment Method', 'Amount', 'Timestamp'
        ])
    else:
        subscriptions_sheet = spreadsheet.worksheet('subscriptions')
    
    if 'coupons' not in worksheet_names:
        coupons_sheet = spreadsheet.add_worksheet(title='coupons', rows=1000, cols=12)
        coupons_sheet.append_row([
            'ID', 'Coupon Code', 'Owner', 'Phone', 'Package',
            'Doctor Type', 'Calls Total', 'Calls Used',
            'Created', 'Expires', 'Status', 'Last Used'
        ])
    else:
        coupons_sheet = spreadsheet.worksheet('coupons')
    
    if 'bookings' not in worksheet_names:
        bookings_sheet = spreadsheet.add_worksheet(title='bookings', rows=1000, cols=12)
        bookings_sheet.append_row([
            'ID', 'Name', 'Phone', 'Doctor', 'Doctor Type',
            'Date', 'Time', 'Type', 'Status',
            'Coupon Used', 'Payment ID', 'Timestamp'
        ])
    else:
        bookings_sheet = spreadsheet.worksheet('bookings')
        
    if 'users' not in worksheet_names:
        users_sheet = spreadsheet.add_worksheet(title='users', rows=1000, cols=10)
        users_sheet.append_row([
            'ID', 'Name', 'Phone', 'Email', 'Country',
            'Joined', 'Status', 'Last Login', 'Bookings Count', 'Subscriptions Count'
        ])
    else:
        users_sheet = spreadsheet.worksheet('users')
        
    logger.info("Google Sheets setup completed successfully")
except Exception as e:
    logger.error(f"Error setting up Google Sheets: {str(e)}")
    # Continue without Google Sheets if there's an error

# AzamPay configuration - Updated with real credentials
AZAMPAY_API_URL = "https://sandbox.azampay.co.tz"  # Change to production URL when ready
AZAMPAY_CLIENT_ID = "84729511-6899-4e29-9d6d-3cca444a8c2c"  # User's actual client ID
AZAMPAY_CLIENT_SECRET = "J1gxAW4i0lO1tv07/g+KHrOuSeBRJTbOj9KN/Fuw5aCdMLKWzWgRBAMhPFkyVHZcCHb7NsfUG50NkFOeeFRIE6b4il+JCb40+Syg5ZR3GZyWQlHzzUoAvIXC8aK2Y487AmAI3DtVkP3Qf2gUKoWkeRP370thg4/mfN/EKAysuB8M0El7U91X0B3RpYEQBWwvCsjgpBOa7YiRdFcBhdlfkv9dkK1+BISHxkFdfzSO7EvMIuwSS7hycVwQpJUqNYNmFi+lgrVDvYmChMWzqk+cULQpR8YNylgycCw/HnJujL2TplqYMxNkIf+MVoLVS44f5R3emdJH/WjOpj09UaUr5DVCgyDZ+B+MnNhVkmVt0QhcYTcgODABmXkB42+RxiVBj8CWjmHg6QoMld36F4PQraeWFPRFxWSFK2n/hFQxBqPdndGp28Kv5s/2qtsHbQlXWI9yBCgW6BR9joOhpPnSHfo1vgQ2bxI8SH/rmKJx3NE++GKgNCeJHqjLXVWlHCAWd1OBugrpx1p15yS7TReD4Eg3pGLmMMFVvyP4dd0Hu809u3NBAMM6TPRUiFJWuptlHcC161Y82bIETW+n123yeOJMwrRay7YLtjJ5CTUMnzvgd/G28ZcxEXuin5d/Ryu23uXhmpblrRHLtPaBX6S/Ix6INgRhHar4dAxz8nwAFKc="  # User's actual secret key
AZAMPAY_CALLBACK_URL = "https://ponahealth.com/api/payments/azampay/callback"  # Updated to permanent domain

# Function to get AzamPay access token
def get_azampay_token():
    try:
        url = f"{AZAMPAY_API_URL}/azampay/api/v1/auth/token"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "appName": "Pona Health",
            "clientId": AZAMPAY_CLIENT_ID,
            "clientSecret": AZAMPAY_CLIENT_SECRET
        }
        
        logger.info(f"Requesting AzamPay token with client ID: {AZAMPAY_CLIENT_ID}")
        response = requests.post(url, headers=headers, json=payload)
        logger.info(f"AzamPay token response status: {response.status_code}")
        
        response_data = response.json()
        logger.debug(f"AzamPay token response: {response_data}")
        
        if response.status_code == 200 and "data" in response_data:
            logger.info("Successfully obtained AzamPay token")
            return response_data["data"]["accessToken"]
        else:
            logger.error(f"Failed to get AzamPay token: {response_data}")
            return None
    except Exception as e:
        logger.error(f"Error getting AzamPay token: {str(e)}")
        return None

# Function to process mobile money payment via AzamPay
def process_azampay_mno_payment(phone, amount, currency, provider, external_id):
    try:
        token = get_azampay_token()
        if not token:
            logger.error("Failed to authenticate with AzamPay")
            return {"success": False, "message": "Failed to authenticate with AzamPay"}
        
        url = f"{AZAMPAY_API_URL}/azampay/mno/checkout"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        # Format phone number to remove any non-numeric characters
        phone = ''.join(filter(str.isdigit, phone))
        
        # Ensure phone number starts with country code (255 for Tanzania)
        if not phone.startswith('255') and phone.startswith('0'):
            phone = '255' + phone[1:]
        elif not phone.startswith('255'):
            phone = '255' + phone
        
        # Map payment method to AzamPay provider format
        provider_map = {
            'm-pesa': 'Mpesa',
            'tigo-pesa': 'Tigo',
            'airtel-money': 'Airtel',
            'halo-pesa': 'Halopesa',
            'Airtel': 'Airtel',
            'Tigo': 'Tigo',
            'Mpesa': 'Mpesa',
            'Halopesa': 'Halopesa'
        }
        
        provider = provider_map.get(provider, provider)
        
        payload = {
            "accountNumber": phone,
            "amount": float(amount),
            "currency": currency,
            "externalId": external_id,
            "provider": provider,
            "additionalProperties": {
                "property1": None,
                "property2": None
            },
            "callbackUrl": AZAMPAY_CALLBACK_URL
        }
        
        logger.info(f"AzamPay MNO checkout request: {payload}")
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        logger.info(f"AzamPay MNO checkout response: {response_data}")
        
        if response.status_code in [200, 201, 202]:
            return {"success": True, "data": response_data, "reference_id": external_id}
        else:
            error_msg = response_data.get("message", "Payment processing failed")
            logger.error(f"AzamPay payment failed: {error_msg}")
            return {"success": False, "message": error_msg}
    except Exception as e:
        logger.error(f"Error processing AzamPay MNO payment: {str(e)}")
        return {"success": False, "message": f"Payment processing error: {str(e)}"}

# Function to generate a random coupon code
def generate_coupon_code():
    characters = string.ascii_uppercase + string.digits
    # Exclude similar looking characters
    characters = characters.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(random.choice(characters) for _ in range(8))

# Routes for the API
@app.route('/api/payments', methods=['POST'])
def process_payment():
    try:
        data = request.json
        logger.info(f"Payment request received: {data}")
        
        payment_id = str(uuid.uuid4())
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Process payment based on method
        payment_method = data.get('payment_method', '').lower()
        
        if payment_method in ['m-pesa', 'tigo-pesa', 'airtel-money', 'halo-pesa']:
            # Map payment method to AzamPay provider
            provider_map = {
                'm-pesa': 'Mpesa',
                'tigo-pesa': 'Tigo',
                'airtel-money': 'Airtel',
                'halo-pesa': 'Halopesa'
            }
            
            provider = provider_map.get(payment_method)
            if not provider:
                return jsonify({
                    'success': False,
                    'message': f'Unsupported payment method: {payment_method}'
                }), 400
            
            # Process mobile money payment via AzamPay
            result = process_azampay_mno_payment(
                phone=data.get('phone'),
                amount=float(data.get('amount', 0)),
                currency='TZS',
                provider=provider,
                external_id=payment_id
            )
            
            if not result['success']:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400
        
        # Store payment info in Google Sheets
        try:
            payments_sheet.append_row([
                payment_id,
                data.get('name', 'Unknown'),
                data.get('phone', 'Unknown'),
                data.get('payment_method', 'Unknown'),
                data.get('amount', 0),
                data.get('package_type', 'Unknown'),
                data.get('doctor_type', 'Unknown'),
                data.get('emergency', False),
                data.get('country', 'Unknown'),
                now
            ])
            
            # If this is a subscription payment, generate a coupon code
            if data.get('package_type') in ['family_doctor_plan', 'pregnancy_care', 'hypertension_care']:
                coupon_code = generate_coupon_code()
                
                # Store subscription info
                subscriptions_sheet.append_row([
                    str(uuid.uuid4()),
                    data.get('name', 'Unknown'),
                    data.get('phone', 'Unknown'),
                    data.get('package_type', 'Unknown'),
                    data.get('doctor_type', 'general'),
                    data.get('country', 'Unknown'),
                    now.split()[0],  # Start date
                    (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),  # End date
                    15,  # Default calls total
                    0,   # Calls used
                    coupon_code,
                    'active',
                    data.get('payment_method', 'Unknown'),
                    data.get('amount', 0),
                    now
                ])
                
                # Store coupon info
                coupons_sheet.append_row([
                    str(uuid.uuid4()),
                    coupon_code,
                    data.get('name', 'Unknown'),
                    data.get('phone', 'Unknown'),
                    data.get('package_type', 'Unknown'),
                    data.get('doctor_type', 'general'),
                    15,  # Default calls total
                    0,   # Calls used
                    now.split()[0],  # Created date
                    (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),  # Expiry date
                    'active',
                    ''   # Last used
                ])
                
                return jsonify({
                    'success': True,
                    'payment_id': payment_id,
                    'coupon_code': coupon_code,
                    'message': 'Payment processed and coupon generated'
                })
            
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'message': 'Payment processed successfully'
            })
            
        except Exception as e:
            logger.error(f"Error storing payment in Google Sheets: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Payment recorded but could not be stored in database'
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/payments/azampay/checkout', methods=['POST'])
def azampay_checkout():
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
        
        # Process mobile money payment via AzamPay
        result = process_azampay_mno_payment(
            phone=phone,
            amount=amount,
            currency='TZS',
            provider=provider,
            external_id=payment_id
        )
        
        if not result['success']:
            logger.error(f"Payment failed: {result['message']}")
            return jsonify({
                'success': False,
                'message': result['message']
            }), 400
        
        # Store payment info in Google Sheets
        try:
            payments_sheet.append_row([
                payment_id,
                name,
                phone,
                payment_method,
                amount,
                package_type,
                doctor_type,
                is_emergency,
                country,
                now
            ])
            
            logger.info(f"Payment data stored in Google Sheets: {payment_id}")
            
            # Return success response with reference ID
            return jsonify({
                'success': True,
                'reference_id': payment_id,
                'message': 'Payment initiated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error storing payment in Google Sheets: {str(e)}")
            # Still return success since payment was processed
            return jsonify({
                'success': True,
                'reference_id': payment_id,
                'message': 'Payment initiated but data storage failed'
            })
            
    except Exception as e:
        logger.error(f"Error processing AzamPay checkout: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Payment processing error: {str(e)}'
        }), 500
        
        # Store payment info in Google Sheets
        try:
            payments_sheet.append_row([
                payment_id,
                data.get('name', 'Unknown'),
                data.get('phone', 'Unknown'),
                data.get('payment_method', 'Unknown'),
                data.get('amount', 0),
                data.get('package_type', 'Unknown'),
                data.get('doctor_type', 'Unknown'),
                data.get('emergency', False),
                data.get('country', 'Unknown'),
                now
            ])
            
            # If this is a subscription payment, generate a coupon code
            if data.get('package_type') in ['family_doctor_plan', 'pregnancy_care', 'hypertension_care']:
                coupon_code = generate_coupon_code()
                
                # Store subscription info
                subscriptions_sheet.append_row([
                    str(uuid.uuid4()),
                    data.get('name', 'Unknown'),
                    data.get('phone', 'Unknown'),
                    data.get('package_type', 'Unknown'),
                    data.get('doctor_type', 'general'),
                    data.get('country', 'Unknown'),
                    now.split()[0],  # Start date
                    (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),  # End date
                    15,  # Default calls total
                    0,   # Calls used
                    coupon_code,
                    'active',
                    data.get('payment_method', 'Unknown'),
                    data.get('amount', 0),
                    now
                ])
                
                # Store coupon info
                coupons_sheet.append_row([
                    str(uuid.uuid4()),
                    coupon_code,
                    data.get('name', 'Unknown'),
                    data.get('phone', 'Unknown'),
                    data.get('package_type', 'Unknown'),
                    data.get('doctor_type', 'general'),
                    15,  # Default calls total
                    0,   # Calls used
                    now.split()[0],  # Created date
                    (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),  # Expiry date
                    'active',
                    ''   # Last used
                ])
                
                return jsonify({
                    'success': True,
                    'payment_id': payment_id,
                    'coupon_code': coupon_code,
                    'message': 'Payment processed and coupon generated'
                })
            
            return jsonify({
                'success': True,
                'payment_id': payment_id,
                'message': 'Payment processed successfully'
            })
            
        except Exception as e:
            logger.error(f"Error storing payment in Google Sheets: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Payment recorded but could not be stored in database'
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/payments/azampay/callback', methods=['POST'])
def azampay_callback():
    try:
        data = request.json
        logger.info(f"AzamPay callback received: {data}")
        
        # Process the callback data
        # Extract transaction details
        external_id = data.get('externalId')
        transaction_status = data.get('transactionStatus')
        message = data.get('message')
        
        # Update payment status in Google Sheets
        try:
            payments = payments_sheet.get_all_records()
            payment_index = next((i for i, p in enumerate(payments) if p['ID'] == external_id), None)
            
            if payment_index is not None:
                # Add 2 to account for header row and 0-indexing
                row_number = payment_index + 2
                
                # Add a status column if it doesn't exist
                headers = payments_sheet.row_values(1)
                if 'Status' not in headers:
                    payments_sheet.update_cell(1, len(headers) + 1, 'Status')
                    payments_sheet.update_cell(1, len(headers) + 2, 'Status Message')
                
                status_col = headers.index('Status') + 1 if 'Status' in headers else len(headers) + 1
                message_col = headers.index('Status Message') + 1 if 'Status Message' in headers else len(headers) + 2
                
                payments_sheet.update_cell(row_number, status_col, transaction_status)
                payments_sheet.update_cell(row_number, message_col, message)
        except Exception as e:
            logger.error(f"Error updating payment status in Google Sheets: {str(e)}")
        
        return jsonify({
            'success': True,
            'message': 'Callback processed successfully'
        })
    except Exception as e:
        logger.error(f"Error processing AzamPay callback: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/coupons/validate', methods=['POST'])
def validate_coupon():
    try:
        data = request.json
        coupon_code = data.get('coupon_code')
        phone_number = data.get('phone_number')
        
        if not coupon_code:
            return jsonify({
                'success': False,
                'message': 'Coupon code is required'
            }), 400
        
        # Find the coupon in Google Sheets
        try:
            coupons = coupons_sheet.get_all_records()
            coupon = next((c for c in coupons if c['Coupon Code'] == coupon_code), None)
            
            if not coupon:
                return jsonify({
                    'success': False,
                    'message': 'Invalid coupon code'
                }), 404
            
            # Check if coupon is active
            if coupon['Status'] != 'active':
                return jsonify({
                    'success': False,
                    'message': 'Coupon has expired'
                }), 400
            
            # Check if all calls have been used
            if coupon['Calls Used'] >= coupon['Calls Total']:
                return jsonify({
                    'success': False,
                    'message': 'All calls for this coupon have been used'
                }), 400
            
            # Check if phone number matches (if provided)
            if phone_number and coupon['Phone'] != phone_number:
                # Allow for different formats of phone numbers
                normalized_coupon_phone = ''.join(filter(str.isdigit, coupon['Phone']))
                normalized_user_phone = ''.join(filter(str.isdigit, phone_number))
                
                if normalized_coupon_phone != normalized_user_phone:
                    return jsonify({
                        'success': False,
                        'message': 'This coupon belongs to another user'
                    }), 400
            
            return jsonify({
                'success': True,
                'data': {
                    'coupon_code': coupon['Coupon Code'],
                    'package': coupon['Package'],
                    'doctor_type': coupon['Doctor Type'],
                    'calls_used': coupon['Calls Used'],
                    'calls_total': coupon['Calls Total'],
                    'expires': coupon['Expires']
                }
            })
            
        except Exception as e:
            logger.error(f"Error validating coupon in Google Sheets: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Error validating coupon'
            }), 500
            
    except Exception as e:
        logger.error(f"Error validating coupon: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Admin API endpoints for dashboard
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    try:
        # Get total bookings
        bookings = bookings_sheet.get_all_records()
        total_bookings = len(bookings)
        
        # Get emergency bookings
        emergency_bookings = len([b for b in bookings if b.get('Type') == 'Emergency'])
        
        # Get total revenue
        payments = payments_sheet.get_all_records()
        total_revenue = sum(float(p.get('Amount', 0)) for p in payments)
        
        # Get active subscriptions
        subscriptions = subscriptions_sheet.get_all_records()
        active_subscriptions = len([s for s in subscriptions if s.get('Status') == 'active'])
        
        return jsonify({
            'success': True,
            'data': {
                'total_bookings': total_bookings,
                'emergency_bookings': emergency_bookings,
                'total_revenue': total_revenue,
                'active_subscriptions': active_subscriptions
            }
        })
    except Exception as e:
        logger.error(f"Error getting admin stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/activity', methods=['GET'])
def get_admin_activity():
    try:
        # Combine recent activity from different sources
        activity = []
        
        # Get recent bookings
        bookings = bookings_sheet.get_all_records()
        for booking in sorted(bookings, key=lambda b: b.get('Timestamp', ''), reverse=True)[:5]:
            activity.append({
                'date': booking.get('Timestamp', '').split()[0] if booking.get('Timestamp') else '',
                'user': booking.get('Name', 'Unknown'),
                'activity': 'Booking Created',
                'details': f"{booking.get('Type', 'Unknown')} consultation with {booking.get('Doctor', 'Unknown')}"
            })
        
        # Get recent payments
        payments = payments_sheet.get_all_records()
        for payment in sorted(payments, key=lambda p: p.get('Timestamp', ''), reverse=True)[:5]:
            activity.append({
                'date': payment.get('Timestamp', '').split()[0] if payment.get('Timestamp') else '',
                'user': payment.get('Name', 'Unknown'),
                'activity': 'Payment Completed',
                'details': f"{payment.get('Amount', 0)} TZS for {payment.get('Package Type', 'Unknown')}"
            })
        
        # Get recent subscriptions
        subscriptions = subscriptions_sheet.get_all_records()
        for subscription in sorted(subscriptions, key=lambda s: s.get('Timestamp', ''), reverse=True)[:5]:
            activity.append({
                'date': subscription.get('Timestamp', '').split()[0] if subscription.get('Timestamp') else '',
                'user': subscription.get('Name', 'Unknown'),
                'activity': 'Subscription Activated',
                'details': f"{subscription.get('Package', 'Unknown')} package for 30 days"
            })
        
        # Sort by date (most recent first)
        activity = sorted(activity, key=lambda a: a.get('date', ''), reverse=True)[:10]
        
        return jsonify({
            'success': True,
            'data': activity
        })
    except Exception as e:
        logger.error(f"Error getting admin activity: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/bookings', methods=['GET'])
def get_admin_bookings():
    try:
        bookings = bookings_sheet.get_all_records()
        
        # Format bookings for the frontend
        formatted_bookings = []
        for booking in bookings:
            formatted_bookings.append({
                'id': booking.get('ID', ''),
                'name': booking.get('Name', 'Unknown'),
                'phone': booking.get('Phone', 'Unknown'),
                'doctor': booking.get('Doctor', 'Unknown'),
                'date': booking.get('Date', ''),
                'time': booking.get('Time', ''),
                'type': booking.get('Type', 'Unknown'),
                'status': booking.get('Status', 'Unknown')
            })
        
        return jsonify({
            'success': True,
            'data': formatted_bookings
        })
    except Exception as e:
        logger.error(f"Error getting admin bookings: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/payments', methods=['GET'])
def get_admin_payments():
    try:
        payments = payments_sheet.get_all_records()
        
        # Format payments for the frontend
        formatted_payments = []
        for payment in payments:
            formatted_payments.append({
                'id': payment.get('ID', ''),
                'name': payment.get('Name', 'Unknown'),
                'phone': payment.get('Phone', 'Unknown'),
                'method': payment.get('Payment Method', 'Unknown'),
                'amount': payment.get('Amount', 0),
                'package': payment.get('Package Type', 'Unknown'),
                'status': payment.get('Status', 'Completed'),
                'date': payment.get('Timestamp', '').split()[0] if payment.get('Timestamp') else ''
            })
        
        return jsonify({
            'success': True,
            'data': formatted_payments
        })
    except Exception as e:
        logger.error(f"Error getting admin payments: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/subscriptions', methods=['GET'])
def get_admin_subscriptions():
    try:
        subscriptions = subscriptions_sheet.get_all_records()
        
        # Format subscriptions for the frontend
        formatted_subscriptions = []
        for subscription in subscriptions:
            formatted_subscriptions.append({
                'id': subscription.get('ID', ''),
                'name': subscription.get('Name', 'Unknown'),
                'phone': subscription.get('Phone', 'Unknown'),
                'package': subscription.get('Package', 'Unknown'),
                'doctor_type': subscription.get('Doctor Type', 'Unknown'),
                'calls_used': subscription.get('Calls Used', 0),
                'calls_total': subscription.get('Calls Total', 0),
                'coupon_code': subscription.get('Coupon Code', ''),
                'status': subscription.get('Status', 'Unknown')
            })
        
        return jsonify({
            'success': True,
            'data': formatted_subscriptions
        })
    except Exception as e:
        logger.error(f"Error getting admin subscriptions: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/coupons', methods=['GET'])
def get_admin_coupons():
    try:
        coupons = coupons_sheet.get_all_records()
        
        # Format coupons for the frontend
        formatted_coupons = []
        for coupon in coupons:
            formatted_coupons.append({
                'id': coupon.get('ID', ''),
                'code': coupon.get('Coupon Code', ''),
                'owner': coupon.get('Owner', 'Unknown'),
                'phone': coupon.get('Phone', 'Unknown'),
                'package': coupon.get('Package', 'Unknown'),
                'calls_used': coupon.get('Calls Used', 0),
                'calls_total': coupon.get('Calls Total', 0),
                'created': coupon.get('Created', ''),
                'expires': coupon.get('Expires', ''),
                'status': coupon.get('Status', 'Unknown')
            })
        
        return jsonify({
            'success': True,
            'data': formatted_coupons
        })
    except Exception as e:
        logger.error(f"Error getting admin coupons: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    try:
        # Extract unique users from bookings and subscriptions
        bookings = bookings_sheet.get_all_records()
        subscriptions = subscriptions_sheet.get_all_records()
        
        # Create a dictionary to store unique users
        users_dict = {}
        
        # Add users from bookings
        for booking in bookings:
            phone = booking.get('Phone', '')
            if phone and phone not in users_dict:
                users_dict[phone] = {
                    'id': str(uuid.uuid4()),
                    'name': booking.get('Name', 'Unknown'),
                    'phone': phone,
                    'email': '',
                    'country': 'Tanzania',
                    'joined': booking.get('Timestamp', '').split()[0] if booking.get('Timestamp') else '',
                    'status': 'Active',
                    'bookings_count': 1,
                    'subscriptions_count': 0
                }
            elif phone:
                users_dict[phone]['bookings_count'] += 1
        
        # Add users from subscriptions
        for subscription in subscriptions:
            phone = subscription.get('Phone', '')
            if phone and phone not in users_dict:
                users_dict[phone] = {
                    'id': str(uuid.uuid4()),
                    'name': subscription.get('Name', 'Unknown'),
                    'phone': phone,
                    'email': '',
                    'country': subscription.get('Country', 'Tanzania'),
                    'joined': subscription.get('Timestamp', '').split()[0] if subscription.get('Timestamp') else '',
                    'status': 'Active',
                    'bookings_count': 0,
                    'subscriptions_count': 1
                }
            elif phone:
                users_dict[phone]['subscriptions_count'] += 1
        
        # Convert dictionary to list
        users = list(users_dict.values())
        
        return jsonify({
            'success': True,
            'data': users
        })
    except Exception as e:
        logger.error(f"Error getting admin users: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/admin/coupons/generate', methods=['POST'])
def generate_admin_coupon():
    try:
        data = request.json
        phone_number = data.get('phone_number')
        package_type = data.get('package_type')
        doctor_type = data.get('doctor_type')
        call_limit = int(data.get('call_limit', 15))
        
        if not phone_number or not package_type or not doctor_type:
            return jsonify({
                'success': False,
                'message': 'Missing required fields'
            }), 400
        
        # Generate a new coupon code
        coupon_code = generate_coupon_code()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store coupon info
        coupon_id = str(uuid.uuid4())
        coupons_sheet.append_row([
            coupon_id,
            coupon_code,
            'Admin Generated',  # Owner
            phone_number,
            package_type,
            doctor_type,
            call_limit,  # Calls total
            0,   # Calls used
            now.split()[0],  # Created date
            (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),  # Expiry date
            'active',
            ''   # Last used
        ])
        
        return jsonify({
            'success': True,
            'data': {
                'id': coupon_id,
                'code': coupon_code,
                'phone': phone_number,
                'package': package_type,
                'doctor_type': doctor_type,
                'calls_total': call_limit,
                'message': 'Coupon generated successfully'
            }
        })
    except Exception as e:
        logger.error(f"Error generating admin coupon: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Admin authentication
@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'admin' and password == 'pona2025':
        session['admin_authenticated'] = True
        return redirect('/admin/dashboard')
    else:
        return redirect('/admin?error=invalid_credentials')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    return redirect('/admin')

# Admin dashboard routes
@app.route('/admin')
def admin_login_page():
    return send_from_directory('static/admin', 'index.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_authenticated'):
        return redirect('/admin')
    return send_from_directory('static/admin', 'dashboard.html')

# Serve static files
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Default route
@app.route('/')
def index():
    return "Pona Health API Server"
    
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "message": "API server is running",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
