import random
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Student, Message, mail
from datetime import datetime, timedelta
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        location = request.form.get('location')
        skills = request.form.get('skills')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validations
        if not (name and email and phone and location and skills and password):
            flash("All fields are required.", "danger")
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('auth.register'))
            
        
            
        # Check existing student
        existing_email = Student.query.filter_by(email=email).first()
        if existing_email:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for('auth.register'))
            
        
            
        # Hashing password using scrypt
        hashed_password = generate_password_hash(password, method='scrypt')
        
        new_student = Student(
            name=name,
            email=email,
            phone=phone,
            location=location,
            skills=skills,
            password_hash=hashed_password,
            is_admin=False
        )
        
        try:
            db.session.add(new_student)
            db.session.commit()
            
            # Seed introductory welcome message
            welcome_msg = Message(
                student_id=new_student.id,
                subject="Welcome to the redesigned CareerConnect!",
                body=f"Hello {new_student.name},\n\nWelcome to your brand-new, modern student CareerConnect dashboard! Here, you can easily update your profile metrics, upload your resume link, connect your LinkedIn account, browse active recruitment drives, apply with a single click, track your pipeline statuses, view calendar events, and receive critical notifications.\n\nIf you have any feedback or face any issues, feel free to contact the administrator office.\n\nBest of luck with your career journey!\n\nBest Regards,\nCareerConnect Team",
                sent_at=datetime.utcnow()
            )
            db.session.add(welcome_msg)
            db.session.commit()
            
            flash("Registration successful! Please login to continue.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "danger")
            print("Register error:", str(e))
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return redirect(url_for('auth.login'))
            
        student = Student.query.filter_by(email=email).first()
        
        # Verify credentials
        if student and check_password_hash(student.password_hash, password):
            login_user(student)
            
            flash(f"Welcome back, {student.name}!", "success")
                
            if student.is_admin:
                return redirect(url_for('admin.admin_dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('login.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    if request.method == 'POST':

        email = request.form.get('email')

        user = Student.query.filter_by(email=email).first()

        if not user:
            flash('No account found with this email.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        otp = str(random.randint(100000, 999999))

        user.reset_otp = otp
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)

        db.session.commit()

        msg = Message(
            subject='CareerConnect Password Reset OTP',
            recipients=[email]
        )

        msg.body = f'''
Your CareerConnect OTP is:

{otp}

This OTP expires in 10 minutes.
'''

        mail.send(msg)

        flash('OTP sent to your email.', 'success')

        return redirect(url_for('auth.verify_otp', email=email))

    return render_template('forgot_password.html')


@auth_bp.route('/verify-otp/<email>', methods=['GET', 'POST'])
def verify_otp(email):

    user = Student.query.filter_by(email=email).first()

    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':

        entered_otp = request.form.get('otp')

        new_password = request.form.get('new_password')

        if user.reset_otp != entered_otp:

            flash('Invalid OTP.', 'danger')

            return redirect(url_for('auth.verify_otp', email=email))

        if datetime.utcnow() > user.otp_expiry:

            flash('OTP expired.', 'danger')

            return redirect(url_for('auth.forgot_password'))

        user.password_hash = generate_password_hash(new_password)

        user.reset_otp = None
        user.otp_expiry = None

        db.session.commit()

        flash('Password updated successfully.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('verify_otp.html', email=email)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('auth.login'))
