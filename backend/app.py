from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import base64
from db import init_db, get_db_connection

app = Flask(__name__, template_folder='../frontend/templates')
CORS(app)  # Enable CORS for frontend-backend communication

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads/profile_photos'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
init_db()

# Allowed file extensions for photo upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve HTML pages
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/landing')
def landing_page():
    return render_template('landing.html')

@app.route('/new-trip')
def newtrip_page():
    return render_template('new-trip.html')

@app.route('/plan-trip')
def plantrip_page():
    return render_template('plan-trip.html')

@app.route('/user-trip')
def usertrip_page():
    return render_template('my-trips.html')

@app.route('/user-profile')
def userprofile_page():
    return render_template('profile.html')


# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        # Get form data
        data = request.form
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        email = data.get('email')
        phone = data.get('phone', '')
        city = data.get('city', '')
        country = data.get('country', '')
        additional_info = data.get('additionalInfo', '')
        
        # Generate username from email
        username = email.split('@')[0]
        
        # Handle photo upload
        photo_path = None
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename and allowed_file(photo.filename):
                filename = secure_filename(f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{photo.filename.rsplit('.', 1)[1].lower()}")
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(photo_path)
        
        # Validation
        if not all([first_name, last_name, email]):
            return jsonify({
                'success': False,
                'message': 'First name, last name, and email are required'
            }), 400
        
        # Check if user already exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400
        
        # Default password (should be changed by user later)
        default_password = generate_password_hash('password123')
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (username, email, password, first_name, last_name, phone, city, country, additional_info, photo_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, default_password, first_name, last_name, phone, city, country, additional_info, photo_path, datetime.now()))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Please login with your email and default password: password123',
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password are required'
            }), 400
        
        # Get user from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
        
        # Verify password
        if not check_password_hash(user[3], password):  # user[3] is password column
            return jsonify({
                'success': False,
                'message': 'Invalid username or password'
            }), 401
        
        # Login successful
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'first_name': user[4],
                'last_name': user[5],
                'phone': user[6],
                'city': user[7],
                'country': user[8],
                'photo_path': user[10]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }), 500

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'first_name': user[4],
                'last_name': user[5],
                'phone': user[6],
                'city': user[7],
                'country': user[8],
                'additional_info': user[9],
                'photo_path': user[10],
                'created_at': user[11]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to retrieve user: {str(e)}'
        }), 500

@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        
        allowed_fields = ['first_name', 'last_name', 'phone', 'city', 'country', 'additional_info']
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'message': 'No fields to update'
            }), 400
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Update failed: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)