import firebase_admin
from firebase_admin import credentials, db
from flask import Flask, request, jsonify
import time

def get_all_products_stock():
    ref = db.reference('/products')
    products = ref.get()
    if not products:
        print("No products found.")
        return
    else:
        return jsonify(products), 201

def stock_movement(data):
    items = data.get('product')
    movement_type = "purchase" if data.get('mobile') == 'purchase' else "sale"

    if movement_type not in ['sale', 'purchase']:
        return jsonify({'error': 'Invalid movement type'}), 400

    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Invalid items list'}), 400

    errors = []
    updates = []

    for item in items:
        product_id = item.get('product_id')
        qty = int(item.get('qty'))

       
        print(f'/products/{product_id}')
        ref = db.reference(f'/products/{product_id}')
        variant_data = ref.get()

        if not variant_data:
            errors.append({**item, 'error': 'Variant not found'})
            continue

        current_stock = variant_data.get('current_stock', 0)
        amount = variant_data.get('price', 0)
        name = variant_data.get('name','')

        if movement_type == "sale" and qty > current_stock:
            item["error"] = "Insufficient stock"
            errors.append(item)
            continue

        # Sale: subtract, Purchase: add
        new_stock = current_stock - qty if movement_type == 'sale' else current_stock + qty

        # if movement_type == 'sale' and qty > current_stock:
        #     errors.append({**item, 'error': 'Insufficient stock'})
        #     continue
        timestamp = int(time.time())
        updates.append({
            'ref': ref,
            'new_stock':new_stock,
            'log':{
                'product_id': product_id,
                'quantity': qty,
                'type': movement_type,
                'updated_stock': new_stock,
                "timestamp": timestamp,
                "amt": amount,
                "name": name,
            }
           
        })

    if errors:
        return jsonify({'error': 'Operation aborted due to errors', 'details': errors}), 400

    # Apply updates and log
    for u in updates:
        u['ref'].update({'current_stock': u['new_stock']}) 
        db.reference('/stock_movements').push(u['log'])

    return 'oK',200
    # return jsonify({
    #     'message': f'{movement_type} successful',
    #     'details': [u for u in updates]
    # }), 200

def create_product(data):
    ref = db.reference('/products').push()
    product_data = {
        'product_id': ref.key,
        **data
    }
    ref.set(product_data)
    return jsonify({
        'message': 'Product added successfully',
        'product': product_data
    }), 201

