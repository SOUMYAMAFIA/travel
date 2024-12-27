from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging
import requests
import json
from io import BytesIO
from azure.storage.blob import BlobServiceClient
import azure.functions as func

# Placeholders for Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=convergentfreetier95d9;AccountKey=HQCkQABXEIWGgozNSLx28KKTr7PhWIJgGr1gdoADuIHG5FMi/Up4wX422SjmhGYFqHIGaeUd6M04+AStgRRp6A==;EndpointSuffix=core.windows.net"
AZURE_STORAGE_CONTAINER_NAME = "cts-travel-agent-logs"

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPT-4 API Configuration
OPENAI_API_KEY = "BloT2ynzgKDblx6tBt7ox3U7k9ynsMj945S5BWtgOaAa0Obj5JIOJQQJ99ALACHYHv6XJ3w3AAABACOGwz5W"
OPENAI_API_ENDPOINT = "https://cts-travel-agent.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-08-01-preview"

# Add a root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Travel Booking Assistant!"}

# Handle favicon requests
@app.get("/favicon.ico")
def favicon():
    return {"message": "Favicon not implemented."}

# Prompt Configuration
prompt = """You are TaskMeister, the most advanced Travel Booking Assistant.
You are tasked with extracting travel details from an email and returning the information in the specified JSON format. The email may be in any of the following languages: English, Arabic, Chinese (Simplified), Bangla, Tamil, or Hindi. The extracted information must include the following fields in the exact JSON format specified below. If any field is missing, leave it as null, "", or apply default values as necessary.

The email content will include details like travel dates, source and destination city/country (you may have to provide the IATA code for the airports using your domain knowledge), number of passengers, preferences, and more. Please extract these details and format them as follows:
# IMPORTANT: If any information is Missing or not Present, Leave the information Blank like a blank string if datatype is string and similarly

JSON Format:
{
  "srchType": <integer (Type of search: 1 for one-way, 2 for round-trip)>,
  "frmAirport": <string (IATA code for the departure airport, e.g., "MAA")>,
  "toAirport": <string (IATA code for the destination airport, e.g., "DXB")>,
  "strDeptDate": <string (Departure date in DD/MM/YYYY format, e.g., "01/01/2025")>,
  "strRetDate": <string (Return date in DD/MM/YYYY format, e.g., "31/03/2025")>,
  "adtCnt": <integer (Number of adults, e.g., 2)>,
  "chldCnt": <integer (Number of children, e.g., 1)>,
  "infntCnt": <integer (Number of infants, e.g., 0)>,
  "classType": <string (Class of travel: "Y" for Economy, "C" for Business, "F" for First Class)>,
  "prefAirlineList": [<array of strings (Preferred airlines using IATA codes, e.g., ["EK", "AI"])>],
  "prefNonStop": <boolean (True if non-stop flights are preferred, e.g., true)>,
  "deptTime": <integer (Preferred departure time: 1 for Before 6 AM, 2 for 6 AM to 12 PM, 3 for 12 PM to 5 PM, 4 for After 6 PM)>,
  "retTime": <integer (Preferred return time: 1 for Before 6 AM, 2 for 6 AM to 12 PM, 3 for 12 PM to 5 PM, 4 for After 6 PM)>,
  "nearByAirport": <boolean (True if nearby airports should be considered, e.g., true)>,
  "flexiDays": <boolean (True if travel dates are flexible, e.g., true)>,
  "travellers": [
    {
      "fname": <string (First name of the traveller, e.g., "Rajesh")>,
      "lname": <string (Last name of the traveller, e.g., "Kumar")>,
      "sname": <string (Short name/nickname, e.g., "Raj")>,
      "dob": <string (Date of birth in DD/MM/YYYY format, e.g., "01/01/1990")>,
      "isLead": <boolean (True if this traveller is the lead traveller, e.g., true)>,
      "nationalitycode": <string (Country code, e.g., "IN" for India)>,
      "countryOfResidenceCode": <string (Country code for the country of residence, e.g., "IN")>,
      "passportNo": <string (Passport number, e.g., "ZBY756778")>,
      "passExp": <string (Passport expiration date in DD/MM/YYYY format, e.g., "31/03/2025")>,
      "mobcntrycode": <string (Mobile country code, e.g., "91" for India)>,
      "mobile": <string (Mobile number, e.g., "886767892")>,
      "email": <string (Email address, e.g., "demo@demo.com")>,
      "city": <string (City of residence, e.g., "Chennai")>,
      "state": <string (State of residence, e.g., "Tamil Nadu")>,
      "country": <string (Country of residence, e.g., "India")>,
      "salutation": <string (Salutation, e.g., "Mr")>,
      "age": <integer (Age of the traveller, e.g., 25)>,
      "gender": <string (Gender, e.g., "M" for Male, "F" for Female)>,
      "passportIssuingGovt": <string (Country of passport issuance, e.g., "IN" for India)>,
      "postalCode": <string (Postal code, e.g., "2332")>,
      "addressLine": [<string (Address line 1, e.g., "123 Main Street")>, <string (Address line 2, e.g., "Apt 4B")>, <string (Address line 3, e.g., "City Center")>],
      "seatPreference": <string (Preferred seat, e.g., "window" or "aisle")>,
      "mealPreference": <string (Meal preference, e.g., "Veg Meal")>
    },
    {
      "fname": <string (First name of the traveller, e.g., "Rajesh")>,
      "lname": <string (Last name of the traveller, e.g., "Kumar")>,
      "sname": <string (Short name/nickname, e.g., "Raj")>,
      "dob": <string (Date of birth in DD/MM/YYYY format, e.g., "01/01/1990")>,
      "isLead": <boolean (True if this traveller is the lead traveller, e.g., true)>,
      "nationalitycode": <string (Country code, e.g., "IN" for India)>,
      "countryOfResidenceCode": <string (Country code for the country of residence, e.g., "IN")>,
      "passportNo": <string (Passport number, e.g., "ZBY756778")>,
      "passExp": <string (Passport expiration date in DD/MM/YYYY format, e.g., "31/03/2025")>,
      "mobcntrycode": <string (Mobile country code, e.g., "91" for India)>,
      "mobile": <string (Mobile number, e.g., "886767892")>,
      "email": <string (Email address, e.g., "demo@demo.com")>,
      "city": <string (City of residence, e.g., "Chennai")>,
      "state": <string (State of residence, e.g., "Tamil Nadu")>,
      "country": <string (Country of residence, e.g., "India")>,
      "salutation": <string (Salutation, e.g., "Mr")>,
      "age": <integer (Age of the traveller, e.g., 25)>,
      "gender": <string (Gender, e.g., "M" for Male, "F" for Female)>,
      "passportIssuingGovt": <string (Country of passport issuance, e.g., "IN" for India)>,
      "postalCode": <string (Postal code, e.g., "2332")>,
      "addressLine": [<string (Address line 1, e.g., "123 Main Street")>, <string (Address line 2, e.g., "Apt 4B")>, <string (Address line 3, e.g., "City Center")>],
      "seatPreference": <string (Preferred seat, e.g., "window" or "aisle")>,
      "mealPreference": <string (Meal preference, e.g., "Veg Meal")>
    },
    .
    .
  ],
  "detected_language": <string (The detected language of the email, e.g., "English", "Arabic", "Chinese Simplified", "Tamil", "Hindi", "Bengali", "Other")>
}
"""
blob_json = {
    "STATUS": "ERROR"
}

# Request model
class QueryModel(BaseModel):
    user_query: str

# GPT-4 API Call
def call_genai_api(user_query: str):
    url = OPENAI_API_ENDPOINT
    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_query}
    ]
    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error during API call: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch response from GPT-4 API")

def upload_to_azure_blob(file_name, data):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
        blob_client = container_client.get_blob_client(file_name)

        # Convert dictionary to JSON string
        if isinstance(data, dict):
            data = json.dumps(data, indent=4)  # Convert dict to JSON string for uploading

        # Use BytesIO to upload data
        with BytesIO(data.encode('utf-8')) as data_stream:
            blob_client.upload_blob(data_stream, overwrite=True)

        logging.info(f"File {file_name} uploaded successfully to Azure Blob Storage.")
    except Exception as e:
        logging.error(f"Failed to upload file to Azure Blob Storage: {str(e)}")
        raise

# Endpoint to process travel booking entities
@app.post("/get_travel_booking_entities")
def get_travel_booking_entities(query: QueryModel):
    user_query = query.user_query
    try:
        gpt_response = call_genai_api(user_query)
        gpt_response = gpt_response[7:-3].replace("\n", "").replace("\\n", "")
        final_output = json.loads(gpt_response)
        blob_json["STATUS"] = "OK"
        blob_json["LANGUAGE"] = final_output.get("detected_language", "Unknown")
    except Exception as e:
        blob_json["STATUS"] = "ERROR"
        blob_json["ERROR"] = str(e)
        blob_json["LANGUAGE"] = "FAILURE"
        final_output = blob_json.copy()

    # Save response to a file
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = f"{blob_json['LANGUAGE']}_{timestamp}.txt"
    upload_to_azure_blob(file_name, blob_json)

    return final_output
