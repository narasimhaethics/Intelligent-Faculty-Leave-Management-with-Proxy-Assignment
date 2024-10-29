from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, Users, LeaveRequests, ProxyAssignment
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('home.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('faculty_dashboard' if user.role == 'faculty' else 'admin_dashboard'))
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/faculty_dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        return redirect(url_for('admin_dashboard'))
    leave_requests = LeaveRequests.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', leave_requests=leave_requests)

@app.route('/leave_request', methods=['GET', 'POST'])
@login_required
def leave_request():
    if current_user.role != 'faculty':
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        leave_request = LeaveRequests(
            user_id=current_user.id,
            start_date=datetime.strptime(start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(end_date, '%Y-%m-%d')
        )
        db.session.add(leave_request)
        db.session.commit()
        flash("Leave request submitted!")
        return redirect(url_for('faculty_dashboard'))
    return render_template('leave_request.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('faculty_dashboard'))
    leave_requests = LeaveRequests.query.all()
    return render_template('admin_dashboard.html', leave_requests=leave_requests)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Initialize the database
    app.run(debug=True)