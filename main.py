import os
print("--- AI Agent Script is now Running ---")
from twilio.rest import Client
from airtable import Airtable
from dotenv import load_dotenv

# Load all credentials from the .env file
load_dotenv()

# Configuration: Credentials fetching
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
ELEVENLABS_AGENT_ID = os.getenv('ELEVENLABS_AGENT_ID')

# Initialize API Clients
client = Client(TWILIO_SID, TWILIO_AUTH)
airtable = Airtable(
    os.getenv('AIRTABLE_BASE_ID'), 
    os.getenv('TABLE_NAME'), 
    api_key=os.getenv('AIRTABLE_API_KEY')
)

def start_multilingual_ai_call(debtor_number, manager_number):
    """
    Triggers an outbound call that connects the debtor to the 
    ElevenLabs Multilingual v2 Agent with automatic language detection.
    """
    # TwiML with ConversationRelay for real-time Voice AI
    # 'language_code="auto"' ensures the AI responds in the user's language.
    twiml_content = f"""
    <Response>
        <Connect>
            <ConversationRelay 
                url="wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"
                language_code="auto"
            />
        </Connect>
    </Response>
    """
    
    try:
        call = client.calls.create(
            twiml=twiml_content,
            to=debtor_number,
            from_=TWILIO_NUMBER
        )
        print(f"Successfully started Multilingual AI call to: {debtor_number}")
        airtable.update(record['id'], {'Status': 'Called'})
        return call.sid
    except Exception as e:
        print(f"Failed to initiate call to {debtor_number}: {e}")
        return None

def transfer_to_manager(call_sid, manager_number):
    """
    Function to bridge the call to a human manager if the AI triggers an escalation.
    Includes a professional fallback message if the manager doesn't pick up.
    """
    try:
        client.calls(call_sid).update(
            twiml=f"""
            <Response>
                <Say>Please wait while I connect your call to our manager for further assistance.</Say>
                <Dial>{manager_number}</Dial>
            </Response>
            """
        )
    except Exception:
        # Fallback message if technical error or manager busy
        client.calls(call_sid).update(
            twiml="<Response><Say>We apologize, but the manager is unavailable due to a technical interruption. We will call you back shortly.</Say></Response>"
        )

# Main Logic: Fetching and Processing Airtable Records
try:
    records = airtable.get_all(view='Grid view')
    print(f"Total records found: {len(records)}")
    for record in records:
        fields = record.get('fields', {})
        current_status = fields.get('Status')
        print(f"Checking record... Status is: {current_status}")
    
        # Only process if status is 'Pending'
        if fields.get('Status') == 'Pending':
            debtor_phone = fields.get('Phone_number')
            manager_phone = fields.get('MANAGER_NUMBER') # Make sure this matches Airtable column name exactly
            
            if debtor_phone and manager_phone:
                start_multilingual_ai_call(debtor_phone, manager_phone)
            else:
                print(f"Missing phone numbers for record ID: {record['id']}")

except Exception as e:
    print(f"Error connecting to Airtable: {e}")