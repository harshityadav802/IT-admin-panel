from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
    static_url_path='/static'
)
app.secret_key = 'IT-ADMIN-SECRET-KEY-2024'
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config['TESTING'] = False

DATA_FILE = BASE_DIR / 'data.json'


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {'users': [], 'licenses': []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            return redirect('/dashboard')
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/login')
    data = load_data()
    return render_template('dashboard.html', users=data['users'], licenses=data['licenses'])

@app.route('/users')
def users():
    if not session.get('logged_in'):
        return redirect('/login')
    data = load_data()
    return render_template('users.html', users=data['users'])

@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if not session.get('logged_in'):
        return redirect('/login')
    
    if request.method == 'POST':
        data = load_data()
        new_user = {
            'id': len(data['users']) + 1,
            'username': request.form.get('username'),
            'email': request.form.get('email'),
            'full_name': request.form.get('full_name'),
            'department': request.form.get('department'),
            'password': generate_password_hash(request.form.get('password'))
        }
        data['users'].append(new_user)
        save_data(data)
        return redirect('/users')
    
    return render_template('create_user.html')

@app.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    data = load_data()
    user = next((u for u in data['users'] if u['id'] == user_id), None)
    
    if not user:
        return redirect('/users')
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        user['password'] = generate_password_hash(new_password)
        save_data(data)
        return redirect('/users')
    
    return render_template('reset_password.html', user=user)

@app.route('/licenses')
def licenses():
    if not session.get('logged_in'):
        return redirect('/login')
    data = load_data()
    return render_template('licenses.html', licenses=data['licenses'], users=data['users'])

@app.route('/assign-license', methods=['GET', 'POST'])
def assign_license():
    if not session.get('logged_in'):
        return redirect('/login')
    
    data = load_data()
    
    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        license_type = request.form.get('license_type')
        
        user = next((u for u in data['users'] if u['id'] == user_id), None)
        if not user:
            return render_template('assign_license.html', users=data['users'], error='User not found')
        
        new_license = {
            'id': len(data['licenses']) + 1,
            'user_id': user_id,
            'license_type': license_type
        }
        data['licenses'].append(new_license)
        save_data(data)
        return redirect('/licenses')
    
    return render_template('assign_license.html', users=data['users'])

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect('/dashboard')
    return redirect('/login')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)