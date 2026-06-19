import datetime
import random

# ==========================================
# MOCK DATABASE (Simulating 1Now Fleet Data)
# ==========================================
MOCK_BOOKINGS = {
    "BK-9041": {
        "renter_name": "Alex Mercer",
        "renter_phone": "+1 (555) 321-4499",
        "car_model": "Tesla Model 3 (2023)",
        "scheduled_return": datetime.datetime.now() - datetime.timedelta(hours=2, minutes=15),
        "hourly_late_rate": 50.0,
        "operator_email": "fleet_ops@luxuryrentals.com"
    },
    "BK-2281": {
        "renter_name": "Sarah Jenkins",
        "renter_phone": "+1 (555) 888-1122",
        "car_model": "Toyota RAV4 (2022)",
        "scheduled_return": datetime.datetime.now() - datetime.timedelta(hours=4),
        "hourly_late_rate": 35.0,
        "operator_email": "admin@midwestrides.com"
    }
}

# Simulating live vehicle telematics
def get_mock_telematics(booking_id):
    if booking_id == "BK-9041":
        return {
            "gps_status": "Active",
            "coordinates": "34.0522° N, 118.2437° W (Moving - 45 mph)",
            "renter_status": "unresponsive"
        }
    else:
        return {
            "gps_status": "Active",
            "coordinates": "40.7128° N, 74.0060° W (Stationary - Idle at Airport)",
            "renter_status": "responsive"
        }

# ==========================================
# CLAUDE CORE AGENT ENGINE
# ==========================================
class ClaudeIncidentAgent:
    def __init__(self, booking_id):
        if booking_id not in MOCK_BOOKINGS:
            raise ValueError("Invalid Booking ID reference.")
        self.booking = MOCK_BOOKINGS[booking_id]
        self.telematics = get_mock_telematics(booking_id)
        
    def calculate_late_fees(self):
        now = datetime.datetime.now()
        time_overdue = now - self.booking["scheduled_return"]
        hours_overdue = max(1, round(time_overdue.total_seconds() / 3600, 1))
        total_penalty = round(hours_overdue * self.booking["hourly_late_rate"], 2)
        return hours_overdue, total_penalty

    def generate_action_plan(self):
        hours, penalty = self.calculate_late_fees()
        
        # Base context shared with Claude's logic loop
        context = f"""
        [System Context: 1Now AI Support Agent]
        Renter Name: {self.booking['renter_name']}
        Vehicle: {self.booking['car_model']}
        Hours Overdue: {hours} hours
        Calculated Penalty: ${penalty}
        Vehicle Live GPS status: {self.telematics['coordinates']}
        Renter Responsiveness: {self.telematics['renter_status']}
        """
        
        print("\n" + "="*50)
        print(f"🤖 CLAUDE INCIDENT AGENT EVALUATING: {self.booking['car_model']}")
        print("="*50)
        
        # Handling the "Happy Path" vs "Messy Edge" logic paths
        if self.telematics['renter_status'] == "responsive":
            # Happy Path: Customer acknowledges late return, automate settlement link
            sms_draft = f"Hi {self.booking['renter_name']}, your rental window for the {self.booking['car_model']} expired {hours} hours ago. A late fee of ${penalty} has been added. Please return the vehicle safely to the designated lot or use this link to extend your booking: 1now.ai/extend/active-session."
            internal_note = "Happy Path Resolution: Renter acknowledged delay. System generated payment/extension link. Monitoring vehicle return trajectory."
        else:
            # Messy Edge: Renter is ghosting, car is moving outside target zone
            sms_draft = f"URGENT: {self.booking['renter_name']}, your rental period ended {hours} hours ago and we have been unable to reach you. Vehicle tracking shows active movement at {self.telematics['coordinates']}. Please contact dispatch immediately to avoid asset recovery procedures."
            internal_note = f"CRITICAL WARNING: Renter uncontactable. Vehicle active in unauthorized window. Drafted breach notice. Flagged for potential vehicle repossession dispatch if no update within 15 minutes."

        return sms_draft, internal_note

# ==========================================
# INTERACTIVE TERMINAL EXECUTION
# ==========================================
if __name__ == "__main__":
    print("🚀 Starting 1Now AI Support Agent Terminal Application...")
    print("Available Active Overdue Bookings to Test:")
    for b_id in MOCK_BOOKINGS.keys():
        print(f" - {b_id} ({MOCK_BOOKINGS[b_id]['renter_name']})")
        
    user_input = input("\nEnter Booking ID to process: ").strip().upper()
    
    try:
        agent = ClaudeIncidentAgent(user_input)
        sms, note = agent.generate_action_plan()
        
        print("\n💬 DRAFTED CUSTOMER SMS VIA CLAUDE:")
        print(f'"{sms}"')
        
        print("\n📋 INTERNAL FLEET OPERATOR LOG NOTE:")
        print(note)
        print("="*50 + "\n")
    except ValueError as e:
        print(f"\n❌ Error: {e}\n")