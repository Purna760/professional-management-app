from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, current_user, login_required
from models import db, User, Client, Project, Invoice, Task
from auth import auth
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
app.register_blueprint(auth)

# Create admin user if not exists
def create_admin_user():
    with app.app_context():
        db.create_all()
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

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    return render_template('index.html')

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
        'pending_invoices': Invoice.query.filter_by(status='pending').count(),
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
    user_invoices = Invoice.query.filter_by(client_id=current_user.id).all()
    
    stats = {
        'total_projects': len(user_projects),
        'completed_projects': len([p for p in user_projects if p.status == 'completed']),
        'pending_invoices': len([i for i in user_invoices if i.status == 'pending']),
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

if __name__ == '__main__':
    create_admin_user()
    app.run(host='0.0.0.0', port=5000, debug=False)
