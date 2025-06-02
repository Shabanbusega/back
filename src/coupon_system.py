"""
Coupon System Module for Pona Health

This module handles coupon code generation, validation, and tracking
for subscription packages.
"""

import uuid
import random
import string
from datetime import datetime, timedelta
from flask import jsonify, request

# In-memory storage for coupons (would be replaced with database in production)
coupons_db = []

def generate_coupon_code():
    """
    Generate a unique 8-character alphanumeric coupon code.
    
    Returns:
        str: Generated coupon code
    """
    # Use uppercase letters and digits, excluding confusing characters like O, 0, I, 1
    characters = ''.join(c for c in string.ascii_uppercase + string.digits 
                        if c not in 'O0I1')
    
    # Generate an 8-character code
    code = ''.join(random.choice(characters) for _ in range(8))
    
    # Check if code already exists and regenerate if needed
    while any(coupon['code'] == code for coupon in coupons_db):
        code = ''.join(random.choice(characters) for _ in range(8))
    
    return code

def save_coupon(coupon_code, phone_number, package_type, call_limit, doctor_type):
    """
    Save a new coupon code with subscription details.
    
    Args:
        coupon_code: Generated coupon code
        phone_number: User's phone number
        package_type: Type of subscription package
        call_limit: Number of calls allowed with this coupon
        doctor_type: Type of doctor (specialist or general)
        
    Returns:
        dict: Saved coupon data
    """
    # Calculate expiry date (30 days from now)
    expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    coupon_data = {
        'id': str(uuid.uuid4()),
        'code': coupon_code,
        'phone_number': phone_number,
        'package_type': package_type,
        'doctor_type': doctor_type,
        'call_limit': call_limit,
        'calls_used': 0,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': expiry_date,
        'is_active': True
    }
    
    # Save to in-memory database (would be a real database in production)
    coupons_db.append(coupon_data)
    
    # Also save to Google Sheets for persistence
    from src.main import append_to_sheet
    
    sheet_data = {
        'name': 'Coupon',
        'phone_number': phone_number,
        'payment_method': 'Subscription',
        'amount': '0',  # Already paid for subscription
        'package_type': package_type,
        'doctor_type': doctor_type,
        'is_emergency': False,
        'country': 'Tanzania',
        'coupon_code': coupon_code,
        'call_limit': call_limit,
        'calls_used': 0,
        'expires_at': expiry_date,
        'status': 'Active'
    }
    
    append_success, append_message = append_to_sheet(sheet_data)
    
    return coupon_data

def validate_coupon(coupon_code, phone_number=None):
    """
    Validate a coupon code and check if it can be used.
    
    Args:
        coupon_code: Coupon code to validate
        phone_number: Optional phone number to verify ownership
        
    Returns:
        tuple: (is_valid, message, coupon_data)
    """
    # Find coupon in database
    coupon = next((c for c in coupons_db if c['code'] == coupon_code), None)
    
    # If coupon not found in memory, check Google Sheets
    if not coupon:
        from src.main import get_sheet_data
        success, message, data = get_sheet_data()
        
        if success and data:
            sheet_coupon = next((item for item in data if item.get('coupon_code') == coupon_code), None)
            
            if sheet_coupon:
                # Convert to our coupon format
                coupon = {
                    'id': str(uuid.uuid4()),
                    'code': coupon_code,
                    'phone_number': sheet_coupon.get('phone_number'),
                    'package_type': sheet_coupon.get('package_type'),
                    'doctor_type': sheet_coupon.get('doctor_type'),
                    'call_limit': int(sheet_coupon.get('call_limit', 0)),
                    'calls_used': int(sheet_coupon.get('calls_used', 0)),
                    'created_at': sheet_coupon.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'expires_at': sheet_coupon.get('expires_at'),
                    'is_active': sheet_coupon.get('status') == 'Active'
                }
                
                # Add to in-memory database
                coupons_db.append(coupon)
    
    if not coupon:
        return False, "Invalid coupon code", None
    
    # Check if coupon is active
    if not coupon['is_active']:
        return False, "Coupon is inactive", coupon
    
    # Check if coupon has expired
    expiry_date = datetime.strptime(coupon['expires_at'], '%Y-%m-%d')
    if datetime.now() > expiry_date:
        return False, "Coupon has expired", coupon
    
    # Check if all calls have been used
    if coupon['calls_used'] >= coupon['call_limit']:
        return False, "All calls for this coupon have been used", coupon
    
    # If phone number is provided, check if it matches
    if phone_number and coupon['phone_number'] != phone_number:
        return False, "Coupon does not belong to this phone number", coupon
    
    return True, "Coupon is valid", coupon

def use_coupon(coupon_code):
    """
    Mark a coupon as used (increment calls_used).
    
    Args:
        coupon_code: Coupon code to use
        
    Returns:
        tuple: (success, message, updated_coupon)
    """
    # Validate coupon first
    is_valid, message, coupon = validate_coupon(coupon_code)
    
    if not is_valid:
        return False, message, coupon
    
    # Increment calls used
    coupon['calls_used'] += 1
    
    # Check if all calls have been used
    if coupon['calls_used'] >= coupon['call_limit']:
        coupon['is_active'] = False
    
    # Update Google Sheets
    from src.main import get_sheet_data, update_sheet_row
    success, message, data = get_sheet_data()
    
    if success and data:
        for i, row in enumerate(data):
            if row.get('coupon_code') == coupon_code:
                # Update calls_used and status
                row_index = row.get('row_index')
                update_data = {
                    'calls_used': coupon['calls_used'],
                    'status': 'Active' if coupon['is_active'] else 'Inactive'
                }
                update_success, update_message = update_sheet_row(row_index, update_data)
                break
    
    return True, "Coupon used successfully", coupon

def get_user_coupons(phone_number):
    """
    Get all coupons for a specific user.
    
    Args:
        phone_number: User's phone number
        
    Returns:
        list: List of coupon data for the user
    """
    # Check in-memory database
    user_coupons = [c for c in coupons_db if c['phone_number'] == phone_number]
    
    # Also check Google Sheets
    from src.main import get_sheet_data
    success, message, data = get_sheet_data()
    
    if success and data:
        for item in data:
            if (item.get('phone_number') == phone_number and 
                item.get('coupon_code') and 
                not any(c['code'] == item.get('coupon_code') for c in user_coupons)):
                
                # Convert to our coupon format
                coupon = {
                    'id': str(uuid.uuid4()),
                    'code': item.get('coupon_code'),
                    'phone_number': phone_number,
                    'package_type': item.get('package_type'),
                    'doctor_type': item.get('doctor_type'),
                    'call_limit': int(item.get('call_limit', 0)),
                    'calls_used': int(item.get('calls_used', 0)),
                    'created_at': item.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'expires_at': item.get('expires_at'),
                    'is_active': item.get('status') == 'Active'
                }
                
                # Add to in-memory database and result
                coupons_db.append(coupon)
                user_coupons.append(coupon)
    
    return user_coupons

# Flask route handlers
def register_coupon_routes(app):
    """
    Register coupon-related routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    @app.route('/api/coupons/validate', methods=['POST'])
    def validate_coupon_endpoint():
        """Validate a coupon code."""
        try:
            data = request.json
            coupon_code = data.get('coupon_code')
            phone_number = data.get('phone_number')
            
            if not coupon_code:
                return jsonify({
                    'success': False,
                    'message': 'Coupon code is required'
                }), 400
            
            is_valid, message, coupon = validate_coupon(coupon_code, phone_number)
            
            if is_valid:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': {
                        'coupon_code': coupon['code'],
                        'package_type': coupon['package_type'],
                        'doctor_type': coupon['doctor_type'],
                        'call_limit': coupon['call_limit'],
                        'calls_used': coupon['calls_used'],
                        'calls_remaining': coupon['call_limit'] - coupon['calls_used'],
                        'expires_at': coupon['expires_at']
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error validating coupon: {str(e)}'
            }), 500
    
    @app.route('/api/coupons/use', methods=['POST'])
    def use_coupon_endpoint():
        """Use a coupon code for booking."""
        try:
            data = request.json
            coupon_code = data.get('coupon_code')
            
            if not coupon_code:
                return jsonify({
                    'success': False,
                    'message': 'Coupon code is required'
                }), 400
            
            success, message, coupon = use_coupon(coupon_code)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': message,
                    'data': {
                        'coupon_code': coupon['code'],
                        'calls_used': coupon['calls_used'],
                        'calls_remaining': coupon['call_limit'] - coupon['calls_used'],
                        'is_active': coupon['is_active']
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error using coupon: {str(e)}'
            }), 500
    
    @app.route('/api/coupons/user/<phone_number>', methods=['GET'])
    def get_user_coupons_endpoint(phone_number):
        """Get all coupons for a user."""
        try:
            coupons = get_user_coupons(phone_number)
            
            # Format for response
            formatted_coupons = [{
                'coupon_code': c['code'],
                'package_type': c['package_type'],
                'doctor_type': c['doctor_type'],
                'call_limit': c['call_limit'],
                'calls_used': c['calls_used'],
                'calls_remaining': c['call_limit'] - c['calls_used'],
                'expires_at': c['expires_at'],
                'is_active': c['is_active']
            } for c in coupons]
            
            return jsonify({
                'success': True,
                'message': f'Found {len(coupons)} coupons',
                'data': formatted_coupons
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error getting user coupons: {str(e)}'
            }), 500
