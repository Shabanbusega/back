"""
Google Sheets Service for Pona Health Admin Dashboard

This module provides functions to interact with Google Sheets API
for storing and retrieving data for the admin dashboard.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials

# Constants
SHEET_ID = "1N38MVn9tIjtyvOhMcsHCoD5bELE5vmHmau7ZgDtSz1g"
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")

# Scopes required for Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class GoogleSheetsService:
    """Service class for Google Sheets operations"""
    
    def __init__(self):
        """Initialize the Google Sheets service with credentials"""
        try:
            self.credentials = Credentials.from_service_account_file(
                CREDENTIALS_PATH, scopes=SCOPES
            )
            self.client = gspread.authorize(self.credentials)
            self.spreadsheet = self.client.open_by_key(SHEET_ID)
        except Exception as e:
            print(f"Error initializing Google Sheets service: {e}")
            raise
    
    def get_sheet(self, sheet_name: str):
        """Get a specific worksheet by name"""
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Create the sheet if it doesn't exist
            return self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
    
    def get_all_records(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Get all records from a specific worksheet"""
        sheet = self.get_sheet(sheet_name)
        return sheet.get_all_records()
    
    def append_row(self, sheet_name: str, row_data: List[Any]) -> None:
        """Append a row to a specific worksheet"""
        sheet = self.get_sheet(sheet_name)
        sheet.append_row(row_data)
    
    def update_row(self, sheet_name: str, row_index: int, row_data: List[Any]) -> None:
        """Update a specific row in a worksheet"""
        sheet = self.get_sheet(sheet_name)
        # Convert to 1-based index for gspread
        sheet.update_row(row_index + 1, row_data)
    
    def delete_row(self, sheet_name: str, row_index: int) -> None:
        """Delete a specific row from a worksheet"""
        sheet = self.get_sheet(sheet_name)
        # Convert to 1-based index for gspread
        sheet.delete_row(row_index + 1)
    
    def update_cell(self, sheet_name: str, row: int, col: int, value: Any) -> None:
        """Update a specific cell in a worksheet"""
        sheet = self.get_sheet(sheet_name)
        # Convert to 1-based indices for gspread
        sheet.update_cell(row + 1, col + 1, value)
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for the admin dashboard"""
        metrics = {
            "total_bookings": 0,
            "total_revenue": 0,
            "active_subscriptions": 0,
            "emergency_bookings": 0,
            "revenue_by_country": {},
            "bookings_by_doctor": {},
            "recent_activity": []
        }
        
        # Get payments data
        payments = self.get_all_records("payments")
        for payment in payments:
            metrics["total_bookings"] += 1
            amount = float(payment.get("amount", 0))
            metrics["total_revenue"] += amount
            
            # Track revenue by country
            country = payment.get("country", "Unknown")
            if country not in metrics["revenue_by_country"]:
                metrics["revenue_by_country"][country] = 0
            metrics["revenue_by_country"][country] += amount
            
            # Track bookings by doctor
            doctor = payment.get("doctor_type", "Unknown")
            if doctor not in metrics["bookings_by_doctor"]:
                metrics["bookings_by_doctor"][doctor] = 0
            metrics["bookings_by_doctor"][doctor] += 1
            
            # Track emergency bookings
            if payment.get("emergency", False):
                metrics["emergency_bookings"] += 1
            
            # Add to recent activity
            metrics["recent_activity"].append({
                "date": payment.get("timestamp", ""),
                "user": payment.get("name", "Unknown"),
                "activity": f"Booked {doctor}",
                "details": f"Amount: {amount}"
            })
        
        # Get subscriptions data
        subscriptions = self.get_all_records("subscriptions")
        active_count = 0
        for subscription in subscriptions:
            expiry_date = subscription.get("expiry_date", "")
            if expiry_date:
                try:
                    expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
                    if expiry > datetime.now():
                        active_count += 1
                except ValueError:
                    pass
        
        metrics["active_subscriptions"] = active_count
        
        # Sort recent activity by date (newest first)
        metrics["recent_activity"].sort(key=lambda x: x["date"], reverse=True)
        
        return metrics
    
    def get_doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors"""
        return self.get_all_records("doctors")
    
    def add_doctor(self, doctor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new doctor"""
        doctors = self.get_doctors()
        
        # Generate a new ID
        new_id = str(len(doctors) + 1)
        doctor_data["id"] = new_id
        
        # Prepare row data
        row_data = [
            new_id,
            doctor_data.get("name", ""),
            doctor_data.get("specialty", ""),
            doctor_data.get("country", ""),
            doctor_data.get("image_path", ""),
            doctor_data.get("is_specialist", False),
            doctor_data.get("rating", 5),
            doctor_data.get("is_active", True)
        ]
        
        # Append to sheet
        self.append_row("doctors", row_data)
        
        return doctor_data
    
    def update_doctor(self, doctor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing doctor"""
        doctors = self.get_doctors()
        doctor_id = doctor_data.get("id")
        
        for i, doctor in enumerate(doctors):
            if str(doctor.get("id")) == str(doctor_id):
                # Prepare row data
                row_data = [
                    doctor_id,
                    doctor_data.get("name", ""),
                    doctor_data.get("specialty", ""),
                    doctor_data.get("country", ""),
                    doctor_data.get("image_path", ""),
                    doctor_data.get("is_specialist", False),
                    doctor_data.get("rating", 5),
                    doctor_data.get("is_active", True)
                ]
                
                # Update row (add 2 to account for header row and 0-indexing)
                self.update_row("doctors", i + 2, row_data)
                return doctor_data
        
        raise ValueError(f"Doctor with ID {doctor_id} not found")
    
    def delete_doctor(self, doctor_id: str) -> bool:
        """Delete a doctor"""
        doctors = self.get_doctors()
        
        for i, doctor in enumerate(doctors):
            if str(doctor.get("id")) == str(doctor_id):
                # Delete row (add 2 to account for header row and 0-indexing)
                self.delete_row("doctors", i + 2)
                return True
        
        return False
    
    def get_payments(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get payments with optional date filtering"""
        payments = self.get_all_records("payments")
        
        if start_date or end_date:
            filtered_payments = []
            for payment in payments:
                payment_date = payment.get("timestamp", "")
                if not payment_date:
                    continue
                
                try:
                    payment_datetime = datetime.strptime(payment_date, "%Y-%m-%d %H:%M:%S")
                    
                    if start_date:
                        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                        if payment_datetime < start_datetime:
                            continue
                    
                    if end_date:
                        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                        if payment_datetime > end_datetime:
                            continue
                    
                    filtered_payments.append(payment)
                except ValueError:
                    # Skip payments with invalid dates
                    continue
            
            return filtered_payments
        
        return payments
    
    def get_doctor_earnings(self, doctor_id: str) -> Dict[str, Any]:
        """Get earnings for a specific doctor"""
        payments = self.get_all_records("payments")
        
        total_earnings = 0
        payment_count = 0
        earnings_by_date = {}
        
        for payment in payments:
            if str(payment.get("doctor_id")) == str(doctor_id):
                amount = float(payment.get("amount", 0))
                total_earnings += amount
                payment_count += 1
                
                # Track earnings by date
                date = payment.get("timestamp", "")[:10]  # Extract YYYY-MM-DD
                if date not in earnings_by_date:
                    earnings_by_date[date] = 0
                earnings_by_date[date] += amount
        
        return {
            "doctor_id": doctor_id,
            "total_earnings": total_earnings,
            "payment_count": payment_count,
            "earnings_by_date": earnings_by_date
        }
    
    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """Get all subscriptions"""
        return self.get_all_records("subscriptions")
    
    def get_revenue_data(self, period: str = "all") -> Dict[str, Any]:
        """Get revenue data with period filtering"""
        payments = self.get_all_records("payments")
        subscriptions = self.get_all_records("subscriptions")
        
        now = datetime.now()
        revenue_data = {
            "total_revenue": 0,
            "booking_revenue": 0,
            "subscription_revenue": 0,
            "revenue_by_country": {},
            "revenue_by_month": {},
            "revenue_by_day": {}
        }
        
        # Filter by period
        filtered_payments = []
        for payment in payments:
            payment_date = payment.get("timestamp", "")
            if not payment_date:
                continue
            
            try:
                payment_datetime = datetime.strptime(payment_date, "%Y-%m-%d %H:%M:%S")
                
                if period == "year":
                    if payment_datetime.year != now.year:
                        continue
                elif period == "month":
                    if payment_datetime.year != now.year or payment_datetime.month != now.month:
                        continue
                elif period == "week":
                    # Simple approximation for "this week"
                    days_diff = (now - payment_datetime).days
                    if days_diff > 7:
                        continue
                
                filtered_payments.append(payment)
            except ValueError:
                # Skip payments with invalid dates
                continue
        
        # Process payments
        for payment in filtered_payments:
            amount = float(payment.get("amount", 0))
            revenue_data["total_revenue"] += amount
            
            # Determine if booking or subscription
            if payment.get("package_type", "").lower() == "subscription":
                revenue_data["subscription_revenue"] += amount
            else:
                revenue_data["booking_revenue"] += amount
            
            # Track revenue by country
            country = payment.get("country", "Unknown")
            if country not in revenue_data["revenue_by_country"]:
                revenue_data["revenue_by_country"][country] = 0
            revenue_data["revenue_by_country"][country] += amount
            
            # Track revenue by month
            payment_date = payment.get("timestamp", "")
            if payment_date:
                try:
                    payment_datetime = datetime.strptime(payment_date, "%Y-%m-%d %H:%M:%S")
                    month_key = f"{payment_datetime.year}-{payment_datetime.month:02d}"
                    
                    if month_key not in revenue_data["revenue_by_month"]:
                        revenue_data["revenue_by_month"][month_key] = 0
                    revenue_data["revenue_by_month"][month_key] += amount
                    
                    # Track revenue by day
                    day_key = f"{payment_datetime.year}-{payment_datetime.month:02d}-{payment_datetime.day:02d}"
                    if day_key not in revenue_data["revenue_by_day"]:
                        revenue_data["revenue_by_day"][day_key] = 0
                    revenue_data["revenue_by_day"][day_key] += amount
                except ValueError:
                    pass
        
        return revenue_data
    
    def get_consultation_fees(self) -> List[Dict[str, Any]]:
        """Get consultation fees for all countries"""
        return self.get_all_records("consultation_fees")
    
    def update_consultation_fees(self, fees_data: List[Dict[str, Any]]) -> bool:
        """Update consultation fees"""
        try:
            sheet = self.get_sheet("consultation_fees")
            
            # Clear existing data (except header)
            rows = sheet.row_count
            if rows > 1:
                sheet.delete_rows(2, rows)
            
            # Add updated data
            for fee in fees_data:
                row_data = [
                    fee.get("id", ""),
                    fee.get("country", ""),
                    fee.get("general_fee", 0),
                    fee.get("specialist_fee", 0),
                    fee.get("currency", "")
                ]
                sheet.append_row(row_data)
            
            return True
        except Exception as e:
            print(f"Error updating consultation fees: {e}")
            return False
    
    def get_care_plans(self) -> List[Dict[str, Any]]:
        """Get all care plans"""
        plans = self.get_all_records("care_plans")
        
        # Get features and prices from related sheets
        features = self.get_all_records("care_plan_features")
        prices = self.get_all_records("care_plan_prices")
        
        # Organize features and prices by plan ID
        features_by_plan = {}
        for feature in features:
            plan_id = feature.get("plan_id")
            if plan_id not in features_by_plan:
                features_by_plan[plan_id] = []
            features_by_plan[plan_id].append({
                "id": feature.get("id"),
                "description": feature.get("description")
            })
        
        prices_by_plan = {}
        for price in prices:
            plan_id = price.get("plan_id")
            if plan_id not in prices_by_plan:
                prices_by_plan[plan_id] = []
            prices_by_plan[plan_id].append({
                "country": price.get("country"),
                "price": price.get("price"),
                "currency": price.get("currency")
            })
        
        # Combine data
        for plan in plans:
            plan_id = plan.get("id")
            plan["features"] = features_by_plan.get(plan_id, [])
            plan["prices"] = prices_by_plan.get(plan_id, [])
        
        return plans
    
    def update_care_plans(self, plans_data: List[Dict[str, Any]]) -> bool:
        """Update care plans"""
        try:
            # Update main care plans
            plans_sheet = self.get_sheet("care_plans")
            features_sheet = self.get_sheet("care_plan_features")
            prices_sheet = self.get_sheet("care_plan_prices")
            
            # Clear existing data (except headers)
            for sheet in [plans_sheet, features_sheet, prices_sheet]:
                rows = sheet.row_count
                if rows > 1:
                    sheet.delete_rows(2, rows)
            
            # Add updated data
            for plan in plans_data:
                # Add plan
                plan_row = [
                    plan.get("id", ""),
                    plan.get("name", ""),
                    plan.get("description", ""),
                    plan.get("duration_days", 30),
                    plan.get("is_active", True)
                ]
                plans_sheet.append_row(plan_row)
                
                # Add features
                for feature in plan.get("features", []):
                    feature_row = [
                        feature.get("id", ""),
                        plan.get("id", ""),
                        feature.get("description", "")
                    ]
                    features_sheet.append_row(feature_row)
                
                # Add prices
                for price in plan.get("prices", []):
                    price_row = [
                        plan.get("id", ""),
                        price.get("country", ""),
                        price.get("price", 0),
                        price.get("currency", "")
                    ]
                    prices_sheet.append_row(price_row)
            
            return True
        except Exception as e:
            print(f"Error updating care plans: {e}")
            return False
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        return self.get_all_records("users")
    
    def add_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new user"""
        users = self.get_users()
        
        # Generate a new ID
        new_id = str(len(users) + 1)
        user_data["id"] = new_id
        
        # Prepare permissions
        permissions = user_data.get("permissions", {})
        if not permissions:
            # Default permissions based on role
            role = user_data.get("role", "sales")
            if role == "admin":
                permissions = {
                    "dashboard": True,
                    "doctors": True,
                    "payments": True,
                    "subscriptions": True,
                    "revenue": True,
                    "consultation_fees": True,
                    "care_plans": True,
                    "settings": True
                }
            elif role == "sales":
                permissions = {
                    "dashboard": True,
                    "doctors": False,
                    "payments": True,
                    "subscriptions": True,
                    "revenue": True,
                    "consultation_fees": False,
                    "care_plans": False,
                    "settings": False
                }
            else:  # content
                permissions = {
                    "dashboard": True,
                    "doctors": True,
                    "payments": False,
                    "subscriptions": False,
                    "revenue": False,
                    "consultation_fees": True,
                    "care_plans": True,
                    "settings": False
                }
        
        # Prepare row data
        row_data = [
            new_id,
            user_data.get("name", ""),
            user_data.get("email", ""),
            user_data.get("password", ""),  # In a real app, this should be hashed
            user_data.get("role", "sales"),
            permissions.get("dashboard", False),
            permissions.get("doctors", False),
            permissions.get("payments", False),
            permissions.get("subscriptions", False),
            permissions.get("revenue", False),
            permissions.get("consultation_fees", False),
            permissions.get("care_plans", False),
            permissions.get("settings", False)
        ]
        
        # Append to sheet
        self.append_row("users", row_data)
        
        # Return user data with permissions
        user_data["permissions"] = permissions
        return user_data
    
    def update_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing user"""
        users = self.get_users()
        user_id = user_data.get("id")
        
        for i, user in enumerate(users):
            if str(user.get("id")) == str(user_id):
                permissions = user_data.get("permissions", {})
                
                # Prepare row data
                row_data = [
                    user_id,
                    user_data.get("name", user.get("name", "")),
                    user_data.get("email", user.get("email", "")),
                    user.get("password", ""),  # Don't update password here
                    user_data.get("role", user.get("role", "sales")),
                    permissions.get("dashboard", False),
                    permissions.get("doctors", False),
                    permissions.get("payments", False),
                    permissions.get("subscriptions", False),
                    permissions.get("revenue", False),
                    permissions.get("consultation_fees", False),
                    permissions.get("care_plans", False),
                    permissions.get("settings", False)
                ]
                
                # Update row (add 2 to account for header row and 0-indexing)
                self.update_row("users", i + 2, row_data)
                return user_data
        
        raise ValueError(f"User with ID {user_id} not found")
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        users = self.get_users()
        
        for i, user in enumerate(users):
            if str(user.get("id")) == str(user_id):
                # Delete row (add 2 to account for header row and 0-indexing)
                self.delete_row("users", i + 2)
                return True
        
        return False
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """Change a user's password"""
        users = self.get_users()
        
        for i, user in enumerate(users):
            if str(user.get("id")) == str(user_id):
                # Update password cell (add 2 to account for header row and 0-indexing)
                self.update_cell("users", i + 2, 4, new_password)  # Assuming password is in column 4
                return True
        
        return False


# Create a singleton instance
sheets_service = GoogleSheetsService()

def get_sheets_service() -> GoogleSheetsService:
    """Get the Google Sheets service instance"""
    return sheets_service
