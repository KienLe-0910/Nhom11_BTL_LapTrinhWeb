from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3

app = Flask(__name__)
dbname = 'db/MerchDB.db'
app.secret_key = "dcum"

@app.route("/")
def index():
    video_data = get_videos()
    music_data = get_music()
    return render_template("index.html", videos=video_data, music=music_data)


def index():
    if 'username' in session:
        # Lấy thông tin tài khoản người dùng từ cơ sở dữ liệu
        user_info = get_user_info(session['username'])
        if user_info:
            full_name = f"{user_info['first_name']} {user_info['last_name']}"
            return render_template("index.html", user_full_name=full_name)
        else:
            return "Không tìm thấy thông tin tài khoản."
    else:
        return render_template("index.html")


def get_videos():
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute('SELECT * FROM Videos ORDER BY created_time DESC LIMIT 6')
        videos = cur.fetchall()
        video_list = []
        #Tạo dict chứa thông tin của Videos
        for video in videos:
            video_dict = {
                'id': video[0],
                'title': video[1],
                'image_url': video[2],
                'created_time': video[3]
            }
            video_list.append(video_dict)
        return video_list
    #Hàm trả về 1 list chứa các video_dict
    except sqlite3.Error as e:
        print("Error reading data from SQLite:", e)
        return []


def get_music():
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute('SELECT * FROM Music ORDER BY created_time DESC LIMIT 5')
        music = cur.fetchall()
        music_list = []
        for music_item in music:
            music_dict = {
                'id': music_item[0],
                'type': music_item[1],
                'title': music_item[2],
                'image_url': music_item[3],
                'created_time': music_item[4]
            }
            music_list.append(music_dict)
        return music_list
    except sqlite3.Error as e:
        print("Error reading data from SQLite:", e)
        return []


@app.route("/store", methods=['GET', 'POST'])
def store():
    if request.method == 'POST':
        NameStr = request.form['SearchNameInput']
        PriceStr = request.form['SearchPriceInput']
        products = load_data(NameStr=NameStr, PriceStr=PriceStr)
        return render_template('store.html', merch=products, NameSearched=NameStr, PriceSearched=PriceStr)
    else:
        merch_data = get_merch()
        return render_template('store.html', merch=merch_data)
    
@app.route("/store/add", methods=["POST"])
def add_to_cart():
    product_id = request.form["product_id"]
    quantity = int(request.form["quantity"])

    connection = sqlite3.connect(dbname)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Merchandise WHERE id = ?", (product_id,))
    #3.1. get one product
    product = cursor.fetchone()
    connection.close()
    product_dict = {
        "id": product[0],
        "name": product[1],
        "image": product[2],
        "price": product[4],
        "quantity": quantity
    }
    #5. get the cart from the session or create an empty list
    cart = session.get("cart", [])
    #6. check if the product is already in the cart
    found = False
    for item in cart:
        if item["id"] == product_id:
            #6.1 update the quantity of the existing product
            item["quantity"] += quantity
            found = True
            break
    if not found:
        #6.2 add the new product to the cart
        cart.append(product_dict)
    #7. save the cart back to the session
    session["cart"] = cart
    return redirect(url_for("store"))


@app.route("/cart", methods=["GET", "POST"])
def view_cart():
    # Get the cart from the session or create an empty list
    current_cart = session.get("cart", [])
    if current_cart == []:
        return "No item in the current cart!"

    # Render the cart.html template and pass the cart
    return render_template("cart.html", cart=current_cart)

@app.route("/cart/delete", methods=["POST"])
def delete_item():
    # Get the product ID of the item to delete from the request
    product_id = int(request.form["product_id"])
    # Get the cart from the session
    cart = session.get("cart", [])
    # Iterate through the items in the cart to find the item with the specified product ID
    for item in cart:
        if item["id"] == product_id:
            # Remove the item from the cart
            cart.remove(item)
            break
    # Update the cart in the session
    session["cart"] = cart
    # Redirect back to the cart page
    return redirect(url_for("view_cart"))

@app.route("/cart/update", methods=["POST"])
def update_item():
        # Get the product ID of the item to delete from the request
    quantityChange = int(request.form["quantityChange"])
    product_id = int(request.form["product_id"])
    # Get the cart from the session
    cart = session.get("cart", [])
    # Iterate through the items in the cart to find the item with the specified product ID
    for item in cart:
        if item["id"] == product_id:
            # Remove the item from the cart
            item["quantity"] = quantityChange
            break
    # Update the cart in the session
    session["cart"] = cart
    # Redirect back to the cart page
    return redirect(url_for("view_cart"))

@app.route("/cart/proceed", methods=["POST"])
def proceed_cart():
    current_cart = []
    if 'cart' in session:
        current_cart  = session.get("cart", [])
    if 'username' in session:
        user_info = get_user_info(session["username"])
    connection = sqlite3.connect(dbname)
    cursor = connection.cursor()
    print
    cursor.execute("INSERT INTO '"'Order'"' (CustomerID) VALUES (?)", (user_info["userid"],))
    cursor.execute("SELECT OrderID FROM '"'Order'"' ORDER BY OrderDate DESC LIMIT 1")
    data = cursor.fetchone()
    orderID = data[0]-1
    Values = ""
    for product in current_cart:
        productID = product["id"]
        productQuantity = product["quantity"]
        productPrice = product["price"]
        Values += f"({orderID}, {productID}, {productQuantity}, {productPrice})"

    Values = Values.replace(")(", "), (")
    print(Values)
    cursor.execute(f"INSERT INTO OrderDetails VALUES {Values};")
    cursor.execute("SELECT OrderDetails.OrderID, Merchandise.image_main_url, Merchandise.name, Merchandise.Price, OrderDetails.Quantity, Merchandise.price * OrderDetails.Quantity AS total_price FROM OrderDetails JOIN Merchandise ON OrderDetails.MerchID = Merchandise.id WHERE OrderDetails.OrderID = ?", (orderID,))
    #[OrderID],[image],[name],[price],[quantity],[total_price]
    items = cursor.fetchall()
    connection.close()
    pop = session.pop('cart')

    return render_template("proceed.html", items=items)

def load_data(NameStr, PriceStr):
    if NameStr == "" and PriceStr == "":
        CommandStr = "SELECT * FROM Merchandise"
    elif NameStr == "":
        CommandStr = f"SELECT * FROM Merchandise WHERE price <= {PriceStr}"
    elif PriceStr == "":
        CommandStr = f"SELECT * FROM Merchandise WHERE name LIKE '%{NameStr}%'"
    else :
        CommandStr = f"SELECT * FROM Merchandise WHERE name LIKE '%{NameStr}%' OR price <= {PriceStr}"
    if CommandStr:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute(CommandStr)
        merch = cur.fetchall()
        merch_list = []
        for merch_item in merch:
            merch_dict = {
                'id': merch_item[0],
                'name': merch_item[1],
                'image_main_url': merch_item[2],
                'image_hover_url': merch_item[3],
                'price': merch_item[4],
                'created_time': merch_item[5]
            }
            merch_list.append(merch_dict)
        return merch_list
    else:
        return []


def get_merch():
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute('SELECT * FROM Merchandise')
        merch = cur.fetchall()
        merch_list = []
        for merch_item in merch:
            merch_dict = {
                'id': merch_item[0],
                'name': merch_item[1],
                'image_main_url': merch_item[2],
                'image_hover_url': merch_item[3],
                'price': merch_item[4],
                'created_time': merch_item[5]
            }
            merch_list.append(merch_dict)
        conn.close()
        return merch_list
    except sqlite3.Error as e:
        print("Error reading data from SQLite:", e)
        return []


@app.route("/item/<int:item_id>")
def item(item_id):
    item_slides = get_item_slides(item_id)
    item_details = get_item_details(item_id)
    if item_details:
        item_details['des'] = add_line_breaks(item_details['des'])
        return render_template('item.html', item_slides=item_slides, item_details=item_details)


def add_line_breaks(text):
    return text.replace('\n', '<br>')


def get_item_slides(item_id):
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute('SELECT image_url FROM ItemSlideImages m WHERE m.item_id = ?'
                    'ORDER BY num ASC', (item_id,))
        item_details = cur.fetchall()
        if item_details:
            slides = [{'item_id': item_id, 'image_url': row[0]} for row in item_details]
            return slides
        else:
            return None
    except sqlite3.Error as e:
        print("Error reading data from SQLite:", e)
        return None


def get_item_details(item_id):
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute('''SELECT m.name, m.price, md.des, md.note, md.copyright 
                       FROM Merchandise m 
                       JOIN MerchDetails md ON m.id = md.item_id 
                       WHERE m.id = ?''', (item_id,))
        item_details = cur.fetchone()
        if item_details:
            item_dict = {
                'item_id': item_id,
                'name': item_details[0],
                'price': item_details[1],
                'des': item_details[2],
                'note': item_details[3],
                'copyright': item_details[4]
            }
            return item_dict
        else:
            return None
    except sqlite3.Error as e:
        print("Error reading data from SQLite:", e)
        return None
    
# Đăng ký
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Lưu thông tin người dùng vào cơ sở dữ liệu
        save_user_to_db(username, first_name, last_name, email, password)

        # Chuyển hướng về trang đăng nhập
        return redirect(url_for("signin"))

    return render_template("signup.html")

# Lưu thông tin đăng ký vào DB
def save_user_to_db(username, first_name, last_name, email, password):
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute("INSERT INTO Customer (UserName, FirstName, LastName, Email, Password) VALUES (?, ?, ?, ?, ?)",
                    (username, first_name, last_name, email, password))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print("Error saving user to SQLite:", e)

# Sign In
@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Kiểm tra thông tin đăng nhập với cơ sở dữ liệu
        if check_user_credentials(username, password):
            # Lưu tên người dùng vào session
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return "Thông tin đăng nhập không đúng. Vui lòng thử lại."

    return render_template("signin.html")

# Check tài khoản
def check_user_credentials(username, password):
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM Customer WHERE UserName = ? AND Password = ?", (username, password))
        result = cur.fetchone()[0]
        conn.close()
        return result > 0
    except sqlite3.Error as e:
        print("Error checking user credentials:", e)
        return False
    
# Account
@app.route("/account")
def account():
    if 'username' in session:
        # Lấy thông tin tài khoản người dùng từ cơ sở dữ liệu
        user_info = get_user_info(session['username'])
        if user_info:
            return render_template("account.html", user_info=user_info)
        else:
            return "Không tìm thấy thông tin tài khoản."
    else:
        return redirect(url_for('signin'))

# Bấm vào tên user sẽ hiện thông tin user  
def get_user_info(username):
    try:
        conn = sqlite3.connect(dbname)
        cur = conn.cursor()
        cur.execute("SELECT ID, FirstName, LastName, Email FROM Customer WHERE UserName = ?", (username,))
        user_info = cur.fetchone()
        conn.close()
        if user_info:
            user_id, first_name, last_name, email = user_info
            return {
                'userid' : user_id,
                'first_name': first_name,
                'last_name': last_name,
                'email': email
            }
        else:
            return None
    except sqlite3.Error as e:
        print("Error fetching user info from SQLite:", e)
        return None
# Logout    
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
