from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, Users, FacultyDetails, FacultyTimetable, LeaveRequest #LeaveRequests, ProxyAssignment
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


def check_timetable_conflicts(timetable, requested_dates):
    conflicts = []
    for day in requested_dates:
        for entry in timetable:
            if entry.day_of_week == day['weekday']:
                # Check if any slots are occupied (replace `slot_X` with slot checking logic)
                if entry.slot_1 or entry.slot_2 or entry.slot_3:
                    conflicts.append(day)
    return conflicts

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
    # Fetch the user's details
    user = Users.query.get(current_user.id)
    faculty = FacultyDetails.query.filter_by(user_id=user.id).first()
    
    if not faculty:
        flash("Faculty details not found.", "danger")
        return redirect(url_for('logout'))

    # Fetch timetable for the faculty
    timetable_entries = FacultyTimetable.query.filter_by(faculty_id=faculty.id).all()
    
    # Format timetable in a dictionary for easy display in HTML
    timetable = {}
    for entry in timetable_entries:
        timetable[entry.day_of_week] = {
            "slot_1": entry.slot_1,
            "slot_2": entry.slot_2,
            "slot_3": entry.slot_3,
            "slot_4": entry.slot_4,
            "slot_5": entry.slot_5,
            "slot_6": entry.slot_6,
        }
    
    return render_template('faculty_dashboard.html', user=user, faculty=faculty, timetable=timetable)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password == confirm_password:
            current_user.password = new_password  # Hash this in a real application
            db.session.commit()
            flash("Password updated successfully.", "success")
        else:
            flash("Passwords do not match.", "danger")
    
    return render_template('change_password.html')

@app.route('/track_application')
@login_required
def track_application():
    # Get all leave requests for the current user
    leave_requests = LeaveRequest.query.filter_by(faculty_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    return render_template('track_application.html', leave_requests=leave_requests)

@app.route('/leave_history')
@login_required
def leave_history():
    # Get all leave requests for the current user
    leave_requests = LeaveRequest.query.filter_by(faculty_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    return render_template('leave_history.html', leave_requests=leave_requests)


@app.route('/leave_request', methods=['GET', 'POST'])
@login_required
def leave_request():
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not (faculty_id and start_date and end_date):
            flash('All fields are required', 'danger')
            return redirect(url_for('leave_request'))

        # Process dates to include weekdays
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        date_list = []

        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_list.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'weekday': current_date.strftime('%A')
            })
            current_date += timedelta(days=1)

        # Create new leave request
        leave_request = LeaveRequest(
            faculty_id=faculty_id,
            start_date=start_date,
            end_date=end_date,
            dates=date_list,
            status='Pending'
        )
        db.session.add(leave_request)
        db.session.commit()
        flash('Leave request submitted successfully', 'success')
        return redirect(url_for('faculty_dashboard'))  # Redirect to faculty dashboard or other page

    # If GET request, render form with faculty data
    faculty_id = 2  # Replace with current faculty's ID or query from session
    faculty = FacultyDetails.query.get(faculty_id)
    return render_template('leave_request.html', faculty=faculty)

@app.route('/get_dates')
def get_dates():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    dates = []

    current_date = start_date
    while current_date <= end_date:
        dates.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'weekday': current_date.strftime('%A')
        })
        current_date += timedelta(days=1)

    return jsonify({'dates': dates})


@app.route('/admin/leave_requests', methods=['GET', 'POST'])
@login_required
def admin_leave_requests():
    leave_requests = LeaveRequest.query.filter_by(status="Pending").all()

    if request.method == 'POST':
        leave_request_id = request.form['leave_request_id']
        action = request.form['action']  # 'approve' or 'reject'

        # Fetch the leave request to update
        leave_request = LeaveRequest.query.get(leave_request_id)

        # Check faculty availability if approving the request
        if action == 'approve':
            faculty_timetable = FacultyTimetable.query.filter_by(faculty_id=leave_request.faculty_id).all()
            conflicts = check_timetable_conflicts(faculty_timetable, leave_request.dates)

            if conflicts:
                flash("Cannot approve leave request; conflicting time slots found.", "danger")
            else:
                leave_request.status = "Approved"
                flash("Leave request approved successfully!", "success")
        else:
            leave_request.status = "Rejected"
            flash("Leave request rejected.", "warning")

        db.session.commit()
        return redirect(url_for('admin_leave_requests'))

    return render_template('admin_leave_requests.html', leave_requests=leave_requests)

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