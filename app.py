from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='client')
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self.is_active

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    industry = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.String(20), default='medium')
    budget = db.Column(db.Float)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'error')
            return redirect(url_for('login'))
        
        from flask_login import login_user
        login_user(user, remember=remember)
        flash('Logged in successfully!', 'success')
        
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    from flask_login import logout_user
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('client_dashboard'))
    
    stats = {
        'total_clients': Client.query.count(),
        'total_projects': Project.query.count(),
        'pending_invoices': 0,  # Placeholder for now
        'active_users': User.query.filter_by(is_active=True).count()
    }
    
    recent_clients = Client.query.order_by(Client.created_at.desc()).limit(5).all()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_clients=recent_clients,
                         recent_projects=recent_projects)

@app.route('/admin/clients')
@login_required
def admin_clients():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('client_dashboard'))
    
    clients = Client.query.all()
    return render_template('admin/clients.html', clients=clients)

@app.route('/admin/add-client', methods=['GET', 'POST'])
@login_required
def add_client():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('client_dashboard'))
    
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        industry = request.form.get('industry')
        
        client = Client(
            company_name=company_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            industry=industry,
            admin_id=current_user.id
        )
        
        db.session.add(client)
        db.session.commit()
        flash('Client added successfully!', 'success')
        return redirect(url_for('admin_clients'))
    
    return render_template('admin/add_client.html')

# Client Routes
@app.route('/client/dashboard')
@login_required
def client_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    user_projects = Project.query.filter_by(user_id=current_user.id).all()
    
    stats = {
        'total_projects': len(user_projects),
        'completed_projects': len([p for p in user_projects if p.status == 'completed']),
        'pending_invoices': 0,
        'active_projects': len([p for p in user_projects if p.status == 'in_progress'])
    }
    
    return render_template('client/dashboard.html', stats=stats, projects=user_projects)

@app.route('/client/profile', methods=['GET', 'POST'])
@login_required
def client_profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.phone = request.form.get('phone')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('client_profile'))
    
    return render_template('client/profile.html')

# Initialize database and create admin user
def initialize_database():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(email='admin@company.com').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@company.com',
                first_name='System',
                last_name='Administrator',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@company.com / admin123")

if __name__ == '__main__':
    initialize_database()
    app.run(host='0.0.0.0', port=5000, debug=False)
