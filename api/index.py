# app_fixed.py - Complete Working Version with All Fixes
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
import jwt
import datetime
import re
import os
import json
import uuid
from functools import wraps
from pathlib import Path

app = Flask(__name__, static_folder='.', static_url_path='')

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = 'krit_agency_secret_key_2024'
app.config['JWT_SECRET'] = 'krit_jwt_secret_key_2024'
app.config['JWT_EXPIRATION_HOURS'] = 24

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Change if you have a password
app.config['MYSQL_DATABASE'] = 'krit_agency_db'

# Initialize extensions
CORS(app, origins=['*'])  # Allow all origins for testing
bcrypt = Bcrypt(app)

# Global variables
db_available = False
chat_backup_file = 'chat_backup.json'


# ==================== DATABASE FUNCTIONS ====================

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE'],
            autocommit=True,
            use_pure=True,
            connection_timeout=5
        )
        return connection
    except Error as e:
        print(f"⚠️ Database connection error: {e}")
        return None


def init_database():
    """Initialize database tables and insert sample data"""
    global db_available

    print("\n🔌 Attempting to connect to MySQL...")

    try:
        # First connect without database
        conn = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            autocommit=True
        )

        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DATABASE']}")
        cursor.execute(f"USE {app.config['MYSQL_DATABASE']}")

        # Create all tables
        print("📋 Creating tables...")

        # Users table
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS users
                       (
                           id
                           INT
                           AUTO_INCREMENT
                           PRIMARY
                           KEY,
                           username
                           VARCHAR
                       (
                           50
                       ) UNIQUE NOT NULL,
                           password_hash VARCHAR
                       (
                           255
                       ) NOT NULL,
                           email VARCHAR
                       (
                           100
                       ),
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Contacts table
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS contacts
                       (
                           id
                           INT
                           AUTO_INCREMENT
                           PRIMARY
                           KEY,
                           name
                           VARCHAR
                       (
                           100
                       ) NOT NULL,
                           email VARCHAR
                       (
                           100
                       ) NOT NULL,
                           service_type VARCHAR
                       (
                           100
                       ),
                           message TEXT NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           is_read BOOLEAN DEFAULT FALSE
                           )
                       """)

        # Portfolio table
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS portfolio
                       (
                           id
                           INT
                           AUTO_INCREMENT
                           PRIMARY
                           KEY,
                           title
                           VARCHAR
                       (
                           200
                       ) NOT NULL,
                           category VARCHAR
                       (
                           50
                       ) NOT NULL,
                           description TEXT,
                           image_url VARCHAR
                       (
                           500
                       ),
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Service requests table
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS service_requests
                       (
                           id
                           INT
                           AUTO_INCREMENT
                           PRIMARY
                           KEY,
                           client_name
                           VARCHAR
                       (
                           100
                       ) NOT NULL,
                           client_email VARCHAR
                       (
                           100
                       ) NOT NULL,
                           service_type VARCHAR
                       (
                           100
                       ) NOT NULL,
                           details TEXT,
                           status VARCHAR
                       (
                           50
                       ) DEFAULT 'pending',
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                           )
                       """)

        # Chat logs table - CRITICAL FIX
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS chat_logs
                       (
                           id
                           INT
                           AUTO_INCREMENT
                           PRIMARY
                           KEY,
                           session_id
                           VARCHAR
                       (
                           100
                       ) NOT NULL,
                           user_message TEXT,
                           bot_response TEXT,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           INDEX idx_session
                       (
                           session_id
                       ),
                           INDEX idx_created
                       (
                           created_at
                       )
                           )
                       """)
        print("✅ chat_logs table created/verified")

        # Insert default admin user
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
            cursor.execute(
                "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
                ('admin', password_hash, 'admin@krit.com')
            )
            print("✅ Default admin created - Username: admin, Password: admin123")

        # Insert sample portfolio items if table is empty
        cursor.execute("SELECT COUNT(*) FROM portfolio")
        if cursor.fetchone()[0] == 0:
            portfolio_items = [
                ('E-commerce Platform Pro', 'Web Development',
                 'Full-stack e-commerce solution with payment integration',
                 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=400&h=250&fit=crop'),
                ('AI Customer Support Bot', 'AI Automation', 'Intelligent chatbot with NLP capabilities',
                 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=250&fit=crop'),
                ('Luxury Brand Identity', 'Graphic Design', 'Complete brand identity package for luxury brand',
                 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=250&fit=crop'),
                ('E-commerce SEO Campaign', 'SEO Optimization', '200% organic traffic increase in 4 months',
                 'https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?w=400&h=250&fit=crop'),
                ('Product Launch Video', 'Video Editing', 'Professional product launch promotional video',
                 'https://images.unsplash.com/photo-1536240474400-3e3a5c3d0e9d?w=400&h=250&fit=crop'),
                ('Fintech Dashboard', 'Web Development', 'Real-time financial analytics dashboard',
                 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=250&fit=crop'),
                ('Social Media Management AI', 'AI Automation', 'Automated social media posting and analytics',
                 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400&h=250&fit=crop'),
                ('Mobile App UI/UX', 'Graphic Design', 'Modern mobile app interface design',
                 'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=400&h=250&fit=crop'),
                ('Local Business SEO', 'SEO Optimization', 'Local search domination for restaurant chain',
                 'https://images.unsplash.com/photo-1555421689-491a97ff2040?w=400&h=250&fit=crop'),
                ('Corporate Training Video', 'Video Editing', 'Professional corporate training series',
                 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=400&h=250&fit=crop')
            ]
            for item in portfolio_items:
                cursor.execute(
                    "INSERT INTO portfolio (title, category, description, image_url) VALUES (%s, %s, %s, %s)", item)
            print("✅ 10 sample portfolio items added")

        conn.close()
        db_available = True
        print("\n✅ DATABASE INITIALIZED SUCCESSFULLY!")
        return True

    except Error as e:
        print(f"\n❌ Database initialization error: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure XAMPP/WAMP is running")
        print("   2. Click 'Start' on MySQL in XAMPP Control Panel")
        print("   3. If you have a MySQL password, update line 26 in this file")
        print("   4. Check if port 3306 is available")
        db_available = False
        return False


# ==================== BACKUP FUNCTIONS ====================

def save_to_backup(session_id, user_message, bot_response):
    """Save chat messages to JSON backup file when database is not available"""
    try:
        backup_data = []
        if os.path.exists(chat_backup_file):
            with open(chat_backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

        backup_data.append({
            'session_id': session_id,
            'user_message': user_message,
            'bot_response': bot_response,
            'created_at': datetime.datetime.now().isoformat()
        })

        with open(chat_backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        return True
    except Exception as e:
        print(f"Error saving to backup: {e}")
        return False


def get_from_backup():
    """Retrieve chat messages from backup file"""
    try:
        if os.path.exists(chat_backup_file):
            with open(chat_backup_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading backup: {e}")
    return []


# ==================== JWT AUTH DECORATOR ====================

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'success': False, 'message': 'Token is missing!'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired!'}), 401
        except:
            return jsonify({'success': False, 'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# ==================== CHATBOT API ENDPOINTS ====================

@app.route('/api/chat/save', methods=['POST'])
def save_chat_message():
    """Save chatbot conversation to database or backup"""
    try:
        data = request.get_json()
        print(f"\n📨 Chat save request received: {data}")

        session_id = data.get('session_id')
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')

        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"🆕 Generated new session ID: {session_id}")

        if not user_message:
            return jsonify({'success': False, 'message': 'User message is required'}), 400

        # Try to save to database first
        if db_available:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                                   INSERT INTO chat_logs (session_id, user_message, bot_response)
                                   VALUES (%s, %s, %s)
                                   """, (session_id, user_message, bot_response))
                    conn.close()
                    print(f"✅ Chat saved to DATABASE - Session: {session_id[:20]}...")
                    return jsonify({
                        'success': True,
                        'message': 'Chat saved to database',
                        'session_id': session_id
                    }), 200
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                    conn.close()

        # If database fails, save to backup file
        print("⚠️ Saving to backup file instead...")
        if save_to_backup(session_id, user_message, bot_response):
            return jsonify({
                'success': True,
                'message': 'Chat saved to backup file (database not available)',
                'session_id': session_id,
                'backup_mode': True
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to save chat'}), 500

    except Exception as e:
        print(f"❌ Error saving chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/logs', methods=['GET'])
@token_required
def get_chat_logs(current_user):
    """Get all chatbot conversations (admin only)"""
    try:
        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM chat_logs ORDER BY created_at DESC LIMIT 500")
                chats = cursor.fetchall()

                for chat in chats:
                    if chat.get('created_at'):
                        chat['created_at'] = chat['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                conn.close()
                return jsonify({
                    'success': True,
                    'data': chats,
                    'count': len(chats),
                    'source': 'database'
                }), 200

        # Return backup data if database not available
        backup_data = get_from_backup()
        return jsonify({
            'success': True,
            'data': backup_data,
            'count': len(backup_data),
            'source': 'backup'
        }), 200

    except Exception as e:
        print(f"Error fetching chat logs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/sessions', methods=['GET'])
@token_required
def get_chat_sessions(current_user):
    """Get unique chat sessions with statistics (admin only)"""
    try:
        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                               SELECT session_id,
                                      MIN(created_at) as first_message,
                                      MAX(created_at) as last_message,
                                      COUNT(*)        as message_count
                               FROM chat_logs
                               GROUP BY session_id
                               ORDER BY last_message DESC
                               """)
                sessions = cursor.fetchall()

                for session in sessions:
                    if session.get('first_message'):
                        session['first_message'] = session['first_message'].strftime('%Y-%m-%d %H:%M:%S')
                    if session.get('last_message'):
                        session['last_message'] = session['last_message'].strftime('%Y-%m-%d %H:%M:%S')

                conn.close()
                return jsonify({'success': True, 'data': sessions, 'total_sessions': len(sessions)}), 200

        return jsonify({'success': False, 'message': 'Database not available'}), 500

    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/stats', methods=['GET'])
@token_required
def get_chat_stats(current_user):
    """Get chatbot statistics (admin only)"""
    try:
        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)

                cursor.execute("SELECT COUNT(*) as total FROM chat_logs")
                total = cursor.fetchone()

                cursor.execute("SELECT COUNT(DISTINCT session_id) as unique_sessions FROM chat_logs")
                sessions = cursor.fetchone()

                cursor.execute("SELECT COUNT(*) as today FROM chat_logs WHERE DATE(created_at) = CURDATE()")
                today = cursor.fetchone()

                cursor.execute(
                    "SELECT COUNT(*) as last_week FROM chat_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
                last_week = cursor.fetchone()

                conn.close()

                return jsonify({'success': True, 'data': {
                    'total_messages': total['total'] if total else 0,
                    'unique_sessions': sessions['unique_sessions'] if sessions else 0,
                    'today_messages': today['today'] if today else 0,
                    'last_week_messages': last_week['last_week'] if last_week else 0
                }}), 200

        backup_data = get_from_backup()
        return jsonify({'success': True, 'data': {
            'total_messages': len(backup_data),
            'unique_sessions': len(set([msg.get('session_id', '') for msg in backup_data])),
            'today_messages': len([msg for msg in backup_data if
                                   msg.get('created_at', '').startswith(datetime.date.today().isoformat())]),
            'last_week_messages': len(backup_data)
        }}), 200

    except Exception as e:
        print(f"Error fetching chat stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== OTHER API ENDPOINTS ====================

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """Save contact form data to MySQL"""
    try:
        data = request.get_json()

        # Validation
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400

        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                               INSERT INTO contacts (name, email, service_type, message)
                               VALUES (%s, %s, %s, %s)
                               """, (data['name'], data['email'], data.get('service_type', ''), data['message']))
                conn.close()
                return jsonify({'success': True, 'message': 'Message sent successfully!'}), 201

        return jsonify({'success': True, 'message': 'Message received (database offline)'}), 201

    except Exception as e:
        print(f"Error in contact submission: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages(current_user):
    """Retrieve all contact messages (admin only)"""
    try:
        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM contacts ORDER BY created_at DESC")
                messages = cursor.fetchall()

                for msg in messages:
                    if msg.get('created_at'):
                        msg['created_at'] = msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')

                conn.close()
                return jsonify({'success': True, 'data': messages}), 200

        return jsonify({'success': True, 'data': []}), 200

    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/login', methods=['POST'])
def admin_login():
    """Admin authentication"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400

        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                conn.close()

                if user and bcrypt.check_password_hash(user['password_hash'], password):
                    token = jwt.encode({
                        'username': username,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
                    }, app.config['JWT_SECRET'], algorithm='HS256')

                    return jsonify({'success': True, 'token': token, 'message': 'Login successful'}), 200

        # Default admin credentials for testing
        if username == 'admin' and password == 'admin123':
            token = jwt.encode({
                'username': 'admin',
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['JWT_SECRET'], algorithm='HS256')
            return jsonify({'success': True, 'token': token, 'message': 'Login successful (demo mode)'}), 200

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Fetch all portfolio items"""
    try:
        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT id, title, category, description, image_url FROM portfolio ORDER BY created_at DESC")
                portfolio = cursor.fetchall()
                conn.close()
                return jsonify({'success': True, 'data': portfolio}), 200

        # Fallback portfolio data
        fallback_portfolio = [
            {'id': 1, 'title': 'E-commerce Platform', 'category': 'Web Development',
             'description': 'Modern e-commerce solution',
             'image_url': 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=400&h=250&fit=crop'},
            {'id': 2, 'title': 'AI Chatbot', 'category': 'AI Automation',
             'description': 'Intelligent customer support',
             'image_url': 'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=250&fit=crop'},
            {'id': 3, 'title': 'Brand Identity', 'category': 'Graphic Design',
             'description': 'Complete brand package',
             'image_url': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=250&fit=crop'}
        ]
        return jsonify({'success': True, 'data': fallback_portfolio, 'fallback': True}), 200

    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/services/request', methods=['POST'])
def request_service():
    """Submit a service request"""
    try:
        data = request.get_json()

        required_fields = ['client_name', 'client_email', 'service_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['client_email']):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                               INSERT INTO service_requests (client_name, client_email, service_type, details)
                               VALUES (%s, %s, %s, %s)
                               """, (data['client_name'], data['client_email'], data['service_type'],
                                     data.get('details', '')))
                conn.close()
                return jsonify({'success': True, 'message': 'Service request submitted successfully!'}), 201

        return jsonify({'success': True, 'message': 'Service request received (database offline)'}), 201

    except Exception as e:
        print(f"Error in service request: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get website statistics"""
    try:
        stats = {
            'total_contacts': 0,
            'total_portfolio': 10,
            'total_service_requests': 0,
            'total_chat_messages': 0
        }

        if db_available:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM contacts")
                stats['total_contacts'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM portfolio")
                stats['total_portfolio'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM service_requests")
                stats['total_service_requests'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM chat_logs")
                stats['total_chat_messages'] = cursor.fetchone()[0]

                conn.close()
        else:
            backup_data = get_from_backup()
            stats['total_chat_messages'] = len(backup_data)

        return jsonify({'success': True, 'data': stats}), 200

    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'database_available': db_available,
        'message': 'KR IT API is running',
        'timestamp': datetime.datetime.now().isoformat()
    }), 200


@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    try:
        if os.path.exists('index.html'):
            with open('index.html', 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Create a simple HTML if index.html doesn't exist
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>KR IT Agency</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                    .container { max-width: 800px; margin: 50px auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
                    h1 { color: #333; }
                    .status { background: #4CAF50; color: white; padding: 10px; border-radius: 5px; text-align: center; }
                    .api-list { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-top: 20px; }
                    code { background: #e0e0e0; padding: 2px 5px; border-radius: 3px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🚀 KR IT Agency API Server</h1>
                    <div class="status">✅ Server is running!</div>
                    <div class="api-list">
                        <h3>📡 Available API Endpoints:</h3>
                        <ul>
                            <li><code>POST /api/chat/save</code> - Save chat messages</li>
                            <li><code>GET /api/chat/logs</code> - View chat logs (admin)</li>
                            <li><code>POST /api/contact</code> - Submit contact form</li>
                            <li><code>POST /api/login</code> - Admin login</li>
                            <li><code>GET /api/portfolio</code> - Get portfolio items</li>
                            <li><code>GET /api/health</code> - Health check</li>
                        </ul>
                        <h3>🔐 Admin Login:</h3>
                        <p>Username: <strong>admin</strong><br>Password: <strong>admin123</strong></p>
                    </div>
                </div>
            </body>
            </html>
            """
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== RUN SERVER ====================
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("   🚀 KR IT AGENCY - COMPLETE BACKEND SERVER")
    print("=" * 70)

    # Initialize database
    init_database()

    print("\n" + "=" * 70)
    if db_available:
        print("   ✅ SERVER READY WITH DATABASE CONNECTION")
    else:
        print("   ⚠️ SERVER RUNNING IN BACKUP MODE")
        print("   💡 Chat messages will be saved to backup file")
    print("=" * 70)

    print(f"\n📍 Frontend URL: http://localhost:5000")
    print(f"📍 API Base URL: http://localhost:5000/api")
    print(f"\n🔐 Admin Login Credentials:")
    print(f"   Username: admin")
    print(f"   Password: admin123")

    print(f"\n📡 Main API Endpoints:")
    print(f"   POST   /api/chat/save          - Save chat message")
    print(f"   GET    /api/chat/logs          - View chat logs (admin)")
    print(f"   GET    /api/chat/sessions      - View chat sessions (admin)")
    print(f"   GET    /api/chat/stats         - Chat statistics (admin)")
    print(f"   POST   /api/contact            - Send contact message")
    print(f"   POST   /api/login              - Admin login")
    print(f"   GET    /api/portfolio          - Get portfolio items")
    print(f"   GET    /api/health             - Health check")

    if not db_available:
        print(f"\n💡 DATABASE TROUBLESHOOTING:")
        print(f"   1. Open XAMPP Control Panel")
        print(f"   2. Click 'Start' on MySQL")
        print(f"   3. Refresh this page after MySQL starts")
        print(f"   4. Chat messages are being saved to: {chat_backup_file}")

    print("\n" + "=" * 70)
    print("   Press Ctrl+C to stop the server")
    print("=" * 70 + "\n")

    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
