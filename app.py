from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, Users, FacultyDetails, FacultyTimetable, LeaveRequest, ProxyAssignment #LeaveRequests, ProxyAssignment
from datetime import datetime, timedelta
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account 
from sqlalchemy import and_
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

app.config['MAIL_SERVER'] = 'smtp.example.com'  # Your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'narasimhaethics@gmail.com'
app.config['MAIL_PASSWORD'] = 'Sivani@1234'
app.config['MAIL_DEFAULT_SENDER'] = 'narasimhaethics@gmail.com'

mail = Mail(app)
'''def get_available_faculties(day, slot):
    occupied_faculty_ids = db.session.query(FacultyTimetable.faculty_id).filter(
        and_(
            FacultyTimetable.day_of_week == day,
            getattr(FacultyTimetable, slot) == "Free"  # Check if the faculty is occupied in this slot
        )
    ).subquery()

    available_faculties = Users.query.join(FacultyDetails).filter(
        ~FacultyDetails.id.in_(occupied_faculty_ids)
    ).all()

    return available_faculties
'''

def get_available_faculties(day, slot, current_faculty_id):
    # Identify faculty who are not free in the specified slot on the given day
    occupied_faculty_ids = db.session.query(FacultyTimetable.faculty_id).filter(
        and_(
            FacultyTimetable.day_of_week == day,
            getattr(FacultyTimetable, slot) != "Free"  # Only include faculties where the slot is not "Free"
        )
    ).subquery()

    # Query for available faculties who are "Free" in that slot, exclude the current faculty
    available_faculties = db.session.query(Users).join(FacultyDetails).join(FacultyTimetable).filter(
        FacultyTimetable.day_of_week == day,
        getattr(FacultyTimetable, slot) == "Free",  # Only include faculties with "Free" in the slot
        FacultyDetails.id != current_faculty_id,    # Exclude the current faculty requesting leave
        FacultyDetails.id.notin_(occupied_faculty_ids)  # Exclude occupied faculties
    ).all()

    return available_faculties

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



@app.route('/leave_history')
@login_required
def leave_history():
    # Get all leave requests for the current user
    leave_requests = LeaveRequest.query.filter_by(faculty_id=current_user.id).order_by(LeaveRequest.start_date.desc()).all()
    return render_template('leave_history.html', leave_requests=leave_requests)

@app.route('/apply_leave', methods=['GET', 'POST'])
def apply_leave():
    faculty = FacultyDetails.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
        faculty_id = request.form['faculty_id']

        leave_requests = []
        while start_date <= end_date:
            leave_requests.append(LeaveRequest(
                faculty_id=faculty_id,
                start_date=start_date,
                end_date=end_date,
                leave_date=start_date,
                weekday=start_date.strftime('%A'),
                status='Pending'
            ))
            start_date += timedelta(days=1)

        db.session.add_all(leave_requests)
        db.session.commit()
        flash('Leave request submitted successfully!', 'success')
        return redirect(url_for('track_application'))

    return render_template('apply_leave.html', faculty=faculty)


@app.route('/track_application')
@login_required
def track_application():
    # Query that joins LeaveRequest, FacultyDetails, and Users based on current_user.id
    leave_requests = (
        db.session.query(LeaveRequest, FacultyDetails, Users)
        .join(FacultyDetails, LeaveRequest.faculty_id == FacultyDetails.id)
        .join(Users, FacultyDetails.user_id == Users.id)
        .filter(Users.id == current_user.id)
        .all()
    )

    # Prepare a list of dictionaries for easy template rendering
    leave_data = []
    for leave_request, faculty, user in leave_requests:
        leave_data.append({
            "faculty_name": f"{user.fname} {user.lname}",
            "email": user.emailid,
            "program": faculty.program,
            "course": faculty.course,
            "semester": faculty.semester,
            "subject_allocated": faculty.subject_allocated,
            "academic_year": faculty.academic_year,
            "leave_date": leave_request.leave_date,
            "weekday": leave_request.weekday,
            "status": leave_request.status,
            "start_date": leave_request.start_date,
            "end_date": leave_request.end_date
        })
    print(leave_data)
    return render_template('track_application.html', leave_data=leave_data)

@app.route('/admin/leave_requests')
@login_required
def view_leave_requests():
    leave_requests = db.session.query(LeaveRequest, FacultyDetails, Users).join(
        FacultyDetails, LeaveRequest.faculty_id == FacultyDetails.id
    ).join(
        Users, FacultyDetails.user_id == Users.id
    ).all()

    # Render the template and pass `get_available_faculties` function to context
    return render_template(
        'admin_leave_requests.html',
        leave_requests=leave_requests,
        get_available_faculties=get_available_faculties  # Pass function here
    )


# Initialize Google Calendar API
'''def get_google_calendar_service():
    credentials = service_account.Credentials.from_service_account_file('path/to/credentials.json', scopes=['https://www.googleapis.com/auth/calendar'])
    return build('calendar', 'v3', credentials=credentials)'''


@app.route('/admin/leave_requests/<int:leave_id>/proxy_assignments', methods=['POST'])
@login_required
def assign_proxy(leave_id):
    # Fetch the leave request details
    leave_request = LeaveRequest.query.get_or_404(leave_id)
    action = request.form.get('action')
    
    # Handle leave request rejection
    if action == "reject":
        leave_request.status = "Rejected"
        db.session.commit()
        flash("Leave request has been rejected.", "warning")
        return redirect(url_for('view_leave_requests'))
    
    proxies = request.form.to_dict(flat=True)
    proxies.pop("action", None)  # Remove action from proxies dictionary

    # Retrieve original faculty details
    faculty_details = FacultyDetails.query.filter_by(id=leave_request.faculty_id).first()
    original_faculty = Users.query.filter_by(id=faculty_details.user_id).first()
    original_faculty_name = f"{original_faculty.fname} {original_faculty.lname}"

    for slot, proxy_faculty_id in proxies.items():
        print(slot)
        if proxy_faculty_id:
            # Check if slot contains both time and date separated by ';'
            if ';' in slot:
                slot_time, slot_date = slot.split(';')
                day_of_week = datetime.strptime(slot_date, "%Y-%m-%d").strftime("%A")

                # Retrieve the subject for this slot from FacultyTimetable, if available
                timetable_entry = FacultyTimetable.query.filter_by(faculty_id=leave_request.faculty_id, slot_time=slot_time, date=slot_date).first()
                subject = timetable_entry.subject if timetable_entry else "N/A"

                # Store the proxy assignment in ProxyAssignment model
                proxy_assignment = ProxyAssignment(
                    leave_request_id=leave_id,
                    faculty_id=leave_request.faculty_id,
                    proxy_faculty_id=proxy_faculty_id,
                    slot_time=slot_time,
                    date=slot_date,
                    subject=subject
                )
                db.session.add(proxy_assignment)

                # Get proxy faculty details
                proxy_faculty_details = FacultyDetails.query.filter_by(id=proxy_faculty_id).first()
                proxy_faculty = Users.query.filter_by(id=proxy_faculty_details.user_id).first()
                proxy_faculty_name = f"{proxy_faculty.fname} {proxy_faculty.lname}"

                # Send email to the proxy faculty
                try:
                    proxy_msg = Message(
                        "Proxy Assignment Alert",
                        sender="admin@example.com",
                        recipients=[proxy_faculty.emailid]
                    )
                    proxy_msg.body = (
                        f"Dear {proxy_faculty_name},\n\n"
                        f"You have been assigned as a proxy for {original_faculty_name}.\n"
                        f"Date: {slot_date} ({day_of_week})\n"
                        f"Time: {slot_time}\n"
                        f"Subject: {subject}\n\n"
                        f"Please be available during this time.\n\nThank you."
                    )
                    mail.send(proxy_msg)
                except Exception as e:
                    flash(f"Failed to send email to proxy faculty: {str(e)}", "error")

                # Send email to the original faculty (requester)
                try:
                    original_msg = Message(
                        "Leave Request Proxy Confirmation",
                        sender="admin@example.com",
                        recipients=[original_faculty.emailid]
                    )
                    original_msg.body = (
                        f"Dear {original_faculty_name},\n\n"
                        f"Your leave request has been approved, and proxies have been assigned.\n"
                        f"Date: {slot_date} ({day_of_week})\n"
                        f"Time: {slot_time}\n"
                        f"Proxy Faculty: {proxy_faculty_name}\n"
                        f"Subject: {subject}\n\n"
                        f"Thank you for notifying us in advance.\n\nBest regards."
                    )
                    mail.send(original_msg)
                except Exception as e:
                    flash(f"Failed to send email to original faculty: {str(e)}", "error")

    # Mark leave request as approved
    leave_request.status = "Approved"
    db.session.commit()

    flash("Leave request approved, and proxies assigned.", "success")
    return redirect(url_for('view_leave_requests'))


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