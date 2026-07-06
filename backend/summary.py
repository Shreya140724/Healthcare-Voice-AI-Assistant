import ollama
from datetime import datetime

from tools import retrieve_appointments


def generate_summary(
    conversation_history,
    phone=None
):

    history_text = ""

    for item in conversation_history:

        history_text += (
            f"{item['role']}: "
            f"{item['content']}\n"
        )

    appointments = []

    if phone:

        appointments = retrieve_appointments(
            phone
        )

    prompt = f"""
Create a concise call summary.

Conversation:

{history_text}

Appointments:

{appointments}

Return:

1. Conversation Summary
2. User Preferences
3. Next Actions
"""

    response = ollama.chat(
    model="phi3:mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return {
        "summary": response["message"]["content"],
        "appointments": appointments,
        "timestamp": timestamp
    }
