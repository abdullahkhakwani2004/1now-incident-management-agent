"""
1Now Fleet Platform — Late Return & Incident Handler
=====================================================
Simulates pulling renter profiles, checkout terms, and live GPS data
for overdue bookings. Generates automated SMS drafts and fleet owner
summaries with calculated late fee penalties.

Usage:
    python 1now_late_return_handler.py
"""

import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
import textwrap


# ─────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────

@dataclass
class RenterProfile:
    renter_id: str
    full_name: str
    phone: str
    email: str
    license_number: str
    membership_tier: str          # "Standard" | "Silver" | "Gold"
    prior_late_returns: int
    damage_incidents: int
    payment_method: str


@dataclass
class CheckoutTerms:
    booking_id: str
    vehicle_id: str
    vehicle_make: str
    vehicle_model: str
    vehicle_plate: str
    daily_rate: float             # USD per day
    late_fee_per_hour: float      # USD per hour after grace
    grace_period_minutes: int
    checkout_time: datetime
    agreed_return_time: datetime
    deposit_held: float
    insurance_type: str           # "Basic" | "Comprehensive"


@dataclass
class GPSSnapshot:
    vehicle_id: str
    latitude: float
    longitude: float
    speed_kmh: float
    last_ping: datetime
    location_label: str           # human-readable area
    is_at_lot: bool


@dataclass
class LateReturnReport:
    booking_id: str
    renter: RenterProfile
    terms: CheckoutTerms
    gps: GPSSnapshot
    current_time: datetime
    minutes_overdue: int
    billable_hours_overdue: float
    late_fee_total: float
    new_projected_total: float
    sms_draft: str
    owner_summary: str


# ─────────────────────────────────────────────
# MOCK DATA STORE
# ─────────────────────────────────────────────

MOCK_BOOKINGS: dict[str, tuple[RenterProfile, CheckoutTerms]] = {

    "BK-1042": (
        RenterProfile(
            renter_id="R-881",
            full_name="Tariq Mehmood",
            phone="+92 300 1234567",
            email="tariq.m@email.com",
            license_number="PB-LH-2019-44821",
            membership_tier="Silver",
            prior_late_returns=1,
            damage_incidents=0,
            payment_method="Visa *4821",
        ),
        CheckoutTerms(
            booking_id="BK-1042",
            vehicle_id="VH-007",
            vehicle_make="Toyota",
            vehicle_model="Corolla Altis",
            vehicle_plate="LHR-RN-4421",
            daily_rate=8500.00,
            late_fee_per_hour=950.00,
            grace_period_minutes=30,
            checkout_time=datetime.now() - timedelta(hours=26, minutes=10),
            agreed_return_time=datetime.now() - timedelta(hours=2, minutes=15),
            deposit_held=25000.00,
            insurance_type="Comprehensive",
        ),
    ),

    "BK-1087": (
        RenterProfile(
            renter_id="R-334",
            full_name="Ayesha Farooq",
            phone="+92 321 9876543",
            email="ayesha.f@workmail.pk",
            license_number="PB-LH-2021-30092",
            membership_tier="Gold",
            prior_late_returns=0,
            damage_incidents=0,
            payment_method="HBL Debit *0033",
        ),
        CheckoutTerms(
            booking_id="BK-1087",
            vehicle_id="VH-019",
            vehicle_make="Honda",
            vehicle_model="HR-V",
            vehicle_plate="LHR-AA-7701",
            daily_rate=12000.00,
            late_fee_per_hour=1400.00,
            grace_period_minutes=30,
            checkout_time=datetime.now() - timedelta(hours=49, minutes=5),
            agreed_return_time=datetime.now() - timedelta(hours=1, minutes=5),
            deposit_held=35000.00,
            insurance_type="Comprehensive",
        ),
    ),

    "BK-1103": (
        RenterProfile(
            renter_id="R-556",
            full_name="Bilal Chaudhry",
            phone="+92 333 4455667",
            email="b.chaudhry@hotmail.com",
            license_number="PB-LH-2017-19834",
            membership_tier="Standard",
            prior_late_returns=3,
            damage_incidents=1,
            payment_method="Cash deposit",
        ),
        CheckoutTerms(
            booking_id="BK-1103",
            vehicle_id="VH-031",
            vehicle_make="Suzuki",
            vehicle_model="Swift",
            vehicle_plate="LHR-BC-2210",
            daily_rate=6000.00,
            late_fee_per_hour=750.00,
            grace_period_minutes=30,
            checkout_time=datetime.now() - timedelta(hours=73, minutes=40),
            agreed_return_time=datetime.now() - timedelta(hours=3, minutes=40),
            deposit_held=18000.00,
            insurance_type="Basic",
        ),
    ),
}


MOCK_GPS: dict[str, GPSSnapshot] = {
    "VH-007": GPSSnapshot(
        vehicle_id="VH-007",
        latitude=31.4697,
        longitude=74.2728,
        speed_kmh=34.5,
        last_ping=datetime.now() - timedelta(minutes=2),
        location_label="DHA Phase 5, Lahore",
        is_at_lot=False,
    ),
    "VH-019": GPSSnapshot(
        vehicle_id="VH-019",
        latitude=31.5204,
        longitude=74.3587,
        speed_kmh=0.0,
        last_ping=datetime.now() - timedelta(minutes=1),
        location_label="1Now Rental Lot — Johar Town",
        is_at_lot=True,
    ),
    "VH-031": GPSSnapshot(
        vehicle_id="VH-031",
        latitude=31.3820,
        longitude=74.1950,
        speed_kmh=0.0,
        last_ping=datetime.now() - timedelta(minutes=8),
        location_label="Model Town, Lahore",
        is_at_lot=False,
    ),
}


# ─────────────────────────────────────────────
# CORE LOGIC
# ─────────────────────────────────────────────

def fetch_booking_data(booking_id: str) -> tuple[RenterProfile, CheckoutTerms]:
    """Simulate fetching booking, renter profile and checkout terms from DB."""
    print(f"\n  ▸ Querying database for booking {booking_id}...")
    if booking_id not in MOCK_BOOKINGS:
        raise ValueError(f"Booking ID '{booking_id}' not found in system.")
    print(f"  ▸ Renter profile retrieved.")
    print(f"  ▸ Checkout terms loaded.")
    return MOCK_BOOKINGS[booking_id]


def fetch_gps_data(vehicle_id: str) -> GPSSnapshot:
    """Simulate pulling live GPS telemetry for a vehicle."""
    print(f"  ▸ Pinging GPS transponder for vehicle {vehicle_id}...")
    if vehicle_id not in MOCK_GPS:
        raise ValueError(f"No GPS signal found for vehicle '{vehicle_id}'.")
    gps = MOCK_GPS[vehicle_id]
    print(f"  ▸ GPS lock acquired — last ping {gps.last_ping.strftime('%H:%M:%S')}.")
    return gps


def calculate_late_fees(terms: CheckoutTerms, current_time: datetime) -> tuple[int, float, float]:
    """
    Returns:
        minutes_overdue       — total minutes past agreed return time
        billable_hours        — hours after grace period (rounded up)
        late_fee_total        — PKR owed for lateness
    """
    overdue_delta = current_time - terms.agreed_return_time
    minutes_overdue = max(0, int(overdue_delta.total_seconds() / 60))

    # Grace period applies
    billable_minutes = max(0, minutes_overdue - terms.grace_period_minutes)
    import math
    billable_hours = math.ceil(billable_minutes / 60) if billable_minutes > 0 else 0

    late_fee_total = billable_hours * terms.late_fee_per_hour
    return minutes_overdue, float(billable_hours), late_fee_total


def draft_sms(renter: RenterProfile, terms: CheckoutTerms,
              gps: GPSSnapshot, minutes_overdue: int, late_fee: float) -> str:
    """Compose a tailored SMS based on vehicle status and renter history."""

    hours_late = minutes_overdue // 60
    mins_late  = minutes_overdue % 60
    time_str   = f"{hours_late}h {mins_late}m" if hours_late else f"{mins_late} minutes"
    fee_str    = f"PKR {late_fee:,.0f}" if late_fee > 0 else "none yet (within grace)"

    # — Vehicle is moving —
    if gps.speed_kmh > 5:
        tone_line = (
            f"Our GPS shows your vehicle is currently in motion near {gps.location_label}. "
            f"Please complete your trip and return immediately."
        )
    # — Vehicle parked at lot —
    elif gps.is_at_lot:
        tone_line = (
            f"We can see your vehicle is now back at our lot — please check in with staff "
            f"immediately to complete the return and settle any outstanding charges."
        )
    # — Vehicle parked elsewhere —
    else:
        tone_line = (
            f"Our GPS shows your vehicle is currently stationary near {gps.location_label}. "
            f"Please return it to our lot as soon as possible."
        )

    # Escalate tone for repeat offenders
    if renter.prior_late_returns >= 3:
        closing = (
            "Please be aware that continued delays may result in your account being flagged "
            "and future rental eligibility reviewed. Contact us immediately: +92-42-1NOW-FLEET."
        )
    elif renter.prior_late_returns >= 1:
        closing = (
            "We appreciate your past business. Please contact us if you need a brief extension "
            "arranged: +92-42-1NOW-FLEET."
        )
    else:
        closing = (
            "If you need a short extension, we are happy to arrange one — "
            "please call us right away: +92-42-1NOW-FLEET."
        )

    sms = (
        f"[1Now Rentals] Hi {renter.full_name.split()[0]}, your booking for the "
        f"{terms.vehicle_make} {terms.vehicle_model} ({terms.vehicle_plate}) was due back "
        f"{time_str} ago. {tone_line} "
        f"A late fee of {fee_str} has been applied to your account. {closing}"
    )
    return sms


def draft_owner_summary(renter: RenterProfile, terms: CheckoutTerms,
                         gps: GPSSnapshot, minutes_overdue: int,
                         billable_hours: float, late_fee: float,
                         current_time: datetime) -> str:
    """Generate a structured summary update for the fleet owner."""

    hours_late = minutes_overdue // 60
    mins_late  = minutes_overdue % 60
    overdue_str = f"{hours_late}h {mins_late}m"

    vehicle_status = (
        f"MOVING — {gps.speed_kmh:.1f} km/h near {gps.location_label}"
        if gps.speed_kmh > 5
        else (
            f"PARKED AT LOT — {gps.location_label}" if gps.is_at_lot
            else f"STATIONARY — {gps.location_label}"
        )
    )

    risk_flags = []
    if renter.prior_late_returns >= 3:
        risk_flags.append(f"Repeat offender ({renter.prior_late_returns} prior late returns)")
    if renter.damage_incidents > 0:
        risk_flags.append(f"Prior damage incident on record ({renter.damage_incidents})")
    if gps.speed_kmh > 5:
        risk_flags.append("Vehicle in active motion — location changing")
    if not terms.deposit_held >= late_fee:
        risk_flags.append("⚠ Deposit may be insufficient to cover accrued fees")

    risk_block = "\n    • ".join(risk_flags) if risk_flags else "None"

    summary = f"""
╔══════════════════════════════════════════════════════════════════╗
║          1Now FLEET — OVERDUE RETURN INCIDENT REPORT            ║
╚══════════════════════════════════════════════════════════════════╝

  Generated    : {current_time.strftime('%d %b %Y  %H:%M:%S')}
  Booking ID   : {terms.booking_id}

── RENTER ──────────────────────────────────────────────────────────
  Name         : {renter.full_name}
  Phone        : {renter.phone}
  Email        : {renter.email}
  Membership   : {renter.membership_tier}
  Licence No.  : {renter.license_number}
  Payment      : {renter.payment_method}

── VEHICLE ─────────────────────────────────────────────────────────
  Vehicle      : {terms.vehicle_make} {terms.vehicle_model}
  Plate        : {terms.vehicle_plate}
  Vehicle ID   : {terms.vehicle_id}
  Insurance    : {terms.insurance_type}

── BOOKING TIMELINE ────────────────────────────────────────────────
  Checked Out  : {terms.checkout_time.strftime('%d %b %Y  %H:%M')}
  Due Back     : {terms.agreed_return_time.strftime('%d %b %Y  %H:%M')}
  Current Time : {current_time.strftime('%d %b %Y  %H:%M')}
  Overdue By   : {overdue_str}
  Grace Period : {terms.grace_period_minutes} min (already elapsed)

── LIVE GPS STATUS ─────────────────────────────────────────────────
  Status       : {vehicle_status}
  Coordinates  : {gps.latitude:.4f}°N, {gps.longitude:.4f}°E
  Last Ping    : {gps.last_ping.strftime('%H:%M:%S')}

── FINANCIAL SUMMARY ───────────────────────────────────────────────
  Daily Rate   : PKR {terms.daily_rate:>10,.2f}
  Late Fee Rate: PKR {terms.late_fee_per_hour:>10,.2f} / hr
  Billable Hrs : {billable_hours:.0f} hr(s)
  Late Fee Due : PKR {late_fee:>10,.2f}
  Deposit Held : PKR {terms.deposit_held:>10,.2f}
  Deposit Cover: {'✔ Sufficient' if terms.deposit_held >= late_fee else '✘ SHORTFALL — manual follow-up required'}

── RISK FLAGS ──────────────────────────────────────────────────────
    • {risk_block}

── RECOMMENDED ACTIONS ─────────────────────────────────────────────
  1. SMS notification sent to renter at {renter.phone}
  2. {'Dispatch lot attendant — vehicle on premises' if gps.is_at_lot else 'Monitor GPS — escalate if no movement within 60 min'}
  3. {'Review account for suspension given repeat late return history' if renter.prior_late_returns >= 3 else 'Log incident to renter profile'}
  4. {'Initiate deposit deduction for PKR ' + f'{late_fee:,.0f}' if late_fee > 0 else 'No fee action required yet'}

════════════════════════════════════════════════════════════════════
"""
    return summary


def process_overdue_booking(booking_id: str) -> LateReturnReport:
    """Main pipeline: fetch data → calculate fees → generate drafts."""

    print(f"\n{'═'*60}")
    print(f"  1Now FLEET  ·  Processing Overdue Booking: {booking_id}")
    print(f"{'═'*60}")

    renter, terms = fetch_booking_data(booking_id)
    gps = fetch_gps_data(terms.vehicle_id)

    current_time = datetime.now()
    minutes_overdue, billable_hours, late_fee = calculate_late_fees(terms, current_time)
    new_projected_total = terms.daily_rate + late_fee

    print(f"  ▸ Late fee calculated: PKR {late_fee:,.2f}")

    sms = draft_sms(renter, terms, gps, minutes_overdue, late_fee)
    summary = draft_owner_summary(
        renter, terms, gps, minutes_overdue, billable_hours, late_fee, current_time
    )
    print(f"  ▸ SMS draft generated.")
    print(f"  ▸ Owner summary compiled.")

    return LateReturnReport(
        booking_id=booking_id,
        renter=renter,
        terms=terms,
        gps=gps,
        current_time=current_time,
        minutes_overdue=minutes_overdue,
        billable_hours_overdue=billable_hours,
        late_fee_total=late_fee,
        new_projected_total=new_projected_total,
        sms_draft=sms,
        owner_summary=summary,
    )


def display_report(report: LateReturnReport):
    """Print results to terminal in a clean, operator-friendly format."""

    print(report.owner_summary)

    print("── AUTOMATED SMS DRAFT ─────────────────────────────────────────────")
    print()
    # Word-wrap to 65 chars to simulate SMS preview
    wrapped = textwrap.fill(report.sms_draft, width=65)
    for line in wrapped.splitlines():
        print(f"  {line}")
    print()
    print(f"  → Recipient : {report.renter.phone}")
    print(f"  → Status    : READY TO SEND (awaiting operator approval)")
    print()
    print("════════════════════════════════════════════════════════════════════")


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

def main():
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║              1Now Fleet Management Platform                     ║")
    print("║              Late Return & Incident Handler  v1.0               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    available = ", ".join(MOCK_BOOKINGS.keys())
    print(f"\n  Available mock booking IDs: {available}")

    while True:
        booking_id = input("\n  Enter overdue booking ID (or 'quit' to exit): ").strip().upper()

        if booking_id in ("QUIT", "Q", "EXIT"):
            print("\n  Session closed. Goodbye.\n")
            break

        try:
            report = process_overdue_booking(booking_id)
            display_report(report)

            again = input("  Process another booking? (y/n): ").strip().lower()
            if again != "y":
                print("\n  Session closed. Goodbye.\n")
                break

        except ValueError as e:
            print(f"\n  ✘ Error: {e}")
            print(f"  Valid IDs are: {available}")


if __name__ == "__main__":
    main()
