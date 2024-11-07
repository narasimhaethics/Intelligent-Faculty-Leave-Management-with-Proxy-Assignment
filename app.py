from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, Users, FacultyDetails, FacultyTimetable #LeaveRequests, ProxyAssignment
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
        emailid = request.form['username']
        password = request.form['password']
        user = Users.query.filter_by(emailid=emailid).first()
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
    #leave_requests = LeaveRequests.query.all()
    return render_template('admin_dashboard.html') #leave_requests=leave_requests)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))
@app.route('/add_faculty', methods=["GET","POST"])
@login_required
def add_faculty():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        emailid = request.form.get('emailid')
        role = 'faculty'
        password = request.form.get('password')
        status = 'active'
        program = request.form.get('program')
        course = request.form.get('course')
        semester = request.form.get('semester')
        subject_allocated = request.form.get('subject_allocated')
        academic_year = request.form.get('academic_year')
        
        
        new_user = Users(fname=fname, lname=lname, emailid=emailid, role=role, password=password, status=status)
        db.session.add(new_user)
        db.session.commit()
        
        # Adding faculty details linked to the user
        new_faculty_details = FacultyDetails(
            user_id=new_user.id,
            program=program,
            course=course,
            semester=int(semester),
            subject_allocated=subject_allocated,
            academic_year=academic_year,
            
        )
        db.session.add(new_faculty_details)
        db.session.commit()
        
        flash('Faculty member added successfully', 'success')
        return redirect(url_for('add_faculty'))

    return render_template('add_faculty.html')

@app.route('/allocate_subject')
@login_required
def allocate_subject():
    pass

@app.route('/view_faculty_details')
@login_required
def view_faculty_details():
    faculties = FacultyDetails.query.all()
    return render_template('faculty_details.html', faculties=faculties)


@app.route('/faculty_timetable')
@login_required
def faculty_timetable():
    pass

@app.route('/faculty_details')
@login_required
def faculty_details():
   
    # Query all faculty details
    faculties = FacultyDetails.query.all()
    return render_template('faculty_details.html', faculties=faculties)

@app.route('/faculty/timetable/<int:faculty_id>', methods=['GET', 'POST'])
@login_required
def view_timetable(faculty_id):
    faculty = FacultyDetails.query.get_or_404(faculty_id)

    # Fetch the timetable for each day for the faculty
    timetable = FacultyTimetable.query.filter_by(faculty_id=faculty.id).all()

    if request.method == 'POST':
        # Handle timetable updates for a particular day
        day_of_week = request.form['day_of_week']
        slot_1 = request.form['slot_1']
        slot_2 = request.form['slot_2']
        slot_3 = request.form['slot_3']
        slot_4 = request.form['slot_4']
        slot_5 = request.form['slot_5']
        slot_6 = request.form['slot_6']

        # Check if a timetable entry already exists for that day
        timetable_entry = FacultyTimetable.query.filter_by(faculty_id=faculty.id, day_of_week=day_of_week).first()
        if timetable_entry:
            # Update existing entry
            timetable_entry.slot_1 = slot_1
            timetable_entry.slot_2 = slot_2
            timetable_entry.slot_3 = slot_3
            timetable_entry.slot_4 = slot_4
            timetable_entry.slot_5 = slot_5
            timetable_entry.slot_6 = slot_6
        else:
            # Create new entry if it doesn't exist
            new_timetable = FacultyTimetable(
                faculty_id=faculty.id,
                faculty_name=faculty.user.fname,
                day_of_week=day_of_week,
                slot_1=slot_1,
                slot_2=slot_2,
                slot_3=slot_3,
                slot_4=slot_4,
                slot_5=slot_5,
                slot_6=slot_6
            )
            db.session.add(new_timetable)

        db.session.commit()
        flash("Timetable updated successfully!", "success")
        return redirect(url_for('view_timetable', faculty_id=faculty.id))

    return render_template('view_timetable.html', timetable=timetable, faculty=faculty)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Initialize the database
    app.run(debug=True)