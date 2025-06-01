from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import A4
import requests
from flask import send_file
from flask import Flask, request, Response
from firebase_admin import credentials, db
from flask import jsonify
from datetime import datetime


app = Flask(__name__)

WHATSAPP_ACCESS_TOKEN = "EACH6PXeLx50BO39th5RhjYBaIEm9WN1DeqyKTanvAM50PQ2cK10GrtVZBZCJiEH5ke8481Dzit3lhhAFB8ZCqZCxhJOIRHTeORvGdiMYYeXWIQRBDjq874W0SvrYqaTP9zsgycuRZCbx4RZAA5SzS2CdEmULMjFsuJBZCboc8cIPPu4oqmzIr178N0fkrQftXQ4uQZDZD"  # Keep secure in .env
PHONE_NUMBER_ID = "638286416039346"
headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}

def draw_items_table(c, items,Total, x_start=60, y_start=780):
    width,height=A4
    total_rows = len(items)
    col_widths = [30,60,214, 60,60,60] 
    headers = ['S.No','Date','Particulars', 'Dr', 'Cr','Amt']
    
    row_height = 20
    total_height = row_height * (total_rows + 2)  # +1 for header
    y = y_start

    # Vertical column lines
    x = x_start
    for width in col_widths:
        c.line(x, y, x, y - total_height)
        x += width
    c.line(x, y-20, width, y-20)  # Final bottom edge
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
            row_data = [
                str(idx + 1),
                item.get("date", ""),
                item.get("particular", ""),
                item.get('dr_amt', 0),
                item.get("cr_amt", 0),
                0
            ]
        else:
            row_data = [""] * 6

        x = x_start
        for i, value in enumerate(row_data):
            value_str = str(value)
            if i == 2:
                # Left-aligned for 2nd column (index 1)
                c.drawString(x + 2, y - row_height + 5, value_str)
            else:
                # Right-aligned for all other columns
                c.drawRightString(x + col_widths[i] - 2, y - row_height + 5, value_str)
            x += col_widths[i]

        y -= row_height

    
    # Footer row
    c.setFont("Helvetica-Bold", 10)
    x = x_start
    footer=['>','Total','', '']
    for i, header in enumerate(footer):
        c.drawString(x + 2, y - row_height + 5, header)
        x += col_widths[i]

    # Final table border
    table_width = sum(col_widths)
    c.rect(x_start, y_start - total_height, table_width, total_height)

    return y

# @app.route('/invoice')
def generate_pdf(order,parsed,from_number):

    ledger = parsed.get('ledger', '')
    fromdate = parsed.get('fromdate', '')
    todate = parsed.get('todate', '')

    # Convert fromdate and todate to datetime objects
    from_dt = datetime.strptime(fromdate, "%Y-%m-%d")
    to_dt = datetime.strptime(todate, "%Y-%m-%d")

    items = list(order.values())
    table_rows = []

    for entry in items:
        date_str = entry.get("date", "")
        try:
            entry_dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue  # Skip invalid dates

        # Check if the entry date is within the range
        if from_dt <= entry_dt <= to_dt:
            # Match DR
            for dr in entry.get("dr", []):
                if dr.get("ledger") == ledger:
                    table_rows.append({
                        "date": date_str,
                        "particular": dr.get('particular', "other"),
                        "dr_amt": dr["amt"],
                        "cr_amt": 0
                    })

            # Match CR
            for cr in entry.get("cr", []):
                if cr.get("ledger") == ledger:
                    table_rows.append({
                        "date": date_str,
                        "particular": cr.get('particular', "other"),
                        "dr_amt": 0,
                        "cr_amt": cr["amt"]
                    })
    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        total=50

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, height - 40, f"{ledger} Ledger ({fromdate} to {todate})")
        y_start = draw_items_table(c,table_rows,total)
        c.showPage()
        c.save()
        buffer.seek(0)
        print("Done")
        # return send_file(buffer, as_attachment=False, download_name="invoice.pdf", mimetype="application/pdf")


        PDF_FILE_PATH = f"{ledger}_{fromdate}-{todate}.pdf"
        # Save to file so WhatsApp API can upload
        with open(PDF_FILE_PATH, "wb") as f:
            f.write(buffer.read())
        print("PDF saved to disk.")

        # === 2. Upload to WhatsApp Cloud API ===
        
        upload_url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/media"
        with open(PDF_FILE_PATH, "rb") as file_data:
            files = {
                "file": (f"{ledger}_{fromdate}-{todate}.pdf", file_data, "application/pdf")
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
                "caption": f"Here is your {ledger} Ledger {fromdate}_{todate}",
                "filename": f"{ledger}_{fromdate}_{todate}.pdf"
            }
        }

        send_resp = requests.post(send_url, headers=headers, json=message_payload)
        send_resp.raise_for_status()
        print("Invoice sent")
        # return jsonify({"message": "Invoice sent via WhatsApp"}), 200
    except Exception as e:
        return {"error": str(e)}, 400

# if __name__ == "__main__":
#     app.run(port=3000, debug=True)