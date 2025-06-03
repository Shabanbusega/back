"""
Admin API routes for Pona Health admin dashboard
"""

from flask import Blueprint, request, jsonify
from .google_sheets_service import get_sheets_service
import json
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
sheets_service = get_sheets_service()

@admin_bp.route('/dashboard', methods=['GET'])
def get_dashboard_metrics():
    """Get dashboard metrics"""
    try:
        metrics = sheets_service.get_dashboard_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/doctors', methods=['GET'])
def get_doctors():
    """Get all doctors"""
    try:
        doctors = sheets_service.get_doctors()
        return jsonify(doctors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/doctors', methods=['POST'])
def add_doctor():
    """Add a new doctor"""
    try:
        doctor_data = request.json
        result = sheets_service.add_doctor(doctor_data)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/doctors/<doctor_id>', methods=['PUT'])
def update_doctor(doctor_id):
    """Update an existing doctor"""
    try:
        doctor_data = request.json
        doctor_data['id'] = doctor_id
        result = sheets_service.update_doctor(doctor_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/doctors/<doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    """Delete a doctor"""
    try:
        result = sheets_service.delete_doctor(doctor_id)
        if result:
            return jsonify({"success": True})
        return jsonify({"error": "Doctor not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/payments', methods=['GET'])
def get_payments():
    """Get payments with optional date filtering"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        payments = sheets_service.get_payments(start_date, end_date)
        return jsonify(payments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/payments/doctor/<doctor_id>', methods=['GET'])
def get_doctor_earnings(doctor_id):
    """Get earnings for a specific doctor"""
    try:
        earnings = sheets_service.get_doctor_earnings(doctor_id)
        return jsonify(earnings)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/subscriptions', methods=['GET'])
def get_subscriptions():
    """Get all subscriptions"""
    try:
        subscriptions = sheets_service.get_subscriptions()
        return jsonify(subscriptions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/revenue', methods=['GET'])
def get_revenue_data():
    """Get revenue data with period filtering"""
    try:
        period = request.args.get('period', 'all')
        revenue_data = sheets_service.get_revenue_data(period)
        return jsonify(revenue_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/consultation-fees', methods=['GET'])
def get_consultation_fees():
    """Get consultation fees for all countries"""
    try:
        fees = sheets_service.get_consultation_fees()
        return jsonify(fees)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/consultation-fees', methods=['PUT'])
def update_consultation_fees():
    """Update consultation fees"""
    try:
        fees_data = request.json
        result = sheets_service.update_consultation_fees(fees_data)
        if result:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to update consultation fees"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/care-plans', methods=['GET'])
def get_care_plans():
    """Get all care plans"""
    try:
        plans = sheets_service.get_care_plans()
        return jsonify(plans)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/care-plans', methods=['PUT'])
def update_care_plans():
    """Update care plans"""
    try:
        plans_data = request.json
        result = sheets_service.update_care_plans(plans_data)
        if result:
            return jsonify({"success": True})
        return jsonify({"error": "Failed to update care plans"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        users = sheets_service.get_users()
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users', methods=['POST'])
def add_user():
    """Add a new user"""
    try:
        user_data = request.json
        result = sheets_service.add_user(user_data)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update an existing user"""
    try:
        user_data = request.json
        user_data['id'] = user_id
        result = sheets_service.update_user(user_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user"""
    try:
        result = sheets_service.delete_user(user_id)
        if result:
            return jsonify({"success": True})
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change a user's password"""
    try:
        data = request.json
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        # In a real app, you would verify the current password
        # and hash the new password before storing it
        
        # For demo purposes, we'll just update the password for the first user
        users = sheets_service.get_users()
        if users:
            user_id = users[0].get('id')
            result = sheets_service.change_password(user_id, new_password)
            if result:
                return jsonify({"success": True})
        
        return jsonify({"error": "Failed to change password"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
