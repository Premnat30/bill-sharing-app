import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import csv
import io
import requests
import re

app = Flask(__name__)

# Render configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'bill-sharing-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bill_sharing.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File upload configuration for Render
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Database Models (keep all your existing models)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Friend(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    country_code = db.Column(db.String(5), default='+91')  # +91 for India, +65 for Singapore
    whatsapp_number = db.Column(db.String(20), nullable=False)
    avatar = db.Column(db.String(50), default='avatar1.png')  # Store avatar filename
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_name = db.Column(db.String(200), nullable=False)
    visit_date = db.Column(db.Date, nullable=False)
    base_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    service_charge = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    bill_image = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BillShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('friend.id'), nullable=False)
    food_item = db.Column(db.String(200), nullable=False)
    food_amount = db.Column(db.Float, nullable=False)
    tax_share = db.Column(db.Float, nullable=False)
    service_charge_share = db.Column(db.Float, default=0.0)
    total_share = db.Column(db.Float, nullable=False)
    shared_at = db.Column(db.DateTime, default=datetime.utcnow)

    bill = db.relationship('Bill', backref='shares')
    friend = db.relationship('Friend', backref='bill_shares')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_amounts_from_text(text):
    """Extract amounts from OCR text using improved regex patterns for restaurant bills"""
    amounts = {
        'subtotal': 0,
        'tax': 0,
        'total': 0,
        'discount': 0,
        'service_charge': 0
    }

    # Improved patterns for restaurant bills
    patterns = {
        'subtotal': [
            r'sub\s?total\s*[:\$]?\s*(\d+\.?\d*)',
            r'base\s*amount\s*[:\$]?\s*(\d+\.?\d*)',
            r'food\s*total\s*[:\$]?\s*(\d+\.?\d*)',
            r'amount\s*before\s*tax\s*[:\$]?\s*(\d+\.?\d*)'
        ],
        'tax': [
            r'tax\s*[:\$]?\s*(\d+\.?\d*)',
            r'gst\s*[:\$]?\s*(\d+\.?\d*)',
            r'vat\s*[:\$]?\s*(\d+\.?\d*)',
            r'sales\s*tax\s*[:\$]?\s*(\d+\.?\d*)',
            r'tax\s*amount\s*[:\$]?\s*(\d+\.?\d*)'
        ],
        'total': [
            r'total\s*[:\$]?\s*(\d+\.?\d*)',
            r'grand\s*total\s*[:\$]?\s*(\d+\.?\d*)',
            r'amount\s*due\s*[:\$]?\s*(\d+\.?\d*)',
            r'amount\s*to\s*pay\s*[:\$]?\s*(\d+\.?\d*)',
            r'final\s*amount\s*[:\$]?\s*(\d+\.?\d*)',
            r'payable\s*amount\s*[:\$]?\s*(\d+\.?\d*)'
        ],
        'discount': [
            r'discount\s*[:\$]?\s*(\d+\.?\d*)',
            r'off\s*[:\$]?\s*(\d+\.?\d*)',
            r'deduction\s*[:\$]?\s*(\d+\.?\d*)',
            r'coupon\s*[:\$]?\s*(\d+\.?\d*)'
        ],
        'service_charge': [
            r'service\s*charge\s*[:\$]?\s*(\d+\.?\d*)',
            r'service\s*[:\$]?\s*(\d+\.?\d*)',
            r'tip\s*[:\$]?\s*(\d+\.?\d*)',
            r'gratuity\s*[:\$]?\s*(\d+\.?\d*)'
        ]
    }

    # Clean and normalize the text
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\s\.\$:]', ' ', text_lower)  # Remove special chars except $, ., :
    text_clean = re.sub(r'\s+', ' ', text_clean)  # Normalize spaces

    print(f"Cleaned OCR Text: {text_clean}")  # Debug output

    # Try to extract amounts using patterns
    for amount_type, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = re.findall(pattern, text_clean)
            if matches:
                try:
                    # Take the last match (often the final amount in bill)
                    amounts[amount_type] = float(matches[-1])
                    print(f"Found {amount_type}: {amounts[amount_type]}")  # Debug
                    break
                except ValueError:
                    continue

    # If total not found, look for currency patterns
    if amounts['total'] == 0:
        # Look for $ amounts specifically
        currency_matches = re.findall(r'\$?\s*(\d+\.?\d*)', text_clean)
        if currency_matches:
            try:
                # Filter reasonable amounts (not too small, not too large)
                valid_amounts = [float(amt) for amt in currency_matches
                               if 1.0 <= float(amt) <= 10000.0]
                if valid_amounts:
                    amounts['total'] = max(valid_amounts)
                    print(f"Found total from currency: {amounts['total']}")  # Debug
            except:
                pass

    # If subtotal not found but total is found, assume subtotal is close to total
    if amounts['subtotal'] == 0 and amounts['total'] > 0:
        amounts['subtotal'] = amounts['total'] - amounts['tax'] - amounts['service_charge'] + amounts['discount']
        if amounts['subtotal'] > 0:
            print(f"Calculated subtotal: {amounts['subtotal']}")  # Debug

    # Ensure amounts make logical sense
    if amounts['total'] > 0:
        # If tax+service+subtotal doesn't match total, adjust
        calculated_total = amounts['subtotal'] - amounts['discount'] + amounts['service_charge'] + amounts['tax']
        if abs(calculated_total - amounts['total']) > 1.0:  # If difference > $1
            # Recalculate based on total
            if amounts['subtotal'] == 0:
                amounts['subtotal'] = amounts['total'] - amounts['tax'] - amounts['service_charge'] + amounts['discount']

    print(f"Final amounts: {amounts}")  # Debug
    return amounts

def ocr_space_file(filename, overlay=False, api_key='helloworld', language='eng'):
    """OCR.space API request with local file."""
    payload = {
        'isOverlayRequired': overlay,
        'apikey': api_key,
        'language': language,
    }
    with open(filename, 'rb') as f:
        r = requests.post(
            'https://api.ocr.space/parse/image',
            files={filename: f},
            data=payload,
        )
    return r.json()

def initialize_database():
    try:
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(username='admin').first():
                admin_user = User(
                    username='admin',
                    password=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print("Default admin user created successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database
initialize_database()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    total_friends = Friend.query.filter_by(user_id=user_id).count()
    total_bills = Bill.query.filter_by(user_id=user_id).count()
    total_spending_result = db.session.query(db.func.sum(Bill.total_amount)).filter_by(user_id=user_id).scalar()
    total_spending = total_spending_result if total_spending_result else 0
    recent_bills = Bill.query.filter_by(user_id=user_id).order_by(Bill.created_at.desc()).limit(5).all()
    return render_template('dashboard.html',
                         total_friends=total_friends,
                         total_bills=total_bills,
                         total_spending=total_spending,
                         recent_bills=recent_bills)

@app.route('/friends', methods=['GET', 'POST'])
def friends():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        whatsapp_number = request.form['whatsapp_number']
        friend = Friend(user_id=session['user_id'], name=name, whatsapp_number=whatsapp_number)
        db.session.add(friend)
        db.session.commit()
        flash('Friend added successfully!', 'success')
        return redirect(url_for('friends'))
    user_friends = Friend.query.filter_by(user_id=session['user_id']).order_by(Friend.created_at.desc()).all()
    return render_template('friends.html', friends=user_friends)

@app.route('/friends/delete/<int:friend_id>')
def delete_friend(friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    friend = Friend.query.filter_by(id=friend_id, user_id=session['user_id']).first()
    if friend:
        BillShare.query.filter_by(friend_id=friend_id).delete()
        db.session.delete(friend)
        db.session.commit()
        flash('Friend deleted successfully!', 'success')
    else:
        flash('Friend not found', 'error')
    return redirect(url_for('friends'))

@app.route('/bills')
def bills():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_bills = Bill.query.filter_by(user_id=session['user_id']).order_by(Bill.visit_date.desc()).all()
    return render_template('bills.html', bills=user_bills)

@app.route('/bills/delete/<int:bill_id>')
def delete_bill(bill_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    bill = Bill.query.filter_by(id=bill_id, user_id=session['user_id']).first()
    if bill:
        BillShare.query.filter_by(bill_id=bill_id).delete()
        db.session.delete(bill)
        db.session.commit()
        flash('Bill deleted successfully!', 'success')
    else:
        flash('Bill not found', 'error')
    return redirect(url_for('bills'))

@app.route('/add_bill', methods=['GET', 'POST'])
def add_bill():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        restaurant_name = request.form['restaurant_name']
        visit_date = request.form['visit_date']
        base_amount = float(request.form['base_amount'])
        discount_amount = float(request.form.get('discount_amount', 0))
        service_charge = float(request.form.get('service_charge', 0))
        tax_amount = float(request.form['tax_amount'])
        total_amount = base_amount - discount_amount + service_charge + tax_amount
        bill = Bill(
            user_id=session['user_id'],
            restaurant_name=restaurant_name,
            visit_date=datetime.strptime(visit_date, '%Y-%m-%d'),
            base_amount=base_amount,
            discount_amount=discount_amount,
            service_charge=service_charge,
            tax_amount=tax_amount,
            total_amount=total_amount
        )
        db.session.add(bill)
        db.session.commit()
        flash('Bill added successfully!', 'success')
        return redirect(url_for('bills'))
    return render_template('add_bill.html')

@app.route('/share_bill', methods=['GET', 'POST'])
def share_bill():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    if request.method == 'POST':
        bill_id = request.form['bill_id']
        friend_ids = request.form.getlist('friend_ids')
        food_items = request.form.getlist('food_items')
        food_amounts = request.form.getlist('food_amounts')
        bill = Bill.query.filter_by(id=bill_id, user_id=user_id).first()
        if not bill:
            flash('Bill not found', 'error')
            return redirect(url_for('share_bill'))
        tax_per_person = bill.tax_amount / len(friend_ids) if friend_ids else 0
        service_charge_per_person = bill.service_charge / len(friend_ids) if friend_ids else 0
        bill_shares_data = []
        for i, friend_id in enumerate(friend_ids):
            if i < len(food_items) and i < len(food_amounts):
                food_amount = float(food_amounts[i])
                total_share = food_amount + tax_per_person + service_charge_per_person
                friend = Friend.query.get(friend_id)
                bill_share = BillShare(
                    bill_id=bill.id,
                    friend_id=friend_id,
                    food_item=food_items[i],
                    food_amount=food_amount,
                    tax_share=tax_per_person,
                    service_charge_share=service_charge_per_person,
                    total_share=total_share
                )
                db.session.add(bill_share)
                bill_shares_data.append({
                    'friend_name': friend.name,
                    'whatsapp_number': friend.whatsapp_number,
                    'food_item': food_items[i],
                    'food_amount': food_amount,
                    'tax_share': tax_per_person,
                    'service_charge_share': service_charge_per_person,
                    'total_share': total_share
                })
        db.session.commit()
        csv_data = generate_bill_shares_csv(bill, bill_shares_data)
        filename = f"bill_share_{bill.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        flash('Bill shared successfully! CSV file has been generated.', 'success')
        return render_template('share_bill_success.html',
                             bill=bill,
                             bill_shares_data=bill_shares_data,
                             csv_data=csv_data,
                             filename=filename)
    friends = Friend.query.filter_by(user_id=user_id).all()
    bills = Bill.query.filter_by(user_id=user_id).order_by(Bill.visit_date.desc()).all()
    return render_template('share_bill.html', friends=friends, bills=bills)

def generate_bill_shares_csv(bill, bill_shares_data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Bill Sharing Details'])
    writer.writerow([])
    writer.writerow(['Restaurant:', bill.restaurant_name])
    writer.writerow(['Visit Date:', bill.visit_date.strftime('%Y-%m-%d')])
    writer.writerow(['Base Amount:', f"${bill.base_amount:.2f}"])
    writer.writerow(['Discount Amount:', f"${bill.discount_amount:.2f}"])
    writer.writerow(['Service Charge:', f"${bill.service_charge:.2f}"])
    writer.writerow(['Tax Amount:', f"${bill.tax_amount:.2f}"])
    writer.writerow(['Total Amount:', f"${bill.total_amount:.2f}"])
    writer.writerow(['Generated On:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    writer.writerow([])
    writer.writerow(['Friend Name', 'WhatsApp Number', 'Food Item', 'Food Amount', 'Tax Share', 'Service Charge Share', 'Total Share'])
    total_food = 0
    total_tax = 0
    total_service_charge = 0
    total_share = 0
    for share in bill_shares_data:
        writer.writerow([
            share['friend_name'],
            share['whatsapp_number'],
            share['food_item'],
            f"${share['food_amount']:.2f}",
            f"${share['tax_share']:.2f}",
            f"${share['service_charge_share']:.2f}",
            f"${share['total_share']:.2f}"
        ])
        total_food += share['food_amount']
        total_tax += share['tax_share']
        total_service_charge += share['service_charge_share']
        total_share += share['total_share']
    writer.writerow([])
    writer.writerow(['TOTAL', '', '', f"${total_food:.2f}", f"${total_tax:.2f}", f"${total_service_charge:.2f}", f"${total_share:.2f}"])
    return output.getvalue()

@app.route('/get_bill_details/<int:bill_id>')
def get_bill_details(bill_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'})
    bill = Bill.query.filter_by(id=bill_id, user_id=session['user_id']).first()
    if bill:
        return jsonify({
            'restaurant_name': bill.restaurant_name,
            'base_amount': bill.base_amount,
            'discount_amount': bill.discount_amount,
            'service_charge': bill.service_charge,
            'tax_amount': bill.tax_amount,
            'total_amount': bill.total_amount
        })
    return jsonify({'error': 'Bill not found'})

# NEW IMAGE UPLOAD & OCR ROUTES
@app.route('/upload_bill_image', methods=['GET', 'POST'])
def upload_bill_image():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'bill_image' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)

        file = request.files['bill_image']

        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                # Process with OCR - try with different settings
                ocr_result = ocr_space_file(filepath, overlay=False, language='eng')

                if ocr_result.get('IsErroredOnProcessing'):
                    # Try with different language setting
                    ocr_result = ocr_space_file(filepath, overlay=False, language='eng')

                if ocr_result.get('IsErroredOnProcessing'):
                    flash('OCR processing failed. Please try another image or enter amounts manually.', 'error')
                    return redirect(request.url)

                # Extract text from OCR result
                parsed_results = ocr_result.get('ParsedResults', [])
                if not parsed_results:
                    flash('No text could be extracted from the image.', 'error')
                    return redirect(request.url)

                parsed_text = parsed_results[0].get('ParsedText', '')

                if not parsed_text or len(parsed_text.strip()) < 10:
                    flash('Very little text extracted. Please try a clearer image.', 'error')
                    return redirect(request.url)

                # Extract amounts from text
                amounts = extract_amounts_from_text(parsed_text)

                # If no amounts found, provide guidance
                if amounts['total'] == 0 and amounts['subtotal'] == 0:
                    flash('No amounts detected automatically. Please enter the amounts manually below.', 'warning')

                flash('Bill image processed successfully! Review the extracted amounts below.', 'success')
                return render_template('process_bill_image.html',
                                     extracted_text=parsed_text,
                                     amounts=amounts,
                                     image_filename=filename)

            except Exception as e:
                flash(f'Error processing image: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('Invalid file type. Please upload PNG, JPG, or JPEG.', 'error')
            return redirect(request.url)

    return render_template('upload_bill_image.html')

@app.route('/create_bill_from_ocr', methods=['POST'])
def create_bill_from_ocr():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Get form data
        restaurant_name = request.form['restaurant_name']
        visit_date = request.form['visit_date']
        base_amount = float(request.form.get('base_amount', 0))
        discount_amount = float(request.form.get('discount_amount', 0))
        service_charge = float(request.form.get('service_charge', 0))
        tax_amount = float(request.form.get('tax_amount', 0))
        total_amount = float(request.form.get('total_amount', 0))
        image_filename = request.form.get('image_filename', '')

        print(f"Received data: {restaurant_name}, {visit_date}, base: {base_amount}, discount: {discount_amount}, service: {service_charge}, tax: {tax_amount}, total: {total_amount}")  # Debug

        # Validate required fields
        if not restaurant_name or not restaurant_name.strip():
            flash('Restaurant name is required', 'error')
            return redirect(url_for('upload_bill_image'))

        if base_amount <= 0:
            flash('Base amount must be greater than 0', 'error')
            return redirect(url_for('upload_bill_image'))

        # Calculate total if it's zero or invalid
        calculated_total = base_amount - discount_amount + service_charge + tax_amount
        if total_amount <= 0:
            total_amount = calculated_total

        # Ensure total makes sense
        if total_amount <= 0:
            flash('Total amount must be greater than 0', 'error')
            return redirect(url_for('upload_bill_image'))

        # Create the bill
        bill = Bill(
            user_id=session['user_id'],
            restaurant_name=restaurant_name.strip(),
            visit_date=datetime.strptime(visit_date, '%Y-%m-%d'),
            base_amount=base_amount,
            discount_amount=discount_amount,
            service_charge=service_charge,
            tax_amount=tax_amount,
            total_amount=total_amount,
            bill_image=image_filename
        )

        db.session.add(bill)
        db.session.commit()

        flash('Bill created successfully from image!', 'success')
        return redirect(url_for('bills'))

    except ValueError as e:
        flash('Please enter valid numeric amounts', 'error')
        print(f"ValueError: {e}")  # Debug
        return redirect(url_for('upload_bill_image'))
    except Exception as e:
        flash(f'Error creating bill: {str(e)}', 'error')
        print(f"Exception: {e}")  # Debug
        return redirect(url_for('upload_bill_image'))

# NEW WHATSAPP ROUTES
@app.route('/share_bill_whatsapp/<int:bill_id>')
def share_bill_whatsapp(bill_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    bill = Bill.query.filter_by(id=bill_id, user_id=session['user_id']).first()
    if not bill:
        flash('Bill not found', 'error')
        return redirect(url_for('bills'))
    bill_shares = BillShare.query.filter_by(bill_id=bill_id).all()
    bill_shares_data = []
    for share in bill_shares:
        friend = Friend.query.get(share.friend_id)
        bill_shares_data.append({
            'friend_name': friend.name,
            'whatsapp_number': friend.whatsapp_number,
            'food_item': share.food_item,
            'food_amount': share.food_amount,
            'tax_share': share.tax_share,
            'service_charge_share': share.service_charge_share,
            'total_share': share.total_share
        })
    message = create_whatsapp_message(bill, bill_shares_data)
    return render_template('share_whatsapp.html',
                         bill=bill,
                         bill_shares_data=bill_shares_data,
                         whatsapp_message=message)

def create_whatsapp_message(bill, bill_shares_data):
    message = f"🍽️ *Bill Sharing - {bill.restaurant_name}*\n"
    message += f"Date: {bill.visit_date.strftime('%Y-%m-%d')}\n"
    message += f"Total Amount: ${bill.total_amount:.2f}\n\n"
    message += "*Individual Shares:*\n"
    for share in bill_shares_data:
        message += f"👤 {share['friend_name']}:\n"
        message += f"   Food: ${share['food_amount']:.2f} ({share['food_item']})\n"
        message += f"   Tax: ${share['tax_share']:.2f}\n"
        message += f"   Service: ${share['service_charge_share']:.2f}\n"
        message += f"   *Total: ${share['total_share']:.2f}*\n\n"
    message += "Please transfer your share. Thank you! 🙏"
    return message

@app.route('/send_whatsapp_individual/<int:bill_id>/<int:friend_id>')
def send_whatsapp_individual(bill_id, friend_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    bill = Bill.query.filter_by(id=bill_id, user_id=session['user_id']).first()
    friend = Friend.query.filter_by(id=friend_id, user_id=session['user_id']).first()
    if not bill or not friend:
        flash('Bill or friend not found', 'error')
        return redirect(url_for('bills'))
    share = BillShare.query.filter_by(bill_id=bill_id, friend_id=friend_id).first()
    if not share:
        flash('Share not found', 'error')
        return redirect(url_for('bills'))
    message = f"Hi {friend.name}! 👋\n\n"
    message += f"Here's your share for {bill.restaurant_name}:\n"
    message += f"🍽️ Food: ${share.food_amount:.2f} ({share.food_item})\n"
    message += f"📊 Tax: ${share.tax_share:.2f}\n"
    message += f"🔔 Service: ${share.service_charge_share:.2f}\n"
    message += f"💰 *Total Amount: ${share.total_share:.2f}*\n\n"
    message += "Please transfer this amount. Thank you! 😊"
    whatsapp_url = f"https://wa.me/{friend.whatsapp_number}?text={message.replace(' ', '%20').replace('\n', '%0A')}"
    return redirect(whatsapp_url)

if __name__ == '__main__':
    app.run(debug=True)
