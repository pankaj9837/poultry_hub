from flask import Flask, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
import requests
from datetime import datetime
import io
from num2words import num2words
from firebase_admin import credentials, db
from flask import Flask, request, jsonify


WHATSAPP_ACCESS_TOKEN = "EACH6PXeLx50BO39th5RhjYBaIEm9WN1DeqyKTanvAM50PQ2cK10GrtVZBZCJiEH5ke8481Dzit3lhhAFB8ZCqZCxhJOIRHTeORvGdiMYYeXWIQRBDjq874W0SvrYqaTP9zsgycuRZCbx4RZAA5SzS2CdEmULMjFsuJBZCboc8cIPPu4oqmzIr178N0fkrQftXQ4uQZDZD"  # Keep secure in .env
PHONE_NUMBER_ID = "638286416039346"
headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}



def draw_header(c,order):
    width, height = A4
      # Add local logo (top-left corner)
    logo_path = "logo.jpeg"  # ← Replace with your actual filename
    logo_width = 70
    logo_height = 70
    c.drawImage(logo_path, 80, height - logo_height - 20, width=logo_width, height=logo_height, mask='auto')

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 35, "INVOICE")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 50, "NEW POULTRY HUB")

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, height - 65, "Address: Shop No-27, Ground Floor, Model Town, Phase-3")
    c.drawCentredString(width / 2, height - 75, "Bathinda ,PUNJAB, Pin 151001")

    # c.setFont("Helvetica-Bold", 10)
    # c.drawCentredString(width / 2, height - 90, "GSTIN : 03ASPPK7498B1ZH")

    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, height - 85, "Tel. : 07554 004526   email : newpoultryhub@gmail.com")

    # Draw rectangles for details
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)

    height+=160

    # Billing and Shipping Details Box
    c.rect(20, height - 380, width - 40, 125)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(25, height - 270, "Billed to :")
    c.setFont("Helvetica", 10)
    c.drawString(25, height - 285, order.get('name',''))
    c.drawString(25, height - 300, order.get('address',''))
    c.drawString(25, height - 315, order.get('city',''))
    c.drawString(25, height - 330, f"State : {order.get('state','')}")
    c.drawString(25, height - 345, f"Mobile No : {order.get('number','')}") 
    c.line(width/2, height - 380, width/2, height - 255)
    x=width/2
    c.drawString(x+5, height - 270, "Invoice No : NPH1001")
    today = datetime.today()
    c.drawString(x+5, height - 285, f"Date of Invoice : {today.strftime("%d-%m-%Y")}")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x+5, height - 300, "Place of Supply:")
    c.setFont("Helvetica", 10)
    c.drawString(x+5, height - 315, order.get('name',''))
    c.drawString(x+5, height - 330, order.get('address',''))
    c.drawString(x+5, height - 345, order.get('city',''))
    c.drawString(x+5, height - 360, f"State of Supply : {order.get('state','')}")
    c.drawString(x+5, height - 375, f"Mobile No : {order.get('number','')}")

    return height

def draw_items_table(c, order,Total, x_start=20, y_start=600):
    width,height=A4
    items = order.get("product", [])
    total_rows = 12
    col_widths = [30, 250, 68, 68, 68, 68] 
    headers = ['S.N', 'Description of Goods', 'Qty.', 'Unit', 'Price', 'Amount']
    
    row_height = 20
    total_height = row_height * (total_rows + 2)  # +1 for header
    y = y_start

    # Vertical column lines
    x = x_start
    for width in col_widths:
        c.line(x, y, x, y - total_height)
        x += width
    c.line(x, y-20, width-60, y-20)  # Final bottom edge
    c.line(x, y, x, y - total_height)  # Final right edge
    # Header row
    c.setFont("Helvetica-Bold", 10)
    x = x_start
    for i, header in enumerate(headers):
        c.drawString(x + 2, y - row_height + 5, header)
        x += col_widths[i]

    y -= row_height

    # Data rows
    c.setFont("Helvetica", 10)
    for idx in range(total_rows):
        if idx < len(items):
            item = items[idx]
            qty = item.get("total_qty", "")
            price = float(item.get("price", ""))
            amt = round(qty * price, 2)
            row_data = [
                str(idx + 1),
                item.get("name", ""),
                qty,
                item.get("unit", "KG"),
                price,
                amt
            ]
        else:
            row_data = [""] * 6

        x = x_start
        for i, value in enumerate(row_data):
            value_str = str(value)
            if i == 1:
                # Left-aligned for 2nd column (index 1)
                c.drawString(x + 2, y - row_height + 5, value_str)
            else:
                # Right-aligned for all other columns
                c.drawRightString(x + col_widths[i] - 2, y - row_height + 5, value_str)
            x += col_widths[i]

        y -= row_height

    
    # Footer row
    c.line(x, total_height+60, width-60, total_height+60)  # Final bottom edge
    c.setFont("Helvetica-Bold", 10)
    x = x_start
    footer=['>','Total','10','','',f'{Total}']
    for i, header in enumerate(footer):
        c.drawString(x + 2, y - row_height + 5, header)
        x += col_widths[i]

    # Final table border
    table_width = sum(col_widths)
    c.rect(x_start, y_start - total_height, table_width, total_height)

    return y


def draw_summary(c, y,width,total):
   

    c.setFont("Helvetica-Bold", 9)
    c.drawString(25, y - 10, "Grand Total")
    c.drawRightString(130, y - 10, f'{total}')

    c.setFont("Helvetica", 9)
    # y -= 25
    # c.drawString(25, y, "Tax Rate        Taxable Amt.   CGST Amt.   SGST Amt.   Total Tax")
    # y -= 15
    # c.drawString(25, y, "5%")
    # c.drawString(90, y, "2,571.42")
    # c.drawString(170, y, "64.29")
    # c.drawString(250, y, "64.29")
    # c.drawString(330, y, "128.58")
    words = num2words(total, to='cardinal', lang='en_IN').title()
    c.drawString(25, y-25, "In Words:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(80, y-25, f'{words} Only')
    c.rect(20, y-60, width - 40, 30)

    return y

def draw_footer(c, y):

    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(25, y, "Previous Balance : ")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(140, y, "87,590.00 Dr")

    c.setFont("Helvetica", 9)
    c.drawString(300, y, "Total Balance :")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(400, y, "90,290.00 Dr")

    # Terms and signature
    y -= 30
    c.setFont("Helvetica-Bold", 9)
    c.drawString(25, y, "Terms & Conditions")
    c.setFont("Helvetica", 8)
    c.drawString(25, y - 12, "E.& O.E.")
    c.drawString(25, y - 24, "1. Goods once sold will not be taken back.")
    c.drawString(25, y - 36, "2. Interest @ 18% p.a. will be charged if the payment is not made within the stipulated time.")
    c.drawString(25, y - 48, "3. Subject to 'Bathinda' Jurisdiction only.")

    logo_path = "sign.jpg"  # ← Replace with your actual filename
    logo_width = 120
    logo_height = 50
    c.drawImage(logo_path, 430, y - logo_height+10, width=logo_width, height=logo_height, mask='auto')

    # Signature
    c.setFont("Helvetica", 9)
    c.drawString(420, y - 48, "for NEW POULTRY HUB  ")
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(420, y - 60, "Authorised Signatory")

    return y

# @app.route('/invoice')
def generate_invoice(order,from_number):
    print(order)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width,heigth=A4
    items = order.get("product", [])
    total = round(sum(float(item.get("total_qty", 0)) * float(item.get("price", 0)) for item in items),2)

    y_header= draw_header(c,order)
    # y_start = draw_table(c, y_header - 380)
    y_start = draw_items_table(c,order,total)
    y_tax = draw_summary(c, y_start - 20,width,total)
    y_footer = draw_footer(c, y_tax - 30)
    c.rect(20, y_footer-70, width - 40, 655)

    c.showPage()
    c.save()
    buffer.seek(0)
    # return send_file(buffer, as_attachment=True, download_name="invoice.pdf", mimetype='application/pdf')

    PDF_FILE_PATH = "Invoice.pdf"
    # Save to file so WhatsApp API can upload
    with open(PDF_FILE_PATH, "wb") as f:
        f.write(buffer.read())
    print("PDF saved to disk.")

    # === 2. Upload to WhatsApp Cloud API ===
    
    upload_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/media"
    with open(PDF_FILE_PATH, "rb") as file_data:
        files = {
            "file": ("Invoice.pdf", file_data, "application/pdf")
        }
        data = {
            "messaging_product": "whatsapp",
            "type": "application/pdf"
        }

        upload_resp = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
            files=files,
            data=data
        )
        print("Upload response:", upload_resp.status_code, upload_resp.text)
        upload_resp.raise_for_status()
        media_id = upload_resp.json()["id"]


    # === 3. Send the PDF via WhatsApp ===
    
    send_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers["Content-Type"] = "application/json"
    message_payload = {
        "messaging_product": "whatsapp",
        "to": from_number,
        "type": "document",
        "document": {
            "id": media_id,
            "caption": "Here is your Receipt",
            "filename": "Invoice.pdf"
        }
    }

    send_resp = requests.post(send_url, headers=headers, json=message_payload)
    send_resp.raise_for_status()
    print("Invoice sent")
    create_bill({**order,"total_amount":total})

from datetime import datetime

def create_bill(data):
    ref = db.reference('/bills')

    # Get existing bills
    existing_bills = ref.get()

    # Generate invoice ID
    last_number = 1000
    if existing_bills:
        invoice_numbers = [
            int(key.replace('NPH', '')) 
            for key in existing_bills.keys() if key.startswith('NPH')
        ]
        if invoice_numbers:
            last_number = max(invoice_numbers)
    
    new_invoice_number = last_number + 1
    invoice_id = f"NPH{new_invoice_number}"

    # Prepare bill data
    product_data = {
        'invoice_id': invoice_id,
        **data
    }

    # Save to /bills
    bill_ref = ref.child(invoice_id)
    bill_ref.set(product_data)
    ledger_ref = db.reference('/ledger').push()
    # Prepare ledger data
    ledger_data = {
        'invoice_id': invoice_id,
        'id':ledger_ref.key,
        'date': datetime.now().strftime("%Y-%m-%d"),
        'dr':[{'ledger':'credit account','particular':'Goods Sold','amt':data.get('total_amount', 0)}],
        'cr':[{'ledger':'sell account','particular':'Goods Sold','amt':data.get('total_amount', 0)}],
        'vendor_id': data.get('vendor_id', ''),
        'total_amount': data.get('total_amount', 0),
        'vendor_name': data.get('name', 'Unknown')
    }

    # Save to /ledger with auto-generated key
    ledger_ref.set(ledger_data)

    return jsonify({
        'message': 'Bill and ledger entry added successfully',
        'invoice_id': invoice_id,
        'product': product_data
    }), 201


        
