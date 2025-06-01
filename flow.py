from flask import request
import requests
from firebase_admin import db

SCREEN_RESPONSES = {
    "SEARCH": {"screen": "SEARCH","data": {}},
    "SUMMARY": {
            "screen": "SUMMARY",
            "data": {}
                }
}

# API_URL = "https://api.duniyatech.com/WhatsApp-cloud-api/fatch_date_and_time/"

# def get_data(search):
#     response = requests.get(f"{API_URL}{search}")
#     return response.json()

def get_next_screen(decrypted_body):
    screen = decrypted_body.get("screen")
    data = decrypted_body.get("data")
    action = decrypted_body.get("action")
    flow_token = decrypted_body.get("flow_token")
    print(decrypted_body)

    if action == "ping":
        return {"data": {"status": "active"}}

    if data and "error" in data:
        print("Received client error:", data)
        return {"data": {"acknowledged": True}}

    if action == "INIT":
        # res_date = get_data('date')
        response = SCREEN_RESPONSES["APPOINTMENT"].copy()
        response["data"] = {
            "screen": "APPOINTMENT",
            **SCREEN_RESPONSES["APPOINTMENT"]["data"],
            # "date": res_date,
            "is_date_enabled": True,
            "is_time_enabled": False
        }
        return response

    if action == "data_exchange":
        # if screen == "APPOINTMENT":
        #     if data.get("trigger") == "Date_selected":
        #         # res_time = get_data(data.get("Date_of_appointment"))
        #         response = SCREEN_RESPONSES["APPOINTMENT"].copy()
        #         response["data"] = {
        #             **SCREEN_RESPONSES["APPOINTMENT"]["data"],
        #             # "time": res_time,
        #             "is_time_enabled": True
        #         }
        #         return response

        #     appointment = f"{data.get('Date_of_appointment_0')} at {data.get('Time_Slot_1')}"
        #     details = f"Name: {data.get('Patient_Name_2')}\n" \
        #               f"Guardian: {data.get('Guardian_Name')}\n" \
        #               f"DOB: {data.get('Date_Of_Birth')}\n" \
        #               f"Age: {data.get('Age_3')}\n" \
        #               f"Email: {data.get('Email_4')}\n" \
        #               f"Symptoms: {data.get('Other_Symptoms_5')}\n" \
        #               f"City: {data.get('City')}\n" \
        #               f"Address: {data.get('Address')}"
        #     response = SCREEN_RESPONSES["DETAILS"].copy()
        #     response["data"] = {
        #         **SCREEN_RESPONSES["DETAILS"]["data"],
        #         "appointment": appointment,
        #         "details": details,
        #         **data
        #     }
        #     return response

        if screen == "SEARCH":
            print("summary")
            vendor_key = data.get("screen_0_Vendor_ID")  # Replace with the actual vendor number key you want to find

            # Step 3: Reference the vendor node and get data
            vendor_ref = db.reference(f'vendor/{vendor_key}')
            vendor_data = vendor_ref.get()

            # Step 4: Handle the result
            if vendor_data:
                print(f"Vendor ({vendor_key}) Data:", vendor_data)
                response = SCREEN_RESPONSES["SUMMARY"].copy()
                response["data"] = {
                    "screen_0_Vendor_ID":"12345"
                }
            else:
                print(f"No vendor found with key: {vendor_key}")
                response = SCREEN_RESPONSES["SEARCH"].copy()
            
            return response

    print("Unhandled request body:", decrypted_body)
    return {"error": "Unhandled request"}, 400

