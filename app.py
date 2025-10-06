from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import os
from datetime import datetime

app=Flask(__name__)

db_config = {
    'host': 'localhost',
    'port': 3307,
    'user': 'root',
    'password': 'abi2004',
    'database': 'inventory_management'
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn, conn.cursor(dictionary=True)

#warehouse routes starts here
@app.route('/warehouse')
def warehouse():
    conn, cursor = get_db_connection()
    cursor.execute("SELECT id , name, address , contactNumber FROM warehouse")
    warehouses = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('locations/index.html' , warehouses = warehouses)

@app.route('/warehouse/<int:warehouse_id>/products')
def warehouseProducts(warehouse_id):
    conn, cursor = get_db_connection()
    cursor.execute("""
        SELECT id, name, price, quantity 
        FROM products 
        WHERE warehouse_id = %s""", (warehouse_id,))
    warehouseProd = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('products/warehouseProd.html', warehouseProd=warehouseProd)

@app.route('/add_warehouse' , methods=['POST'])
def add_warehouse():
    name = request.form['name']
    address = request.form['address']
    contact_number = request.form['contact']
    conn , cursor = get_db_connection()

    cursor.execute("INSERT INTO warehouse (name, address , contactNumber) Values (%s ,%s ,%s)" , (name , address , contact_number))
    
    conn.commit()
    conn.close()
    cursor.close()

    return redirect(url_for('warehouse'))

@app.route('/edit_warehouse' , methods=['POST'])
def edit_warehouse():
    warehouse_id=request.form['warehouse_id']
    name = request.form['name']
    address = request.form['address']
    contact = request.form['contact']

    conn, cursor = get_db_connection()
    cursor.execute(" UPDATE warehouse SET name=%s , address =%s , contactNumber=%s WHERE id = %s " , (name , address , contact , warehouse_id))

    conn.commit()
    conn.close()
    cursor.close()

    return redirect(url_for('warehouse'))
# warehouse routes ends here

#products routes start here
@app.route('/products')
def products():
    conn, cursor = get_db_connection()

    # for options values
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.execute("SELECT * FROM warehouse")
    warehouses = cursor.fetchall()

    cursor.execute("""
        SELECT p.id, p.name, p.price, p.quantity , p.expiry_date
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE c.name = 'Food'
        ORDER BY p.expiry_date ASC
    """)
    food_products = cursor.fetchall()

    cursor.execute("""
        SELECT p.id, p.name, p.price, p.quantity
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE c.name = 'Electronics'
    """)
    electronics_products = cursor.fetchall()

    cursor.execute("""
        SELECT p.id, p.name, p.price, p.quantity, p.expiry_date, c.name AS category
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE c.name = 'Stationery'
    """)
    stationery_products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'products/index.html',
        food_products=food_products , electronics_products=electronics_products , stationery_products=stationery_products ,
        categories = categories , warehouses = warehouses
    )

@app.route('/add_product' , methods=['POST'])
def add_product():
    name = request.form['name']
    price = request.form['price']
    quantity = request.form['quantity']
    category_id = request.form['category_id']
    warehouse_id = request.form['warehouse_id']
    expiry_date = datetime.today().strftime('%Y-%m-%d') if category_id == 1 else none

    conn , cursor = get_db_connection()

    cursor.execute("""INSERT INTO products (name , price , quantity ,expiry_date , category_id , warehouse_id )
    VALUES (%s ,%s ,%s ,%s ,%s ,%s)""" , (name , price, quantity , expiry_date , category_id , warehouse_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('products')) 

@app.route('/edit_products' , methods=['POST'])
def edit_products():
    product_id = request.form['product_id']
    name = request.form['name']
    price = request.form['price']
    quantity = request.form['quantity']
    category_id = request.form['category_id']
    warehouse_id = request.form['warehouse_id']

    conn, cursor = get_db_connection()
    cursor.execute("""
        UPDATE products SET name=%s, price=%s, quantity=%s,
        category_id=%s, warehouse_id=%s WHERE id=%s
    """, (name, price, quantity, category_id, warehouse_id, product_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('products'))
# products routes ends here

# Movement routes start here
@app.route('/movement')
def movement():
    conn, cursor = get_db_connection()
    cursor.execute("SELECT * FROM productmovement")
    movements = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('movements/index.html', movements=movements)

@app.route('/add_movement' , methods=['POST'])
def add_movement():
    product_id = request.form['product_id']
    quantity = int(request.form['quantity']) 
    from_location = request.form.get('from_location') or None
    to_location = request.form.get('to_location') or None
    
    conn , cursor = get_db_connection()

    if from_location and to_location :
        cursor.execute("SELECT id FROM warehouse WHERE name=%s" , (from_location))
        from_warehouse = cursor.fetchone()
        cursor.execute("SELECT id FROM warehouse WHERE name=%s" , (to_location))
        to_warehouse = cursor.fetchone()

        from_id = from_warehouse['id']
        to_id = to_warehouse['id']

        cursor.execute ("SELECT quantity FROM products WHERE id=%s AND warehouse_id = %s" ,
        (product_id , from_id))
        prod_quantity = cursor.fetchone()

        if prod_quantity is not None and prod_quantity['quantity'] >= quantity:

            cursor.execute("UPDATE products SET quantity = quantity - %s WHERE id=%s,warehouse_id=%s",
            (prod_quantity , product_id , from_id))

            cursor.execute("SELECT id FROM products WHERE id=%s , warehouse_id =%s" , 
            (product_id,to_id))
            destination = cursor.fetchone()

            if destination :
                cursor.execute("UPDATE products SET quantity = quantity+%s WHERE id=%s , warehouse_id=%s",
                (prod_quantity , product_id, to_id))
            else :
                cursor.execute("SELECT name, price, category_id, expiry_date FROM products WHERE id = %s", (product_id,))
                product_info = cursor.fetchone()

                cursor.execute("INSERT INTO products (name, price, quantity, expiry_date, category_id, warehouse_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (product_info['name'], product_info['price'], quantity,product_info['expiry_date'], product_info['category_id'], to_id))

            cursor.execute("INSERT INTO productmovement (product_id, quantity, from_location, to_location, timestamp) VALUES (%s, %s, %s, %s, NOW())",
            (product_id, quantity, from_location, to_location))
            conn.commit()
    elif from_location:
        cursor.execute("SELECT id FROM warehouse WHERE name=%s" , (from_location,))
        from_warehouse = cursor.fetchone()

        from_id = from_warehouse['id']

        cursor.execute ("SELECT quantity FROM products WHERE id=%s AND warehouse_id = %s" ,
        (product_id , from_id))
        prod_quantity = cursor.fetchone()

        if prod_quantity['quantity'] >= quantity:
            cursor.execute("UPDATE products SET quantity = quantity - %s WHERE id=%s AND warehouse_id=%s",
            (quantity , product_id , from_id))

            cursor.execute("INSERT INTO productmovement (product_id, quantity, from_location, to_location, timestamp) VALUES (%s, %s, %s, %s, NOW())",
            (product_id, quantity, from_location, to_location))
        conn.commit()
    elif to_location:
        cursor.execute("SELECT id FROM warehouse WHERE name=%s" , (to_location,))
        to_warehouse = cursor.fetchone()

        to_id = to_warehouse['id']

        cursor.execute ("SELECT quantity FROM products WHERE id=%s AND warehouse_id = %s" ,
        (product_id , to_id))
        prod_quantity = cursor.fetchone()

        cursor.execute("UPDATE products SET quantity = quantity + %s WHERE id=%s AND warehouse_id=%s",
        (quantity , product_id , to_id))

        cursor.execute("INSERT INTO productmovement (product_id, quantity, from_location, to_location, timestamp) VALUES (%s, %s, %s, %s, NOW())",
        (product_id, quantity, from_location, to_location))
        conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for('movement'))
    
# Movement routes end here
@app.route('/')
def landing_page():
    return render_template('landingPage.html')
    
@app.route('/dashboard')
def dashboard():
    conn, cursor = get_db_connection()

    cursor.execute("SELECT COUNT(*) AS total_products FROM products")
    total_products = cursor.fetchone()['total_products']

    cursor.execute("SELECT COUNT(*) AS low_stock FROM products WHERE quantity < 10")
    low_stock = cursor.fetchone()['low_stock']

    cursor.execute("SELECT COUNT(*) AS total_warehouses FROM warehouse")
    total_warehouses = cursor.fetchone()['total_warehouses']

    cursor.execute("""
        SELECT pm.*, p.name AS product_name 
        FROM productmovement pm 
        JOIN products p ON pm.product_id = p.id 
        ORDER BY pm.timestamp DESC 
        LIMIT 3
    """)
    recent_movements = cursor.fetchall()

    cursor.execute("""
        SELECT c.name AS category, SUM(p.quantity) AS total_quantity
        FROM products p
        JOIN categories c ON p.category_id = c.id
        GROUP BY c.name
    """)
    stock_by_category = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_products=total_products,
        low_stock=low_stock,
        total_warehouses=total_warehouses,
        recent_movements=recent_movements,
        stock_by_category=stock_by_category
    )

@app.route('/report')
def report():
    conn, cursor = get_db_connection()
    cursor.execute("""
    SELECT p.name as product_name , w.name as warehouse_name , p.quantity as quantity FROM
    products p JOIN warehouse w 
    ON p.warehouse_id = w.id
    ORDER BY w.name
    """)
    report = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('report.html' , report = report)

if __name__ == '__main__':
    app.run(debug=True)