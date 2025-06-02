import json
import base64
import hmac
import hashlib
from flask import Flask, request, Response
from encryption import decrypt_request, encrypt_response, FlowEndpointException
from flow import get_next_screen
from flask import jsonify
import firebase_admin
import requests
from firebase_admin import credentials, db
from datetime import datetime
from flask_cors import CORS
import time
from collections import defaultdict
from pdf import generate_pdf
from pdf2 import generate_invoice
from db import get_all_products_stock,stock_movement,create_product
import re

app = Flask(__name__)
CORS(app)

PORT = 5000
PASSPHRASE = "password"
APP_SECRET = "33c7ec9aa719ba8350b67811bf64e47b"
PRIVATE_KEY = """-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFJDBWBgkqhkiG9w0BBQ0wSTAxBgkqhkiG9w0BBQwwJAQQd6lQS6B5yB3w35l9
nsF+QAICCAAwDAYIKoZIhvcNAgkFADAUBggqhkiG9w0DBwQIzrJNJZQ76F4EggTI
TucgxOwQlFeqJIv8PNepQOToYpWZyYR6w8KOhc0T3N/9bI6dpLUSEuW5FbcM5zmx
33CsMfEqWuEnaALuhxWJfFWEQEYHyJMXgaFvW9k6W14ZmyTaW3S3rwKThsYWaZcc
PLx/stu0eaRDde8sBIi6tN8ujPJofpFFC7vo4mKNN46lE+CPwPNTeu/sRogdOv74
KS9LFxYt44bEooa4A2WCKd5EzyefN6eLx1j5Rpz9mcHBRBvwGEy211HduxqPXamc
GxqVdgUMz3a+MXCqhqBs4abhUw5jPhSwsxli+xNIAti7g4dgfTyuzI9v+PR6pnOL
xJrFbkpd0mvpvTwhufVB0k8zbJwDjDnb8DlTf75PAApRCJx6sUw7BlJEy43DHtzr
xMVWdd6qiMAroV50W/HHXMW649VbqWQPwdcoxE4OJykMIDZ+2orXrfh/PoVBvQoE
IBfBgWyuaBxAF/+2filulkpLwMHjEuxb8wssCA8gNnDNsHrlVMlFtdobUxHHE8ID
efviJVG/TXp4jcr8McF0mZBbP1FGKb2kuDhcBTGhBQgjJA7Xba0macAfXnmrJuGl
tPQshid4tO1GFuKkx0dWbTwlmcWgg4a3V++2+om2dRQ//NeyOEgG8/3hXArx699g
Jufjg8v7lQcMyYYwxEPxfNYjnuU5DeJn+ebgVP9vQvY+mLIA0arIj2RUhLBZgWZi
lHvlqI2ofXWpkJpuKqBYjOH7Vo6hkDQjo6h4uaS0YouuY7+di7UxE8zt0f/ODLWn
lYIqCJ9tvFPXkTJ9H9z3K8cA2QLgiZcvJTkHBMq5sKslsBb+iMiTwub+ka6Q0TM5
0EhJE4qQHMJKDtsrr0Qy6kXA7NlK3sLWMcFeNSmBUEW+K7GruvwZwAzWd3GVqjwo
XYvxjRFu82Yp5Ric1Q2/+VNK27gYD/ONcfpqrsvZo6G6bAVQ1vhLcqBdDDslyEbP
ix08SunoGCNzIGLpJ5j/0bDaz1RIfMvRwwtiNldhRHEv+q44AU9Hr5TdzGCNO9Sf
xMgUArYdObqAAwTUhlcM9Py0ZLl0Xvvh3lMjGUnXHvykBi8gNvcm1BZkQZTANXFJ
GG35B3+Q2oRtePTQxT1cgV4XOfM4NexOa3RPKbt4qnqcyCgYVtZa0nQW3JNMbbox
t9kP+8N7IjZMnxDwEG9WSc44GzCGK8kY3G/yxePnPCd8DVP6O2W1+uzka0mjsGj5
93U4wqEC3YwAjuuJXeX7pDe4ehyh1wF3aer4sSZbJMRnuPDWqMyscHjRqx+8K9ZR
2Abm/Uo8fjO3lKWTsvUfrf6brpxwlysHli6hq+i7oWIs5LRxwAIrsy8sx5gLTNrB
/sBz7xBXHXUoQ17LC/EPCyCuNDdCCTAy2zCSTzypKQxRVMRDldyC8xMOmc4GWYrq
8yu1uEYpD3HHA7eQXm+pwcwkaU9lgI5XyUhRuyuFucDpuyIzjuJCGLZsPw3XK8B/
iUoHbXrTPt42+OKdwMggVpsp1Ll03ogh69h0iE7zDxz9O9SzNEMFqunNj+G09ISx
Q0IKi7TQUwfWzilTUSEpaUXBpSL+C9RiOIrnd0h89kbzDEqU2PE6l4GuRrtvIuLK
k3aT53ltPKzgI5Aa/w2fVTCPoDW9kI2R
-----END ENCRYPTED PRIVATE KEY-----"""




        
@app.route("/", methods=["POST"])
def handle_request():
    if not PRIVATE_KEY:
        raise Exception('Private key is empty. Please check your environment variable "PRIVATE_KEY".')
    
    if not is_request_signature_valid(request):
        return Response(status=432)
    
    try:
        decrypted_request = decrypt_request(request.json, PRIVATE_KEY, PASSPHRASE)
    except FlowEndpointException as err:
        return Response(status=err.status_code)
    except Exception as err:
        print(err)
        return Response(status=500)
    
    aes_key_buffer = decrypted_request["aesKeyBuffer"]
    initial_vector_buffer = decrypted_request["initialVectorBuffer"]
    decrypted_body = decrypted_request["decryptedBody"]
    
    print("Decrypted Request:", decrypted_body)
    
    screen_response = get_next_screen(decrypted_body)
    print("Response to Encrypt:", screen_response)
    
    return encrypt_response(screen_response, aes_key_buffer, initial_vector_buffer)

@app.route("/", methods=["GET"])
def home():
    return "<pre>Nothing to see here.\nCheckout README.md to start.</pre>"

def is_request_signature_valid(req):
    if not APP_SECRET:
        print("Warning: App Secret is not set. Please add it in the .env file.")
        return True
    
    signature_header = req.headers.get("x-hub-signature-256")
    if not signature_header:
        print("Error: Missing x-hub-signature-256 header")
        return False
    
    signature_buffer = bytes.fromhex(signature_header.replace("sha256=", ""))
    raw_body = req.data
    if not raw_body:
        print("Error: req.data is undefined. Ensure middleware is set up correctly.")
        return False
    
    digest = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).digest()
    
    if not hmac.compare_digest(digest, signature_buffer):
        print("Error: Request Signature did not match")
        return False
    
    return True




# Firebase setup

cred = credentials.Certificate('/etc/secrets/serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://poultryhub-5242a-default-rtdb.asia-southeast1.firebasedatabase.app'
})

WHATSAPP_ACCESS_TOKEN = "EACH6PXeLx50BO39th5RhjYBaIEm9WN1DeqyKTanvAM50PQ2cK10GrtVZBZCJiEH5ke8481Dzit3lhhAFB8ZCqZCxhJOIRHTeORvGdiMYYeXWIQRBDjq874W0SvrYqaTP9zsgycuRZCbx4RZAA5SzS2CdEmULMjFsuJBZCboc8cIPPu4oqmzIr178N0fkrQftXQ4uQZDZD"  # Keep secure in .env
PHONE_NUMBER_ID = "638286416039346"
RECIPIENT_NUMBER = "919131037870"
headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

@app.route("/create_product", methods=["POST"])   
def create_product_route():
    return create_product(request.get_json())

@app.route("/update_stock", methods=["POST"])   
def update_stock_route():
    return stock_movement(request.get_json())

@app.route("/get_all_product", methods=["GET"])   
def get_products():
    return get_all_products_stock()

@app.route("/get_vendor/<string:id>", methods=["GET"])   
def get_vendor_id(id):
    vendor_ref = db.reference(f'vendor/{id}')
    vendor_data = vendor_ref.get()
    return jsonify(vendor_data),200

@app.route("/stock_movement", methods=["GET"])  
def get_stock_movement():
    vendor_ref = db.reference(f'/stock_movements')
    vendor_data = vendor_ref.get()
    return jsonify(vendor_data),200
    

@app.route('/webhook', methods=['POST'])
def webhook():
    print('Webhook triggered')
    data = request.get_json()
    print(json.dumps(data, indent=2))

    entry = data.get('entry', [{}])[0]
    changes = entry.get('changes', [{}])[0]
    value = changes.get('value', {})

    message_info = value.get('messages', [{}])[0]
    contact_info = value.get('contacts', [{}])[0]

    from_number = message_info.get('from')
    body = message_info.get('text', {}).get('body', '')
    body = body.lower()
    msg_type = message_info.get('type')
    timestamp = message_info.get('timestamp')
    name = contact_info.get('profile', {}).get('name')

    if body and body.split()[0] == "ap":
        vendor=body.split()[1]
        type='sell'
        invoice='0000'
        if vendor:
            old_user_send(from_number,vendor,invoice,type)
        else:
            message(from_number,"No vendor found")
    if body and body.split()[0] == "purchase":
        type='purchase'
        vendor=body.split()[1]
        invoice=body.split()[2].uppercase()
        if vendor:
            old_user_send(from_number,vendor,invoice,type)
        else:
            message(from_number,"No vendor found")
        
    if body and body.split()[0] == "bill":
        vendor=body.split()[1]
        if vendor:
            print("Extracted vendor:",vendor)
            vendor_ref = db.reference(f'vendor/{vendor}')
            vendor_data = vendor_ref.get()
            print(vendor_data)
            if vendor_data:
                shop(vendor_data,from_number,vendor,timestamp)
            else:
                send_flow(from_number,"create_vendor")
        else:
            print("No number found")
        
    if body == "vendor" or body == "create vendor" :
        send_flow(from_number,"create_vendor")
    if body == "ledger":
        send_flow(from_number,"get_ledger")
    # if body == "search" or body == "find" :
    #     send_flow(from_number,"search_vendor")
    if body == "add" :
        send_flow(from_number,"add_product")

    if msg_type == "interactive" and message_info.get('interactive', {}).get('type') == "nfm_reply":
        res = message_info.get('interactive', {}).get('nfm_reply', {}).get('response_json')
        print(res)
        parsed = json.loads(res)
        if parsed.get("role") == 'shop':
        #    shop(parsed,from_number,timestamp)
           shop(parsed,from_number,timestamp)
        elif parsed.get("role") == "create_vendor":
           create_vendor(parsed,from_number,timestamp)
        elif parsed.get("role") == "vendor":
            print("vendor Details")
        elif parsed.get("role") == "pdf":
            base_ref = db.reference('ledger')
            ledgers = base_ref.get() or {}
            generate_pdf(ledgers,parsed,from_number)
        elif parsed.get("role") == "add":
            print("vendor Details")
            ref = db.reference('/products').push()
            product_data = {
                'product_id': ref.key,
                **parsed
            }
            ref.set(product_data)
            message(from_number,'Product Added Successfully')
        else :
            print("None")
    if msg_type == "interactive" and message_info.get('interactive', {}).get('type') == "button_reply":
        res = message_info.get('interactive', {}).get('button_reply', {}).get('id')
        type=res.split()[0]
        vendor=res.split()[1]
        invoice=res.split()[2]
        if res:
            send_template(from_number,type,vendor,invoice)
        else:
            print("No vendor found")
    return ''

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    VERIFY_TOKEN = 'sadapoorna'
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print('WEBHOOK_VERIFIED')
        return challenge, 200
    else:
        return '', 403

@app.route('/add_product', methods=['POST'])
def add_product():
    try:
        data = request.get_json()  # ✅ correct way
        type = data.get('type', '')
        invoice = data.get('invoice', '')
        items = data.get("product", [])
        total = round(sum(float(item.get("total_qty", 0)) * float(item.get("price", 0)) for item in items),2)
        if type=='purchase':
            new_order_ref = db.reference(f'purchase/{invoice}')
            new_order_ref.set({
                **data,
                'total':total,
                'id': invoice,
                'createdAt': int(time.time() * 1000)
            })
            ledger_ref = db.reference('/ledger').push()
            ledger_data = {
                'invoice_id': invoice,
                'id':ledger_ref.key,
                'date': datetime.now().strftime("%Y-%m-%d"),
                'dr':[{'ledger':'purchase account','particular':'Goods Purchased','amt':total}],
                'cr':[{'ledger':'credit account','particular':'Goods Purchased','amt':total}],
                'vendor_id': data.get('vendor_id', ''),
                'total_amount': total,
                'vendor_name': data.get('vendor_name', 'Unknown')
            }

            # Save to /ledger with auto-generated key
            ledger_ref.set(ledger_data)
        else:
            new_order_ref = db.reference('weborders').push()
            new_order_ref.set({
                **data,
                'id': new_order_ref.key,
                'createdAt': int(time.time() * 1000)
            })

        print("order saved")
        stock_movement(data)
        to = data['created_by']
        message(to,'Saved Sucessfully')
        return jsonify({'message': 'Order saved', 'id': new_order_ref.key}), 200
    except Exception as e:
        print('Error saving order:', e)
        return jsonify({'error': 'Internal Server Error'}), 500


@app.route('/test-firebase', methods=['GET'])
def test_firebase():
    try:
        test_ref = db.reference('testConnection')
        test_ref.set({ 'connectedAt': int(time.time() * 1000) })
        return jsonify({'message': '✅ Firebase connected and write successful'}), 200
    except Exception as e:
        print('❌ Firebase connection failed:', e)
        return jsonify({'error': 'Firebase connection failed'}), 500

def send_flow(from_number,flow_name):
    try:
        send_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
        headers["Content-Type"] = "application/json"
        message_payload = { 
            "messaging_product": "whatsapp", 
            "to": from_number, 
            "type": "template", 
            "template": { 
                "name": flow_name, 
                "language": { "code": "en" },
                "components": [
                    {
                        "type": "header"
                    },
                    {
                        "type": "body",
                        "parameters": []
                    },
                    {
                        "type": "button",
                        "sub_type": "flow",  
                        "index": "0"  
                    }
                ]
            } 
        }


        send_resp = requests.post(send_url, headers=headers, json=message_payload)
        send_resp.raise_for_status()
        print(flow_name,"flow sended")
        # return jsonify({"message": "Invoice sent via WhatsApp"}), 200
    except Exception as e:
        print(flow_name,'Error sending flow:', e)
        # return jsonify({'error': 'Internal Server Error'}), 500

def send_template(from_number,type,vendor,invoice):
    send_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers["Content-Type"] = "application/json"
    message_payload = {
        "messaging_product": "whatsapp",
        "to": from_number,
        "type": "template",
        "template": {
            "name": "sadapoorna_ecom",
            "language": {
            "code": "en"
            },
            "components": [
            {
                "type": "header",
                "parameters": [
                {
                    "type": "image",
                    "image": {
                    "link": "https://sadapoorna.netlify.app/logo.png"
                    }
                }
                ]
            },
            {
                "type": "body",
                "parameters": []
            },
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [
                {
                    "type": "text",
                    "text": f"{type}/{vendor}/{from_number}/{invoice}"
                }
                ]
            }
            ]
        }
        }


    send_resp = requests.post(send_url, headers=headers, json=message_payload)
    send_resp.raise_for_status()
    # print("It's OK")
    # return jsonify({"message": "Invoice sent via WhatsApp"}), 200

@app.route("/invoice", methods=["GET"])   
def testing():
    base_ref = db.reference('ledger')
    ledgers = base_ref.get() or {}
    return generate_pdf(ledgers)

def shop(parsed,from_number,vendor,timestamp):
    try:
        new_order_ref = db.reference('confirmorders').push()
        new_order_ref.set({
            'res': parsed,
            'fromNumber': from_number,
            'timestamp': timestamp,
            'id': new_order_ref.key 
        })
        
        # Reference the weborders collection
        weborders_ref = db.reference('weborders')
        weborders = weborders_ref.get()
        # dt_object = datetime.fromtimestamp(int(timestamp))
        dt_object = datetime.fromtimestamp(int(timestamp))
        target_date = dt_object.date().isoformat()
        matching_orders = []
        print(vendor,target_date,timestamp)

        for key, order in weborders.items():
            vendor_id = str(order.get('vendor_id'))
            date_str = order.get('date')
            
            # Extract just the date part and keep full datetime for sorting
            if date_str:
                try:
                    full_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    only_date = full_date.date().isoformat()
                except ValueError:
                    continue
                
                if vendor == vendor_id and only_date == target_date:
                    matching_orders.append({
                        'id': key,
                        **order,
                        '_parsed_datetime': full_date  # temp key for sorting
                    })

        # Aggregate qty per product_id
        
        aggregated_products = {}

        for order in matching_orders:
            product_list = order.get('product', [])
            for product in product_list:
                product_id = product.get('product_id')
                try:
                    qty = int(product.get('qty', 0))
                except:
                    qty = 0

                if product_id:
                    if product_id not in aggregated_products:
                        aggregated_products[product_id] = {
                            'product_id': product_id,
                            'name': product.get('name', ''),
                            'price': product.get('price', ''),
                            'total_qty': qty
                        }
                    else:
                        aggregated_products[product_id]['total_qty'] += qty

        # Convert dict to list
        merged_products = list(aggregated_products.values())

        # Optional: Sort by product name
        merged_products.sort(key=lambda x: x['name'])
        print("Latest matching order:")
        # generate_pdf({'product':merged_products,**parsed},from_number)
        generate_invoice({'product':merged_products,**parsed},from_number)
        
    except Exception as e:
        print('Error saving order:', e)
        # return jsonify({'error': 'Internal Server Error'}), 500

def create_vendor(parsed,from_number,timestamp):
    print("Create Vendor")
    text = parsed.get("name")  # Vendor name
    initials = ''.join(word[0] for word in text.split()).lower()

    base_ref = db.reference('vendor')
    all_vendors = base_ref.get() or {}

    # Find all vendor keys that start with the initials (e.g., AE, AE1, AE2, ...)
    matching_keys = [key for key in all_vendors.keys() if key.startswith(initials)]

    # Extract the suffix numbers (e.g., AE -> 0, AE1 -> 1, AE2 -> 2)
    suffixes = []
    for key in matching_keys:
        suffix = key[len(initials):]
        if suffix == '':
            suffixes.append(0)
        elif suffix.isdigit():
            suffixes.append(int(suffix))

    # Determine the next available number
    next_suffix = max(suffixes, default=-1) + 1

    # Build final vendor key
    final_key = initials if next_suffix == 0 else f"{initials}{next_suffix}"

    print("Final vendor key to store:", final_key)

    # Save to Firebase under the unique key
    vendor_ref = db.reference(f'vendor/{final_key}')
    vendor_ref.set({
         **parsed,
        'fromNumber': from_number,
        'timestamp': timestamp,
        'vendor_id':final_key

    })
    print(f"Vendor {final_key} created.")
    message(from_number,f'Created Vendor ID:{final_key.upper()} ')

def message(from_number,msg):
    send_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers["Content-Type"] = "application/json"
    data={
        "messaging_product": "whatsapp",
        "to": from_number,
        "type": "text",
        "text": {
            "body": msg
        }
        }
    send_resp = requests.post(send_url, headers=headers, json=data)
    send_resp.raise_for_status()


def old_user_send(from_number,vendor_id,invoice,type):
    send_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

# Function to send buttons in batches of 3
    def send_whatsapp_buttons(to_number, vendor_id):
        # for i in range(0, len(buttons_list), 3): 
        vendor_ref = db.reference(f'vendor/{vendor_id}')
        vendor_data = vendor_ref.get()
        if vendor_data:
            payload = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": to_number,
    "type": "interactive",
    "interactive": {
        "type": "button",
        "body": {
            "text": f"ID: {vendor_id}-{vendor_data.get('name')}"
        },
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"{type} {vendor_id} {invoice}",
                        "title": "Yes"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "No",
                        "title": "No"
                    }
                }
            ]
        }

    }
}


            response = requests.post(send_url, headers=headers, json=payload)
            return "OK", 200
        else:
            message(to_number,"No vendor found")
            return "Error",400


# Send multiple messages with 3 buttons per message
    send_whatsapp_buttons(from_number, vendor_id)
    return "OK", 200

if __name__ == "__main__":
    app.run(port=PORT, debug=True)
