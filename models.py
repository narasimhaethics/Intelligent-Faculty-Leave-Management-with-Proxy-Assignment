from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

from flask_login import UserMixin

class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(100), nullable=False)
    lname = db.Column(db.String(50), nullable=False)
    emailid = db.Column(db.String(150), nullable=False, unique=True)
    role = db.Column(db.String(20), nullable=False)  # faculty or admin
    password = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(10), nullable=False)  # active, inactive, etc.
    
    # Relationship with FacultyDetails
    faculty_details = db.relationship('FacultyDetails', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.fname} {self.lname}, Role: {self.role}>"

class FacultyDetails(db.Model):
    __tablename__ = 'faculty_details'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    program = db.Column(db.String(50), nullable=False)  # B.Tech, BCA, MCA
    course = db.Column(db.String(50), nullable=False)   # CSE, IT, General, etc.
    semester = db.Column(db.Integer, nullable=False)    # Semester number
    subject_allocated = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(9), nullable=False)  # e.g., "2024-2025"
   # timetable = db.Column(db.JSON, nullable=False)      # JSON structure for timetable

    def __repr__(self):
        return f"<FacultyDetails Subject: {self.subject_allocated}, Program: {self.program}, Course: {self.course}, Semester: {self.semester}>"


class FacultyTimetable(db.Model):
    __tablename__ = 'faculty_timetable'

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_details.id'), nullable=False)
    faculty_name = db.Column(db.String(100), nullable=False)  # Faculty name
    day_of_week = db.Column(db.String(10), nullable=False)  # e.g., 'Monday', 'Tuesday', etc.
    
    # Time slots for 6 hours (with break in between)
    slot_1 = db.Column(db.String(100), nullable=True)  # 7:30 AM to 8:30 AM
    slot_2 = db.Column(db.String(100), nullable=True)  # 8:30 AM to 9:30 AM
    slot_3 = db.Column(db.String(100), nullable=True)  # 9:30 AM to 10:30 AM
    slot_4 = db.Column(db.String(100), nullable=True)  # 10:30 AM to 11:30 AM
    slot_5 = db.Column(db.String(100), nullable=True)  # 11:30 AM to 12:30 PM
    slot_6 = db.Column(db.String(100), nullable=True)  # 12:30 PM to 1:30 PM

    # Define a relationship to the `FacultyDetails` model
    faculty = db.relationship('FacultyDetails', backref='timetable', lazy=True)

    def __repr__(self):
        return f"<FacultyTimetable for {self.faculty_name} on {self.day_of_week}>"
    

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty_details.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    leave_date = db.Column(db.Date, nullable=False)
    weekday = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # "Pending", "Approved", "Rejected"

    faculty = db.relationship('FacultyDetails', backref='leave_requests', lazy=True)

    def __repr__(self):
        return f"<LeaveRequest {self.faculty_id} - {self.leave_date}: {self.status}>"