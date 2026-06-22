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

# =====================================
# System Prompt
# =====================================

SYSTEM_PROMPT = """
You are a healthcare appointment assistant.

Classify the user's intent.

Possible intents:

1. identify_user
   Examples:
   - my phone number is 9876543210
   - identify me

2. fetch_slots
   Examples:
   - available slots
   - show slots
   - what times are available

3. book_appointment
   Examples:
   - book appointment
   - schedule appointment

4. retrieve_appointments
   Examples:
   - show my appointments
   - list my bookings
   - retrieve appointments
   - what appointments do I have

5. cancel_appointment
   Examples:
   - cancel appointment
   - delete appointment
   - remove appointment

6. modify_appointment
   Examples:
   - move appointment
   - reschedule appointment
   - change appointment time

7. end_conversation
   Examples:
   - bye
   - goodbye

Return ONLY JSON.

Examples:

{
    "intent":"retrieve_appointments",
    "phone":"9876543210"
}

{
    "intent":"cancel_appointment",
    "phone":"9876543210",
    "date":"2026-06-25",
    "time":"10:00 AM"
}

{
    "intent":"modify_appointment",
    "phone":"9876543210",
    "old_date":"2026-06-25",
    "old_time":"10:00 AM",
    "new_date":"2026-06-25",
    "new_time":"11:00 AM"
}
"""
# =====================================
# Extract JSON safely
# =====================================

def extract_json(text):

    matches = re.findall(
        r"\{[^{}]*\}",
        text,
        re.DOTALL
    )

    for match in matches:

        try:
            return json.loads(match)

        except Exception:
            continue

    return None

# =====================================
# Ask LLM
# =====================================

def detect_intent(user_message):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for msg in conversation_history:
        messages.append(msg)

    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    response = ollama.chat(
    model="phi3:mini",
    messages=messages
)

    content = response["message"]["content"]

    print("\n===================")
    print("LLM RESPONSE")
    print(content)
    print("===================\n")

    parsed = extract_json(content)

    return parsed


# =====================================
# Main Agent
# =====================================

def process_user_message(user_message):

    conversation_history.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    message_lower = user_message.lower()

    print("\n========================")
    print("USER:", user_message)
    print("========================")

    # ==========================
    # FETCH SLOTS
    # ==========================

    if (
        "available slots" in message_lower
        or "show slots" in message_lower
        or "show available slots" in message_lower
        or "what slots are available" in message_lower
    ):

        result = fetch_slots()
        return {
            "tool": "fetch_slots",
            "tool_result": result,
            "response": f"Available slots are {result['available_slots']}"
        }

    # ==========================
    # BOOK APPOINTMENT
    # ==========================

    elif (
    "book" in message_lower
    or "schedule" in message_lower
):
        phone_match = re.search(
        r"\b\d{10}\b",
        user_message
    )

        date_match = re.search(
            r"\d{4}-\d{2}-\d{2}",
            user_message
        )

        time_match = re.search(
            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",
            user_message,
            re.IGNORECASE
        )

        name_match = re.search(
        r"for\s+(.+?)\s+on",
        user_message,
        re.IGNORECASE
        )


        if (
            phone_match
            and date_match
            and time_match
    ):
            name = (
            name_match.group(1).strip()
            if name_match
            else "Patient"
        )

            result = book_appointment(
                name,
                phone_match.group(),
                date_match.group(),
                time_match.group().upper()
            )

            return {
                "tool": "book_appointment",
                "tool_result": result,
                "response": result["message"]
            }

        return {
            "tool": None,
            "response": "Please provide name, phone, date and time."
        }

    # ==========================
    # RETRIEVE APPOINTMENTS
    # ==========================

    elif (
        "show my appointments" in message_lower
        or "show my appointment" in message_lower
        or "retrieve appointments" in message_lower
        or "my bookings" in message_lower
        or "show appointments" in message_lower
        or "appointments" in message_lower
    ):

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        if phone_match:

            result = retrieve_appointments(
                phone_match.group()
            )

            if len(result) == 0:

                return {
                    "tool": "retrieve_appointments",
                    "tool_result": result,
                    "response": "No appointments found."
                }

            appointments_text = ""

            for appt in result:

                appointments_text += (
                    f"Appointment {appt['id']}\n"
                    f"Patient: {appt['name']}\n"
                    f"Date: {appt['date']}\n"
                    f"Time: {appt['time']}\n"
                    f"--------------------\n"
                )

            return {
                "tool": "retrieve_appointments",
                "tool_result": result,
                "response": appointments_text
            }

        return {
            "tool": None,
            "response": "Please provide phone number."
        }

    # ==========================
    # CANCEL APPOINTMENT
    # ==========================

    elif (
    "cancel" in message_lower
    or "delete" in message_lower
    or "remove" in message_lower
):

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        date_match = re.search(
            r"\d{4}-\d{2}-\d{2}",
            user_message
        )

        time_match = re.search(
            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",
            user_message,
            re.IGNORECASE
        )

        if phone_match and date_match and time_match:

            result = cancel_appointment(
                phone_match.group(),
                date_match.group(),
                time_match.group().upper()
            )

            return {
                "tool": "cancel_appointment",
                "tool_result": result,
                "response": result["message"]
            }

        return {
            "tool": None,
            "response": "Please provide phone, date and time."
        }

    # ==========================
    # MODIFY APPOINTMENT
    # ==========================

    elif (
        "move" in message_lower
        or "reschedule" in message_lower
        or "change appointment" in message_lower
    ):

        phone_match = re.search(
            r"\b\d{10}\b",
            user_message
        )

        dates = re.findall(
            r"\d{4}-\d{2}-\d{2}",
            user_message
        )

        times = re.findall(
            r"\d{1,2}(?::\d{2})?\s?(?:AM|PM)",
            user_message,
            re.IGNORECASE
        )

        if (
            phone_match
            and len(dates) >= 2
            and len(times) >= 2
        ):

            result = modify_appointment(
                phone_match.group(),
                dates[0],
                times[0].upper(),
                dates[1],
                times[1].upper()
            )

            return {
                "tool": "modify_appointment",
                "tool_result": result,
                "response": result["message"]
            }

        return {
            "tool": None,
            "response": "Please provide old and new date/time."
        }

    # ==========================
    # END CONVERSATION
    # ==========================

    elif (
        "bye" in message_lower
        or "goodbye" in message_lower
    ):

        result = end_conversation()

        return {
            "tool": "end_conversation",
            "tool_result": result,
            "response": result["message"]
        }

# ==========================
# FALLBACK
# ==========================

    # ==========================
    # LLM FALLBACK
    # ==========================

    intent_data = detect_intent(user_message)

    print("\n====================")
    print("INTENT DATA")
    print(intent_data)
    print("====================\n")

    if intent_data:

        return {
            "tool": "llm",
            "tool_result": intent_data,
            "response": str(intent_data)
        }

    return {
        "tool": None,
        "response": (
            "Please choose one of the following:\n\n"
            "1. Show available slots\n"
            "2. Book appointment\n"
            "3. Show appointments\n"
            "4. Cancel appointment\n"
            "5. Modify appointment"
        )
    }