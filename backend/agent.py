import json
import re
import ollama

from tools import (
    identify_user,
    fetch_slots,
    book_appointment,
    retrieve_appointments,
    cancel_appointment,
    modify_appointment,
    end_conversation
)

# =====================================
# Conversation Memory
# =====================================

conversation_history = []

current_user = {
    "name": None,
    "phone": None
}

pending_action = None

# =====================================
# System Prompt
# =====================================

SYSTEM_PROMPT = """
You are a Healthcare Voice AI Assistant.

Identify ONLY the user's intent.

Possible intents:

identify_user
fetch_slots
book_appointment
retrieve_appointments
cancel_appointment
modify_appointment
end_conversation

Return ONLY JSON.

Example:

{
"intent":"book_appointment"
}
"""

# =====================================
# Extract JSON
# =====================================

def extract_json(text):

    matches = re.findall(
        r"\{.*?\}",
        text,
        re.DOTALL
    )

    for match in matches:

        try:
            return json.loads(match)

        except Exception:
            pass

    return None


# =====================================
# Detect Intent
# =====================================

def detect_intent(user_message):

    response = ollama.chat(

        model="phi3:mini",

        messages=[
            {
                "role":"system",
                "content":SYSTEM_PROMPT
            },
            {
                "role":"user",
                "content":user_message
            }
        ]
    )

    return extract_json(
        response["message"]["content"]
    )


# =====================================
# Format Appointment List
# =====================================

def format_appointments(result):

    if len(result) == 0:
        return "You don't have any appointments."

    text = "Your appointments are:\n\n"

    for index, appt in enumerate(result, start=1):

        text += (
            f"Appointment {index}\n"
            f"Patient : {appt['name']}\n"
            f"Date : {appt['date']}\n"
            f"Time : {appt['time']}\n\n"
        )

    return text

# =====================================
# Format Slots
# =====================================

def format_slots(result):

    slots=[]

    for slot in result["available_slots"]:

        slot=(

            slot.replace(":00","")
                .replace("AM"," AM")
                .replace("PM"," PM")
                .lstrip("0")

        )

        slots.append(slot)

    return (

        "Available appointment slots are:\n\n"

        +"\n".join(

            f"• {s}"

            for s in slots

        )

        +"\n\nWhich slot would you like to book?"

    )
# =====================================
# Main Agent
# =====================================

def process_user_message(user_message):

    global pending_action

    conversation_history.append(
        {
            "role":"user",
            "content":user_message
        }
    )

    message_lower=user_message.lower()

    print("\n======================")
    print("USER :",user_message)
    print("======================")

    # =====================================
    # Fetch Slots
    # =====================================

    if any(x in message_lower for x in [

        "available slots",
        "show slots",
        "available appointment",
        "free slots",
        "slot"

    ]):

        result=fetch_slots()

        return{

            "tool":"fetch_slots",
            "tool_result":result,
            "response":format_slots(result)

        }

    # =====================================
    # Book Appointment
    # =====================================

    elif any(x in message_lower for x in [

        "book",
        "schedule"

    ]):
        # Start a fresh booking every time

        current_user["name"] = None
        current_user["phone"] = None
        current_user.pop("date", None)

        pending_action = "book_name"
        return {
        "tool": None,
        "response": "Sure! What is the patient's name?"
    }

    # =====================================
    # Retrieve Appointments
    # =====================================

    elif any(x in message_lower for x in [

        "show appointments",
        "show my appointments",
        "my appointments",
        "retrieve appointments",
        "my bookings"

    ]):

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        if phone_match:

            current_user["phone"] = phone_match.group()

        if current_user["phone"] is None:

            pending_action = "retrieve_phone"

            return {
                "tool": None,
                "response": "Sure. Please provide your phone number."
            }

        result = retrieve_appointments(
            current_user["phone"]
        )

        return {
            "tool": "retrieve_appointments",
            "tool_result": result,
            "response": format_appointments(result)
        }

    # =====================================
    # Cancel Appointment
    # =====================================

    elif any(x in message_lower for x in [

        "cancel",
        "delete",
        "remove"

    ]):

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        if phone_match:

            current_user["phone"] = phone_match.group()

        id_match = re.search(
            r"appointment\s*(\d+)",
            message_lower
        )

        # ---------------------------------
        # Cancel using Appointment Number
        # ---------------------------------

        if id_match:

            if current_user["phone"] is None:

                return {
                    "tool": None,
                    "response": "Please provide your phone number."
                }

            appointments = retrieve_appointments(
                current_user["phone"]
            )

            index = int(id_match.group(1)) - 1

            if index < 0 or index >= len(appointments):

                return {
                    "tool": None,
                    "response": "Invalid appointment number."
                }

            appointment_id = appointments[index]["id"]

            result = cancel_appointment(
                appointment_id
            )

            return {

                "tool": "cancel_appointment",

                "tool_result": result,

                "response": result["message"]

            }

        # ---------------------------------
        # Cancel using Date & Time
        # ---------------------------------

        date_match = re.search(

            r"\d{4}-\d{2}-\d{2}",

            user_message

        )

        time_match = re.search(

            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",

            user_message,

            re.IGNORECASE

        )

        if current_user["phone"] and date_match and time_match:

            appointments = retrieve_appointments(
                current_user["phone"]
            )

            target = None

            for appt in appointments:

                if (
                    appt["date"] == date_match.group()
                    and appt["time"] == time_match.group().upper()
                ):

                    target = appt["id"]

                    break

            if target is None:

                return {

                    "tool": None,

                    "response": "Appointment not found."

                }

            result = cancel_appointment(target)

            return {

                "tool": "cancel_appointment",

                "tool_result": result,

                "response": result["message"]

            }

        return {

            "tool": None,

            "response":
            "Please provide the appointment number or date and time."

        }

    # =====================================
    # Modify Appointment
    # =====================================

    elif any(x in message_lower for x in [

        "modify",
        "move",
        "change",
        "reschedule"

    ]):

        if current_user["phone"] is None:

            return {

                "tool": None,

                "response":"Please provide your phone number."

            }

        dates = re.findall(

            r"\d{4}-\d{2}-\d{2}",

            user_message

        )

        times = re.findall(

            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",

            user_message,

            re.IGNORECASE

        )

        if len(dates) == 1:

            dates.append(
                dates[0]
            )

        if len(times) < 2:

            return {

                "tool":None,

                "response":
                "Please provide both old and new appointment times."

            }

        result = modify_appointment(

            current_user["phone"],

            dates[0],

            times[0].upper(),

            dates[1],

            times[1].upper()

        )

        return {

            "tool":"modify_appointment",

            "tool_result":result,

            "response":result["message"]

        }
    # =====================================
    # End Conversation
    # =====================================

    elif any(x in message_lower for x in [

        "bye",
        "goodbye",
        "exit",
        "quit",
        "thank you",
        "thanks"

    ]):

        pending_action = None

        result = end_conversation()

        return {

            "tool":"end_conversation",

            "tool_result":result,

            "response":"Thank you for using the Healthcare Voice AI Assistant. Have a great day!"

        }

    # =====================================
    # Pending Conversation
    # =====================================

    if pending_action == "retrieve_phone":

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        if phone_match:

            current_user["phone"] = phone_match.group()

            pending_action = None

            result = retrieve_appointments(
                current_user["phone"]
            )

            return {

                "tool":"retrieve_appointments",

                "tool_result":result,

                "response":format_appointments(result)

            }

        return {

            "tool":None,

            "response":"Please enter a valid 10-digit phone number."

        }

    # =====================================
    # Book Conversation
    # =====================================

    if pending_action == "book_name":

        current_user["name"] = user_message.strip()

        pending_action = "book_phone"

        return {

            "tool":None,

            "response":"Please provide your phone number."

        }


    if pending_action == "book_phone":

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        if not phone_match:

            return {

                "tool":None,

                "response":"Please enter a valid 10-digit phone number."

            }

        current_user["phone"] = phone_match.group()

        pending_action = "book_date"

        return {

            "tool":None,

            "response":"Which date would you like to book? (YYYY-MM-DD)"

        }


    if pending_action == "book_date":

        date_match = re.search(

            r"\d{4}-\d{2}-\d{2}",

            user_message

        )

        if not date_match:

            return {

                "tool":None,

                "response":"Please enter the date in YYYY-MM-DD format."

            }

        current_user["date"] = date_match.group()

        pending_action = "book_time"

        return {

            "tool":None,

            "response":"Which time would you like?"

        }


    if pending_action == "book_time":

        time_match = re.search(

            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",

            user_message,

            re.IGNORECASE

        )

        if not time_match:

            return {

                "tool":None,

                "response":"Please provide a valid appointment time."

            }

        result = book_appointment(

            current_user["name"],

            current_user["phone"],

            current_user["date"],

            time_match.group().upper()

        )

        pending_action = None

        return {

            "tool":"book_appointment",

            "tool_result":result,

            "response":result["message"]

        }

    # =====================================
    # Final Fallback
    # =====================================

    return {

        "tool":None,

        "response":

        "I can help you with:\n\n"

        "• Show available slots\n"

        "• Book an appointment\n"

        "• View appointments\n"

        "• Cancel an appointment\n"

        "• Modify an appointment\n\n"

        "How may I assist you today?"

    }
