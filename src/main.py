"""
Main application file for Pona Health backend
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
import json
import requests
import os
from datetime import datetime
from .azampay_integration import process_payment
from .admin_routes import admin_bp

app = Flask(__name__, static_folder='static')
CORS(app)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
SHEET_ID = "1N38MVn9tIjtyvOhMcsHCoD5bELE5vmHmau7ZgDtSz1g"

try:
    credentials = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SHEET_ID)
    
    # Get or create worksheets
    try:
        bookings_sheet = spreadsheet.worksheet("bookings")
    except gspread.exceptions.WorksheetNotFound:
        bookings_sheet = spreadsheet.add_worksheet(title="bookings", rows=1000, cols=20)
        bookings_sheet.append_row(["id", "name", "phone", "doctor_type", "emergency", "country", "timestamp"])
    
    try:
        payments_sheet = spreadsheet.worksheet("payments")
    except gspread.exceptions.WorksheetNotFound:
        payments_sheet = spreadsheet.add_worksheet(title="payments", rows=1000, cols=20)
        payments_sheet.append_row(["id", "name", "phone", "payment_method", "amount", "package_type", "doctor_type", "emergency", "country", "timestamp"])
    
    try:
        subscriptions_sheet = spreadsheet.worksheet("subscriptions")
    except gspread.exceptions.WorksheetNotFound:
        subscriptions_sheet = spreadsheet.add_worksheet(title="subscriptions", rows=1000, cols=20)
        subscriptions_sheet.append_row(["id", "name", "phone", "package", "amount", "payment_method", "coupon", "start_date", "expiry_date", "timestamp"])
    
    print("Google Sheets connection established successfully")
except Exception as e:
    print(f"Error connecting to Google Sheets: {e}")
    bookings_sheet = None
    payments_sheet = None
    subscriptions_sheet = None

# Register blueprints
app.register_blueprint(admin_bp)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/env-check', methods=['GET'])
def env_check():
    """Environment variables check endpoint"""
    env_vars = {
        "AZAMPAY_CLIENT_ID": os.environ.get("AZAMPAY_CLIENT_ID", "Not set"),
        "AZAMPAY_SECRET_KEY": "***" if os.environ.get("AZAMPAY_SECRET_KEY") else "Not set",
        "AZAMPAY_BASE_URL": os.environ.get("AZAMPAY_BASE_URL", "Not set"),
        "CALLBACK_URL": os.environ.get("CALLBACK_URL", "Not set")
    }
    return jsonify(env_vars)

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    try:
        data = request.json
        
        # Generate booking ID
        booking_id = f"BK-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get current timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store booking in Google Sheets
        if bookings_sheet:
            bookings_sheet.append_row([
                booking_id,
                data.get('name', 'Unknown'),
                data.get('phone', 'Unknown'),
                data.get('doctor_type', 'Unknown'),
                data.get('emergency', False),
                data.get('country', 'Unknown'),
                now
            ])
        
        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "message": "Booking created successfully"
        })
    except Exception as e:
        print(f"Error creating booking: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/payments', methods=['POST'])
def create_payment():
    """Create a new payment"""
    try:
        data = request.json
        
        # Generate payment ID
        payment_id = f"PY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get current timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store payment info in Google Sheets
        if payments_sheet:
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
        
        return jsonify({
            "success": True,
            "payment_id": payment_id,
            "message": "Payment created successfully"
        })
    except Exception as e:
        print(f"Error creating payment: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/payments/azampay/checkout', methods=['POST'])
def azampay_checkout():
    """Process AzamPay checkout"""
    try:
        data = request.json
        print(f"Received payment request: {data}")
        
        # Format amount if it contains commas
        amount_str = data.get('amount', '0')
        if isinstance(amount_str, str):
            amount_str = amount_str.replace(',', '')
        amount = float(amount_str)
        
        # Process payment through AzamPay
        payment_result = process_payment(
            phone=data.get('phone', ''),
            amount=amount,
            provider=data.get('payment_method', 'Airtel'),
            currency=data.get('currency', 'TZS')
        )
        
        if payment_result.get('success'):
            # Generate payment ID
            payment_id = f"PY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Get current timestamp
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Store payment info in Google Sheets
            if payments_sheet:
                payments_sheet.append_row([
                    payment_id,
                    data.get('name', 'Unknown'),
                    data.get('phone', 'Unknown'),
                    data.get('payment_method', 'Unknown'),
                    amount,
                    data.get('package_type', 'Unknown'),
                    data.get('doctor_type', 'Unknown'),
                    data.get('emergency', False),
                    data.get('country', 'Unknown'),
                    now
                ])
            
            # If it's a subscription, store in subscriptions sheet
            if data.get('package_type', '').lower() == 'subscription':
                package = data.get('package', {})
                
                # Calculate expiry date (30 days from now)
                start_date = datetime.now().strftime("%Y-%m-%d")
                expiry_date = datetime.now().replace(
                    day=min(datetime.now().day + 30, 28)  # Simple approximation
                ).strftime("%Y-%m-%d")
                
                if subscriptions_sheet:
                    subscriptions_sheet.append_row([
                        payment_id,
                        data.get('name', 'Unknown'),
                        data.get('phone', 'Unknown'),
                        package.get('name', 'Unknown'),
                        amount,
                        data.get('payment_method', 'Unknown'),
                        data.get('coupon', ''),
                        start_date,
                        expiry_date,
                        now
                    ])
            
            return jsonify({
                "success": True,
                "payment_id": payment_id,
                "message": "Payment processed successfully",
                "azampay_reference": payment_result.get('reference', '')
            })
        else:
            return jsonify({
                "success": False,
                "error": payment_result.get('error', 'Payment processing failed')
            }), 400
    except Exception as e:
        print(f"Error processing AzamPay checkout: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/payments/azampay/callback', methods=['POST'])
def azampay_callback():
    """Handle AzamPay callback"""
    try:
        data = request.json
        print(f"Received AzamPay callback: {data}")
        
        # In a production environment, you would update the payment status
        # based on the callback data
        
        return jsonify({
            "success": True,
            "message": "Callback received"
        })
    except Exception as e:
        print(f"Error handling AzamPay callback: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/subscriptions', methods=['POST'])
def create_subscription():
    """Create a new subscription"""
    try:
        data = request.json
        
        # Generate subscription ID
        subscription_id = f"SUB-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get current timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate dates
        start_date = datetime.now().strftime("%Y-%m-%d")
        expiry_date = datetime.now().replace(
            day=min(datetime.now().day + 30, 28)  # Simple approximation
        ).strftime("%Y-%m-%d")
        
        # Store subscription in Google Sheets
        if subscriptions_sheet:
            subscriptions_sheet.append_row([
                subscription_id,
                data.get('name', 'Unknown'),
                data.get('phone', 'Unknown'),
                data.get('package', 'Unknown'),
                data.get('amount', 0),
                data.get('payment_method', 'Unknown'),
                data.get('coupon', ''),
                start_date,
                expiry_date,
                now
            ])
        
        return jsonify({
            "success": True,
            "subscription_id": subscription_id,
            "message": "Subscription created successfully"
        })
    except Exception as e:
        print(f"Error creating subscription: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    """Serve admin dashboard"""
    return send_from_directory('static/admin', 'dashboard.html')

@app.route('/admin/<path:path>', methods=['GET'])
def admin_static(path):
    """Serve admin static files"""
    return send_from_directory('static/admin', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
