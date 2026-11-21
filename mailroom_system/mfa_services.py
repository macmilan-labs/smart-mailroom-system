import os
from logger import log_otp, log_otp_error

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "14155238886")

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

def send_whatsapp_otp(phone_number: str, otp: str, parcel_id: str) -> bool:
    """Send OTP via WhatsApp using Twilio. Falls back to terminal logging if not configured."""
    log_otp("Generated")

    if not (TWILIO_AVAILABLE and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_NUMBER):
        log_otp("Sent (or fallback)")
        print(f"\n  [OTP FALLBACK] WHATSAPP → +{phone_number}: Parcel {parcel_id} arrived. OTP: {otp}\n")
        return True

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # Twilio whatsapp requires numbers in the format whatsapp:+<country_code><number>
        if not phone_number.startswith("+"):
            phone_number = "+" + phone_number
            
        message = client.messages.create(
            from_=f"whatsapp:+{TWILIO_WHATSAPP_NUMBER}",
            body=f"Your parcel '{parcel_id}' has arrived! Your secure collection OTP is: {otp}. Valid for 5 minutes.",
            to=f"whatsapp:{phone_number}"
        )
        log_otp("Sent (or fallback)")
        return True
    except Exception as e:
        log_otp_error(f"Failed to send Twilio message", e)
        log_otp("Sent (or fallback)")
        print(f"\n  [OTP FALLBACK ERROR] WHATSAPP → +{phone_number}: Parcel {parcel_id} arrived. OTP: {otp}\n")
        return True
