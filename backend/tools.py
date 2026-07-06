from database import SessionLocal
from models import Appointment


# =====================================
# Identify User
# =====================================

def identify_user(phone):

    db = SessionLocal()

    appointments = (
        db.query(Appointment)
        .filter(Appointment.phone == phone)
        .all()
    )

    return {
        "phone": phone,
        "appointment_count": len(appointments)
    }


# =====================================
# Fetch Available Slots
# =====================================

def fetch_slots():

    slots = [
        "10:00 AM",
        "11:00 AM",
        "02:00 PM",
        "04:00 PM"
    ]

    return {
        "available_slots": slots
    }


# =====================================
# Book Appointment
# =====================================

def book_appointment(
    name,
    phone,
    date,
    time
):

    db = SessionLocal()

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.date == date,
            Appointment.time == time
        )
        .first()
    )

    if existing:

        return {
            "status": "failed",
            "message": "Slot already booked"
        }

    appointment = Appointment(
        name=name,
        phone=phone,
        date=date,
        time=time
    )

    db.add(appointment)
    db.commit()

    return {
        "status": "success",
        "message":
        f"Your appointment has been booked successfully for "
        f"{date} at {time}."
    
    }


# =====================================
# Retrieve Appointments
# =====================================

def retrieve_appointments(phone):

    db = SessionLocal()

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.phone == phone
        )
        .all()
    )

    result = []

    for item in appointments:

        result.append(
            {
                "id": item.id,
                "name": item.name,
                "date": item.date,
                "time": item.time
            }
        )

    return result

# =====================================
# Cancel Appointment
# =====================================

def cancel_appointment(appointment_id):

    db = SessionLocal()

    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id)
        .first()
    )

    if not appointment:

        db.close()

        return {
            "status":"failed",
            "message":"Appointment not found."
        }

    db.delete(appointment)

    db.commit()

    db.close()

    return {
        "status":"success",
        "message":"Appointment cancelled successfully."
    }
# =====================================
# Modify Appointment
# =====================================

def modify_appointment(
    phone,
    old_date,
    old_time,
    new_date,
    new_time
):

    db = SessionLocal()

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.phone == phone,
            Appointment.date == old_date,
            Appointment.time == old_time
        )
        .first()
    )

    if not appointment:

        return {
            "status": "failed",
            "message": "Original appointment not found"
        }

    already_booked = (
        db.query(Appointment)
        .filter(
            Appointment.date == new_date,
            Appointment.time == new_time
        )
        .first()
    )

    if already_booked:

        return {
            "status": "failed",
            "message": "New slot already booked"
        }

    appointment.date = new_date
    appointment.time = new_time

    db.commit()

    return {
        "status": "success",
        "message": f"Your appointment has been rescheduled to {new_date} at {new_time}."
    }


# =====================================
# End Conversation
# =====================================

def end_conversation():

    return {
        "status": "success",
        "message": "Thank you for using Healthcare Voice AI. Have a great day!"
    }
