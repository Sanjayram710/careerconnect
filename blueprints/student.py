import os
from models import LiveJob ,SavedJob, SavedInternship, PlacementEvent
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from flask_mail import Message as MailMessage
from werkzeug.utils import secure_filename
from models import db, Student, Job, Application, Message, mail, CompanyNewsCache, BookmarkedNews, TrackedApplication
from datetime import datetime, timedelta
from services.job_api import fetch_jobs
from services.job_api import fetch_internships
from models import LiveInternship
from services.news_service import get_company_news
from services.calendar_service import sync_student_events



SKILLS = [
    'Python', 'Java', 'JavaScript', 'React', 'Angular',
    'Node.js', 'SQL', 'MySQL', 'PostgreSQL',
    'AWS', 'Azure', 'Docker', 'Kubernetes',
    'Flask', 'Django', 'Spring Boot',
    'C', 'C++', 'C#', '.NET',
    'Git', 'Linux', 'HTML', 'CSS',
    'MongoDB', 'Redis',
    'Machine Learning', 'AI'
]



student_bp = Blueprint('student', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_application_receipt_email(student, job, applied_date):
    """Sends a professional HTML application confirmation email."""
    try:
        msg = MailMessage(
            subject=f"Application Received: {job.role} at {job.company_name}",
            recipients=[student.email]
        )
        msg.html = render_template(
            'emails/application_confirmation.html',
            student=student,
            job=job,
            applied_at=applied_date
        )
        mail.send(msg)
        print(f"SMTP Email successfully sent to {student.email}")
        return True
    except Exception as e:
        print(f"SMTP Mail dispatch failed (Check .env configuration): {str(e)}")
        return False

# Calculate profile completion percentage
def get_profile_completion(user):
    score = 0
    total = 8

    if user.name: score += 1
    if user.phone: score += 1
    if user.location: score += 1
    if user.skills: score += 1
    if user.resume_filename or user.resume_link: score += 1
    if user.bio: score += 1
    if user.experience: score += 1
    if user.linkedin_url or user.linkedin_connected: score += 1

    return int((score / total) * 100)
@student_bp.route('/dashboard')
@login_required
def dashboard():

    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    # =========================
    # LOCAL DATABASE JOBS
    # =========================
    jobs = Job.query.order_by(
        Job.last_date.asc()
    ).all()

   
    # =========================
    # READ LIVE JOBS FROM DB
    # =========================
    live_jobs = LiveJob.query.filter_by(is_expired=False).order_by(
        LiveJob.updated_at.desc()
    ).limit(10).all()

    # =========================
    # USER APPLICATIONS
    # =========================
    applications = Application.query.filter_by(
        student_id=current_user.id
    ).order_by(
        Application.applied_at.desc()
    ).all()

    applied_job_ids = [app.job_id for app in applications]

    # =========================
    # DASHBOARD STATS
    # =========================
    total_applied = len(applications)

    shortlisted = sum(
        1 for app in applications
        if app.status == 'Shortlisted'
    )

    interviewing = sum(
        1 for app in applications
        if app.status == 'Interviewing'
    )

    offered = sum(
        1 for app in applications
        if app.status in ['Offered', 'Selected']
    )

    # =========================
    # PROFILE COMPLETION
    # =========================
    profile_completion = get_profile_completion(
        current_user
    )

    # =========================
    # SKILLS PROGRESS
    # =========================
    skills_list = []

    if current_user.skills:

        raw_skills = [
            s.strip()
            for s in current_user.skills.split(',')
        ]

        for i, sk in enumerate(raw_skills[:5]):

            progress_value = 95 - (i * 12)

            if progress_value < 40:
                progress_value = 55

            skills_list.append({
                'name': sk,
                'progress': progress_value
            })

    # =========================
    # SAVED JOBS
    # =========================
    saved_job_ids = set()
    if current_user.is_authenticated:
        saved_job_ids = {
            saved.live_job_id
            for saved in SavedJob.query.filter_by(user_id=current_user.id).all()
        }

    # =========================
    # UPCOMING EVENTS & CALENDAR STATS
    # =========================
    sync_student_events(current_user.id)
    today = datetime.now()
    end_of_week = today + timedelta(days=7)

    # Stats
    total_upcoming_count = PlacementEvent.query.filter(
        PlacementEvent.user_id == current_user.id,
        PlacementEvent.event_date >= today
    ).count()

    deadlines_this_week_count = PlacementEvent.query.filter(
        PlacementEvent.user_id == current_user.id,
        PlacementEvent.event_type.in_(['Application Deadline', 'Offer Deadline']),
        PlacementEvent.event_date >= today,
        PlacementEvent.event_date <= end_of_week
    ).count()

    interviews_scheduled_count = PlacementEvent.query.filter(
        PlacementEvent.user_id == current_user.id,
        PlacementEvent.event_type == 'Interview Date',
        PlacementEvent.event_date >= today
    ).count()

    assessments_scheduled_count = PlacementEvent.query.filter(
        PlacementEvent.user_id == current_user.id,
        PlacementEvent.event_type == 'Assessment Date',
        PlacementEvent.event_date >= today
    ).count()

    # Upcoming list (max 4)
    upcoming_events_db = PlacementEvent.query.filter(
        PlacementEvent.user_id == current_user.id,
        PlacementEvent.event_date >= today
    ).order_by(PlacementEvent.event_date.asc()).limit(4).all()

    color_map = {
        'Google': 'google',
        'Microsoft': 'microsoft',
        'Stripe': 'stripe',
        'NVIDIA': 'nvidia',
        'Adobe': 'adobe',
        'Tesla': 'tesla',
        'Airbnb': 'airbnb',
        'Uber': 'uber',
        'Amazon': 'amazon',
        'Meta': 'meta'
    }
    icon_map = {
        'Application Deadline': 'fa-calendar-xmark',
        'Assessment Date': 'fa-list-check',
        'Interview Date': 'fa-comments',
        'Hiring Drive': 'fa-briefcase',
        'Offer Deadline': 'fa-trophy',
        'Campus Placement Event': 'fa-building'
    }

    upcoming_events = []
    for ev in upcoming_events_db:
        days_rem = (ev.event_date.date() - today.date()).days
        days_str = "Today" if days_rem == 0 else "Tomorrow" if days_rem == 1 else f"{days_rem} days left"
        upcoming_events.append({
            "title": ev.role_title,
            "company": ev.company_name,
            "date_str": ev.event_date.strftime('%d %b %Y'),
            "days_str": days_str,
            "event_type": ev.event_type,
            "icon": icon_map.get(ev.event_type, 'fa-bell'),
            "color": color_map.get(ev.company_name, 'primary')
        })

    # =========================
    # UNREAD MESSAGES & RENDER TEMPLATE
    # =========================
    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'dashboard.html',
        jobs=jobs,
        live_jobs=live_jobs,
        applications=applications,
        applied_job_ids=applied_job_ids,
        saved_job_ids=saved_job_ids,
        active_jobs_count=len(jobs) + len(live_jobs),
        total_applied=total_applied,
        shortlisted_count=shortlisted,
        interviewing_count=interviewing,
        offers_count=offered,
        profile_completion=profile_completion,
        skills_progress=skills_list,
        unread_messages_count=unread_messages_count,
        upcoming_events=upcoming_events,
        total_upcoming_count=total_upcoming_count,
        deadlines_this_week_count=deadlines_this_week_count,
        interviews_scheduled_count=interviews_scheduled_count,
        assessments_scheduled_count=assessments_scheduled_count
    )


@student_bp.route('/explore-jobs')
@login_required
def explore_jobs():

    page = request.args.get('page', 1, type=int)

    live_jobs = LiveJob.query.filter_by(is_expired=False).order_by(
        LiveJob.id.desc()
    ).paginate(page=page, per_page=20)

    saved_job_ids = set()
    applied_job_ids = set()
    if current_user.is_authenticated:
        saved_job_ids = {
            saved.live_job_id
            for saved in SavedJob.query.filter_by(user_id=current_user.id).all()
        }
        applied_job_ids = {
            app.job_id
            for app in TrackedApplication.query.filter_by(
                student_id=current_user.id,
                application_type='job'
            ).all()
            if app.job_id
        }

    # Build user skills list once
    user_skills = []
    if current_user.skills:
        user_skills = [
            skill.strip().lower()
            for skill in current_user.skills.split(',')
        ]

    # Compute match score and skill tags for every job
    for job in live_jobs.items:
        job_text = ((job.title or '') + ' ' + (job.description or '')).lower()
        matched_skills = sum(1 for sk in user_skills if sk in job_text)
        job.match_score = int((matched_skills / len(user_skills)) * 100) if user_skills else 0
        job.skill_tags = [skill for skill in SKILLS if skill.lower() in job_text][:5]

    live_jobs.items.sort(key=lambda x: getattr(x, 'match_score', 0), reverse=True)

    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'explore_jobs.html',
        live_jobs=live_jobs,
        saved_job_ids=saved_job_ids,
        applied_job_ids=applied_job_ids,
        now=datetime.utcnow(),
        skill_options=SKILLS,
        unread_messages_count=unread_messages_count,
        active_filters={
            'search': '', 'location': '', 'role': '', 'job_type': '',
            'salary_min': '', 'salary_max': '', 'experience': '',
            'date_posted': '', 'skill': ''
        }
    )

@student_bp.route('/job/<int:job_id>')
@login_required
def job_details(job_id):

    job = Job.query.get_or_404(job_id)

    return render_template(
        'job_details.html',
        job=job
    )

@student_bp.route('/save-job/<int:job_id>', methods=['POST'])
@login_required
def save_job(job_id):

    existing_job = SavedJob.query.filter_by(
        user_id=current_user.id,
        live_job_id=job_id
    ).first()

    if existing_job:

        db.session.delete(existing_job)

        db.session.commit()

        # Keep calendar in sync
        try:
            sync_student_events(current_user.id)
        except Exception as sync_err:
            print(f"Calendar sync warning on job unsave: {sync_err}")

        flash('Job removed from saved jobs.', 'info')

    else:

        new_saved_job = SavedJob(
            user_id=current_user.id,
            live_job_id=job_id
        )

        db.session.add(new_saved_job)

        db.session.commit()

        # Keep calendar in sync
        try:
            sync_student_events(current_user.id)
        except Exception as sync_err:
            print(f"Calendar sync warning on job save: {sync_err}")

        flash('Job saved successfully!', 'success')

    return redirect(request.referrer or url_for('student.jobs_list'))

@student_bp.route('/saved-jobs')
@login_required
def saved_jobs():

    saved_jobs = SavedJob.query.filter_by(
        user_id=current_user.id
    ).all()

    saved_live_jobs = []

    for saved in saved_jobs:

        live_job = LiveJob.query.get(saved.live_job_id)

        if live_job:
            saved_live_jobs.append(live_job)

    return render_template(
        'saved_jobs.html',
        saved_live_jobs=saved_live_jobs
    )

@student_bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply_job(job_id):
    if current_user.is_admin:
        flash("Administrators cannot apply to job listings.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    job = Job.query.get_or_404(job_id)

    # Check duplicate application
    existing_app = Application.query.filter_by(
        student_id=current_user.id,
        job_id=job.id
    ).first()

    if existing_app:
        flash(
            f"You have already applied for the {job.role} position at {job.company_name}.",
            "warning"
        )
        return redirect(url_for('student.dashboard'))

    # Check deadline
    if job.last_date < datetime.now().date():
        flash("The application deadline for this position has passed.", "danger")
        return redirect(url_for('student.dashboard'))

    # Check resume uploaded
    if not current_user.resume_filename and not current_user.resume_link:
        flash("Please upload your resume before applying.", "warning")
        return redirect(url_for('student.profile'))

    try:
        new_application = Application(
            student_id=current_user.id,
            job_id=job.id,
            status='Applied'
        )
        db.session.add(new_application)
        db.session.commit()

        # Confirmation inbox message
        confirm_subject = f"Application Received - {job.role} ({job.company_name})"
        confirm_body = (
            f"Hi {current_user.name},\n\n"
            f"Thank you for applying for the position of {job.role} at {job.company_name}.\n"
            f"We have received your application successfully.\n\n"
            f"Track your application status in the 'My Applications' tab.\n\n"
            f"Best Regards,\n"
            f"CareerConnect Team"
        )

        new_msg = Message(
            student_id=current_user.id,
            subject=confirm_subject,
            body=confirm_body,
            sent_at=datetime.utcnow()
        )
        db.session.add(new_msg)
        db.session.commit()

        flash("Application submitted successfully!", "success")

    except Exception as e:
        db.session.rollback()
        flash("Failed to submit application.", "danger")
        print("Application error:", str(e))

    return redirect(url_for('student.dashboard'))


@student_bp.route('/internships')
@login_required
def internships():

    # =========================
    # GET ALL FILTER VALUES
    # =========================
    search      = request.args.get('search', '')
    location    = request.args.get('location', '')
    role        = request.args.get('role', '')
    internship_type = request.args.get('internship_type', '')
    date_posted = request.args.get('date_posted', '')
    skill_filter = request.args.get('skill', '')
    page        = request.args.get('page', 1, type=int)

    # Experience and salary filters passed visually
    experience  = request.args.get('experience', '')
    salary_min  = request.args.get('salary_min', '')
    salary_max  = request.args.get('salary_max', '')

    # =========================
    # BUILD QUERY
    # =========================
    query = LiveInternship.query.filter_by(is_expired=False)

    if search:
        query = query.filter(
            LiveInternship.title.ilike(f"%{search}%") |
            LiveInternship.company.ilike(f"%{search}%")
        )

    if location:
        query = query.filter(LiveInternship.location.ilike(f"%{location}%"))

    if role:
        query = query.filter(LiveInternship.title.ilike(f"%{role}%"))

    if internship_type:
        if internship_type.lower() == 'remote':
            query = query.filter(
                LiveInternship.location.ilike('%remote%') |
                LiveInternship.internship_type.ilike('%remote%')
            )
        else:
            query = query.filter(LiveInternship.internship_type.ilike(f"%{internship_type}%"))

    if date_posted:
        from datetime import timedelta
        now_dt = datetime.utcnow()
        if date_posted == 'today':
            query = query.filter(LiveInternship.created_at >= now_dt - timedelta(days=1))
        elif date_posted == 'week':
            query = query.filter(LiveInternship.created_at >= now_dt - timedelta(days=7))
        elif date_posted == 'month':
            query = query.filter(LiveInternship.created_at >= now_dt - timedelta(days=30))

    if skill_filter:
        query = query.filter(
            LiveInternship.title.ilike(f"%{skill_filter}%") |
            LiveInternship.description.ilike(f"%{skill_filter}%")
        )

    # =========================
    # PAGINATE
    # =========================
    internships = query.order_by(
        LiveInternship.created_at.desc()
    ).paginate(page=page, per_page=20)

    # =========================
    # MATCH SCORE + SKILL TAGS (runs for EVERY internship)
    # =========================
    user_skills = []
    if current_user.skills:
        user_skills = [
            sk.strip().lower() for sk in current_user.skills.split(',')
        ]

    for item in internships.items:
        desc_text = item.description or ''
        title_text = item.title or ''
        item_text = (title_text + ' ' + desc_text).lower()
        matched = sum(1 for sk in user_skills if sk in item_text)
        item.match_score = int((matched / len(user_skills)) * 100) if user_skills else 0
        item.skill_tags  = [s for s in SKILLS if s.lower() in item_text][:5]

    internships.items.sort(key=lambda x: getattr(x, 'match_score', 0), reverse=True)

    # =========================
    # APPLIED INTERNSHIP IDS
    # =========================
    applied_internship_ids = set()
    if current_user.is_authenticated:
        applied_internship_ids = {
            app.internship_id
            for app in TrackedApplication.query.filter_by(
                student_id=current_user.id,
                application_type='internship'
            ).all()
            if app.internship_id
        }

    # =========================
    # SAVED INTERNSHIP IDS
    # =========================
    saved_internship_ids = set()
    if current_user.is_authenticated:
        saved_internships = SavedInternship.query.filter_by(user_id=current_user.id).all()
        saved_internship_ids = {si.live_internship_id for si in saved_internships}

    # =========================
    # UNREAD MESSAGES
    # =========================
    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'internships.html',
        internships=internships,
        applied_internship_ids=applied_internship_ids,
        saved_internship_ids=saved_internship_ids,
        now=datetime.utcnow(),
        skill_options=SKILLS,
        unread_messages_count=unread_messages_count,
        active_filters={
            'search': search, 'location': location, 'role': role,
            'internship_type': internship_type, 'date_posted': date_posted,
            'skill': skill_filter, 'experience': experience,
            'salary_min': salary_min, 'salary_max': salary_max
        }
    )

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        experience = request.form.get('experience', '').strip()
        bio = request.form.get('bio', '').strip()
        skills = request.form.get('skills', '').strip()
        certifications = request.form.get('certifications', '').strip()
        resume_link = request.form.get('resume_link', '').strip()
        portfolio_url = request.form.get('portfolio_url', '').strip()
        github_url = request.form.get('github_url', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()

        if not name:
            flash("Full name is required.", "danger")
            return redirect(url_for('student.profile'))

        current_user.name = name
        current_user.phone = phone
        current_user.location = location
        current_user.experience = experience
        current_user.bio = bio
        current_user.skills = skills
        current_user.certifications = certifications
        current_user.resume_link = resume_link
        current_user.portfolio_url = portfolio_url
        current_user.github_url = github_url
        current_user.linkedin_url = linkedin_url

        try:
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Failed to update profile. Please try again.", "danger")
            print("Profile update error:", str(e))

        return redirect(url_for('student.profile'))

    profile_completion = get_profile_completion(current_user)
    return render_template('profile.html', profile_completion=profile_completion)

@student_bp.route('/profile/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    if 'resume_file' not in request.files:
        flash("No file part selected.", "danger")
        return redirect(url_for('student.profile'))

    file = request.files['resume_file']
    if file.filename == '':
        flash("No selected file.", "danger")
        return redirect(url_for('student.profile'))

    if file and allowed_file(file.filename):
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        new_filename = secure_filename(f"resume_user_{current_user.id}_{int(datetime.now().timestamp())}.{original_ext}")

        upload_folder = os.path.join(current_app.root_path, 'uploads', 'resumes')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file.save(os.path.join(upload_folder, new_filename))

        current_user.resume_filename = new_filename
        current_user.resume_link = url_for('student.download_own_resume')

        try:
            db.session.commit()
            flash("Resume uploaded successfully! Your profile completion has improved.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Failed to save resume. Please try again.", "danger")
            print(str(e))
    else:
        flash("Invalid file format. Only PDF files are allowed.", "danger")

    return redirect(url_for('student.profile'))

@student_bp.route('/profile/download-resume')
@login_required
def download_own_resume():
    if not current_user.resume_filename:
        flash("No uploaded resume found.", "warning")
        return redirect(url_for('student.profile'))

    upload_folder = os.path.join(current_app.root_path, 'uploads', 'resumes')
    return send_from_directory(upload_folder, current_user.resume_filename, as_attachment=True)

@student_bp.route('/jobs')
@login_required
def jobs_list():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    # =========================
    # GET ALL FILTER VALUES
    # =========================
    search      = request.args.get('search', '')
    location    = request.args.get('location', '')
    role        = request.args.get('role', '')
    job_type    = request.args.get('job_type', '')
    salary_min  = request.args.get('salary_min', '')
    salary_max  = request.args.get('salary_max', '')
    experience  = request.args.get('experience', '')
    date_posted = request.args.get('date_posted', '')
    skill_filter = request.args.get('skill', '')
    page        = request.args.get('page', 1, type=int)

    # =========================
    # BUILD QUERY
    # =========================
    query = LiveJob.query.filter_by(is_expired=False)

    if search:
        query = query.filter(
            LiveJob.title.ilike(f"%{search}%") |
            LiveJob.company.ilike(f"%{search}%")
        )

    if location:
        query = query.filter(LiveJob.location.ilike(f"%{location}%"))

    if role:
        query = query.filter(LiveJob.title.ilike(f"%{role}%"))

    if job_type:
        query = query.filter(LiveJob.job_type.ilike(f"%{job_type}%"))

    if salary_min:
        try:
            query = query.filter(LiveJob.salary_min >= int(salary_min))
        except (ValueError, TypeError):
            pass

    if salary_max:
        try:
            query = query.filter(LiveJob.salary_max <= int(salary_max))
        except (ValueError, TypeError):
            pass

    if experience and experience != 'Any':
        query = query.filter(LiveJob.experience_required.ilike(f"%{experience}%"))

    if date_posted:
        from datetime import timedelta
        now_dt = datetime.utcnow()
        if date_posted == 'today':
            query = query.filter(LiveJob.updated_at >= now_dt - timedelta(days=1))
        elif date_posted == 'week':
            query = query.filter(LiveJob.updated_at >= now_dt - timedelta(days=7))
        elif date_posted == 'month':
            query = query.filter(LiveJob.updated_at >= now_dt - timedelta(days=30))

    if skill_filter:
        query = query.filter(
            LiveJob.title.ilike(f"%{skill_filter}%") |
            LiveJob.description.ilike(f"%{skill_filter}%")
        )

    # =========================
    # PAGINATE
    # =========================
    live_jobs = query.order_by(
        LiveJob.updated_at.desc()
    ).paginate(page=page, per_page=20)

    # =========================
    # SAVED JOB IDS
    # =========================
    saved_job_ids = set()
    applied_job_ids = set()
    if current_user.is_authenticated:
        saved_job_ids = {
            saved.live_job_id
            for saved in SavedJob.query.filter_by(user_id=current_user.id).all()
        }
        applied_job_ids = {
            app.job_id
            for app in TrackedApplication.query.filter_by(
                student_id=current_user.id,
                application_type='job'
            ).all()
            if app.job_id
        }

    # =========================
    # MATCH SCORE + SKILL TAGS (fixed: runs for EVERY job)
    # =========================
    user_skills = []
    if current_user.skills:
        user_skills = [
            sk.strip().lower() for sk in current_user.skills.split(',')
        ]

    for job in live_jobs.items:
        job_text = ((job.title or '') + ' ' + (job.description or '')).lower()
        matched = sum(1 for sk in user_skills if sk in job_text)
        job.match_score = int((matched / len(user_skills)) * 100) if user_skills else 0
        job.skill_tags  = [s for s in SKILLS if s.lower() in job_text][:5]

    live_jobs.items.sort(key=lambda x: getattr(x, 'match_score', 0), reverse=True)

    # =========================
    # UNREAD MESSAGES
    # =========================
    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'explore_jobs.html',
        live_jobs=live_jobs,
        saved_job_ids=saved_job_ids,
        applied_job_ids=applied_job_ids,
        now=datetime.utcnow(),
        skill_options=SKILLS,
        unread_messages_count=unread_messages_count,
        active_filters={
            'search': search, 'location': location, 'role': role,
            'job_type': job_type, 'salary_min': salary_min,
            'salary_max': salary_max, 'experience': experience,
            'date_posted': date_posted, 'skill': skill_filter
        }
    )


def send_tracked_application_email(student, role_title, company_name, applied_date):
    """Sends a professional HTML tracked application confirmation email."""
    try:
        msg = MailMessage(
            subject="Application Tracked Successfully",
            recipients=[student.email]
        )
        msg.html = render_template(
            'emails/tracked_application_confirmation.html',
            student=student,
            role_title=role_title,
            company_name=company_name,
            applied_at=applied_date
        )
        mail.send(msg)
        print(f"SMTP Email successfully sent to {student.email}")
        return True
    except Exception as e:
        print(f"SMTP Mail dispatch failed (Check .env configuration): {str(e)}")
        return False


@student_bp.route('/api/applications', methods=['POST'])
@login_required
def api_create_application():
    if current_user.is_admin:
        return {"success": False, "message": "Admin cannot apply."}, 403

    data = request.get_json() or {}
    job_id = data.get('jobId')
    internship_id = data.get('internshipId')
    company_name = data.get('companyName')
    role_title = data.get('roleTitle')
    application_type = data.get('applicationType')  # "job" or "internship"

    if not company_name or not role_title or not application_type:
        return {"success": False, "message": "Missing required fields."}, 400

    if application_type not in ['job', 'internship']:
        return {"success": False, "message": "Invalid application type."}, 400

    # Prevent duplicates
    dup_query = TrackedApplication.query.filter_by(
        student_id=current_user.id,
        application_type=application_type
    )
    if application_type == 'job' and job_id:
        dup_query = dup_query.filter_by(job_id=int(job_id))
    elif application_type == 'internship' and internship_id:
        dup_query = dup_query.filter_by(internship_id=int(internship_id))
    else:
        return {"success": False, "message": "Missing job/internship ID."}, 400

    existing = dup_query.first()
    if existing:
        return {"success": False, "message": "Already Applied"}, 400

    try:
        new_app = TrackedApplication(
            student_id=current_user.id,
            job_id=int(job_id) if (application_type == 'job' and job_id) else None,
            internship_id=int(internship_id) if (application_type == 'internship' and internship_id) else None,
            company_name=company_name,
            role_title=role_title,
            application_type=application_type,
            status='Applied',
            applied_at=datetime.utcnow()
        )
        db.session.add(new_app)
        db.session.commit()

        # Send confirmation email
        send_tracked_application_email(current_user, role_title, company_name, new_app.applied_at)

        return {
            "success": True,
            "message": "Application tracked successfully!",
            "application": {
                "id": new_app.id,
                "company_name": new_app.company_name,
                "role_title": new_app.role_title,
                "application_type": new_app.application_type,
                "status": new_app.status,
                "applied_at": new_app.applied_at.isoformat()
            }
        }, 201

    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Server error: {str(e)}"}, 500


@student_bp.route('/api/applications', methods=['GET'])
@login_required
def api_get_applications():
    apps = TrackedApplication.query.filter_by(student_id=current_user.id).order_by(TrackedApplication.applied_at.desc()).all()
    return {
        "success": True,
        "applications": [
            {
                "id": a.id,
                "job_id": a.job_id,
                "internship_id": a.internship_id,
                "company_name": a.company_name,
                "role_title": a.role_title,
                "application_type": a.application_type,
                "status": a.status,
                "applied_at": a.applied_at.isoformat()
            } for a in apps
        ]
    }


@student_bp.route('/api/applications/status', methods=['GET'])
@login_required
def api_check_application_status():
    job_id = request.args.get('jobId')
    internship_id = request.args.get('internshipId')
    app_type = request.args.get('applicationType')

    if not app_type:
        return {"success": False, "message": "applicationType is required."}, 400

    query = TrackedApplication.query.filter_by(student_id=current_user.id, application_type=app_type)
    if app_type == 'job' and job_id:
        query = query.filter_by(job_id=int(job_id))
    elif app_type == 'internship' and internship_id:
        query = query.filter_by(internship_id=int(internship_id))
    else:
        return {"success": False, "message": "Missing job/internship ID."}, 400

    app = query.first()
    return {"success": True, "applied": app is not None, "status": app.status if app else None}


@student_bp.route('/api/applications/<int:app_id>', methods=['DELETE'])
@login_required
def api_delete_application(app_id):
    app = TrackedApplication.query.filter_by(id=app_id, student_id=current_user.id).first()
    if not app:
        return {"success": False, "message": "Application not found."}, 404

    try:
        db.session.delete(app)
        db.session.commit()
        return {"success": True, "message": "Application deleted successfully."}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "message": f"Server error: {str(e)}"}, 500


@student_bp.route('/applications')
@login_required
def my_applications():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    active_pipeline_id = request.args.get('active_pipeline', '').strip()

    applications = Application.query.filter_by(student_id=current_user.id).order_by(Application.applied_at.desc()).all()
    tracked_applications = TrackedApplication.query.filter_by(student_id=current_user.id).order_by(TrackedApplication.applied_at.desc()).all()

    selected_app = None
    if active_pipeline_id:
        try:
            selected_app = Application.query.filter_by(id=int(active_pipeline_id), student_id=current_user.id).first()
        except (ValueError, TypeError):
            pass

    if not selected_app and applications:
        selected_app = applications[0]

    return render_template(
        'applications.html',
        applications=applications,
        tracked_applications=tracked_applications,
        selected_app=selected_app
    )

@student_bp.route('/companies')
@login_required
def companies_list():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    search_query = request.args.get('search', '').strip()
    news_search = request.args.get('news_search', '').strip()

    all_companies = [
        {"name": "Google", "industry": "Technology & AI", "hq": "Mountain View, CA", "size": "150,000+", "about": "Google is a leading global technology company specializing in internet services, cloud architecture, and AI."},
        {"name": "Microsoft", "industry": "Enterprise Software & Cloud Systems", "hq": "Redmond, WA", "size": "220,000+", "about": "Microsoft enables digital transformation with Azure cloud computing, productivity suites, and development tooling."},
        {"name": "NVIDIA", "industry": "Parallel Processing & Accelerated Hardware", "hq": "Santa Clara, CA", "size": "26,000+", "about": "NVIDIA pioneered accelerated GPU computing systems driving graphics, gaming, parallel computations, and generative AI models."},
        {"name": "Stripe", "industry": "Financial Tech & Web Infrastructure", "hq": "San Francisco, CA", "size": "8,000+", "about": "Stripe runs financial transaction and routing APIs for internet businesses around the world."},
        {"name": "Adobe", "industry": "Digital Media & Creative Platforms", "hq": "San Jose, CA", "size": "29,000+", "about": "Adobe constructs digital content creations suites, creative clouds, and digital analytics services."},
        {"name": "Tesla", "industry": "Sustainable Transit & Autopilot Systems", "hq": "Austin, TX", "size": "140,000+", "about": "Tesla designs electric vehicles, battery grid storages, solar devices, and automated driving hardware."}
    ]

    # Calculate active roles dynamically and find matches
    filtered_companies = []
    for comp in all_companies:
        comp['open_roles'] = LiveJob.query.filter(LiveJob.company.ilike(f"%{comp['name']}%")).count()
        
        # Get cached or real-time news highlights (2 items)
        news, _ = get_company_news(comp['name'])
        
        # Filter highlights if news_search is active
        if news_search:
            matched_news = [n for n in news if news_search.lower() in n['title'].lower() or news_search.lower() in (n['summary'] or '').lower()]
            comp['news_highlights'] = matched_news[:2]
            comp['has_matching_news'] = len(matched_news) > 0
        else:
            comp['news_highlights'] = news[:2] if news else []
            comp['has_matching_news'] = True
            
        # Match company search filters
        matches_search = True
        if search_query:
            q = search_query.lower()
            matches_search = (q in comp['name'].lower() or q in comp['industry'].lower() or q in comp['about'].lower())
            
        # Keep if matches search and has matching news (if news search is active)
        if matches_search and (not news_search or comp['has_matching_news']):
            filtered_companies.append(comp)

    # Sort trending list by active vacancies
    trending_companies = sorted(
        [{"name": c["name"], "industry": c["industry"], "open_roles": c["open_roles"]} for c in all_companies],
        key=lambda x: x["open_roles"],
        reverse=True
    )[:3]

    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'companies.html',
        companies=filtered_companies,
        trending_companies=trending_companies,
        search_query=search_query,
        news_search=news_search,
        unread_messages_count=unread_messages_count
    )


@student_bp.route('/company/<company_name>')
@login_required
def company_details(company_name):
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    all_companies = {
        "Google": {"name": "Google", "industry": "Technology & AI", "hq": "Mountain View, CA", "size": "150,000+", "about": "Google is a leading global technology company specializing in internet services, cloud architecture, and AI.", "website": "https://about.google"},
        "Microsoft": {"name": "Microsoft", "industry": "Enterprise Software & Cloud Systems", "hq": "Redmond, WA", "size": "220,000+", "about": "Microsoft enables digital transformation with Azure cloud computing, productivity suites, and development tooling.", "website": "https://www.microsoft.com"},
        "NVIDIA": {"name": "NVIDIA", "industry": "Parallel Processing & Accelerated Hardware", "hq": "Santa Clara, CA", "size": "26,000+", "about": "NVIDIA pioneered accelerated GPU computing systems driving graphics, gaming, parallel computations, and generative AI models.", "website": "https://www.nvidia.com"},
        "Stripe": {"name": "Stripe", "industry": "Financial Tech & Web Infrastructure", "hq": "San Francisco, CA", "size": "8,000+", "about": "Stripe runs financial transaction and routing APIs for internet businesses around the world.", "website": "https://stripe.com"},
        "Adobe": {"name": "Adobe", "industry": "Digital Media & Creative Platforms", "hq": "San Jose, CA", "size": "29,000+", "about": "Adobe constructs digital content creations suites, creative clouds, and digital analytics services.", "website": "https://www.adobe.com"},
        "Tesla": {"name": "Tesla", "industry": "Sustainable Transit & Autopilot Systems", "hq": "Austin, TX", "size": "140,000+", "about": "Tesla designs electric vehicles, battery grid storages, solar devices, and automated driving hardware.", "website": "https://www.tesla.com"}
    }

    # Match case insensitively
    matched_key = None
    for key in all_companies:
        if key.lower() == company_name.lower():
            matched_key = key
            break

    if not matched_key:
        company = {
            "name": company_name,
            "industry": "Corporate Partner",
            "hq": "Global Operations",
            "size": "N/A",
            "about": f"{company_name} is a verified recruiting associate on CareerConnect, committed to finding top-tier student talent.",
            "website": "#"
        }
    else:
        company = all_companies[matched_key]

    news_search = request.args.get('news_search', '').strip()
    news_articles, _ = get_company_news(company['name'])

    if news_search:
        news_articles = [n for n in news_articles if news_search.lower() in n['title'].lower() or news_search.lower() in (n['summary'] or '').lower()]

    # Map bookmarks
    bookmarked_urls = {b.url for b in BookmarkedNews.query.filter_by(student_id=current_user.id).all()}
    for art in news_articles:
        art['is_bookmarked'] = art['url'] in bookmarked_urls

    open_jobs = LiveJob.query.filter(LiveJob.company.ilike(f"%{company['name']}%")).all()

    # Get trending companies for sidebar
    trending_companies = []
    for name, details in all_companies.items():
        job_count = LiveJob.query.filter(LiveJob.company.ilike(f"%{name}%")).count()
        trending_companies.append({
            "name": name,
            "industry": details["industry"],
            "open_roles": job_count
        })
    trending_companies = sorted(trending_companies, key=lambda x: x["open_roles"], reverse=True)[:3]

    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'company_details.html',
        company=company,
        news_articles=news_articles,
        open_jobs=open_jobs,
        trending_companies=trending_companies,
        news_search=news_search,
        unread_messages_count=unread_messages_count
    )


@student_bp.route('/company/<company_name>/refresh', methods=['POST'])
@login_required
def refresh_company_news(company_name):
    if current_user.is_admin:
        return {"success": False, "message": "Admin cannot refresh news"}, 403

    try:
        get_company_news(company_name, force_refresh=True)
        flash(f"News feed for {company_name} updated successfully!", "success")
        return {"success": True, "message": f"News feed for {company_name} updated."}
    except Exception as e:
        print(f"Error refreshing news for {company_name}: {str(e)}")
        return {"success": False, "message": "Failed to update news feed."}, 500


@student_bp.route('/company/news/bookmark', methods=['POST'])
@login_required
def toggle_bookmark_news():
    if current_user.is_admin:
        return {"success": False, "message": "Admin cannot bookmark news"}, 403

    data = request.get_json() or {}
    company_name = data.get('company_name', '').strip()
    title = data.get('title', '').strip()
    source = data.get('source', '').strip()
    published_at = data.get('published_at', '').strip()
    summary = data.get('summary', '').strip()
    url = data.get('url', '').strip()

    if not (company_name and title and url):
        return {"success": False, "message": "Missing required fields"}, 400

    existing = BookmarkedNews.query.filter_by(
        student_id=current_user.id,
        url=url
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return {"success": True, "bookmarked": False, "message": "Bookmark removed"}
    else:
        new_bookmark = BookmarkedNews(
            student_id=current_user.id,
            company_name=company_name,
            title=title,
            source=source,
            published_at=published_at,
            summary=summary,
            url=url
        )
        db.session.add(new_bookmark)
        db.session.commit()
        return {"success": True, "bookmarked": True, "message": "Bookmark added"}


@student_bp.route('/companies/bookmarks')
@login_required
def bookmarked_news_list():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    search_query = request.args.get('search', '').strip()

    query = BookmarkedNews.query.filter_by(student_id=current_user.id)
    if search_query:
        query = query.filter(
            BookmarkedNews.title.ilike(f"%{search_query}%") |
            BookmarkedNews.company_name.ilike(f"%{search_query}%") |
            BookmarkedNews.summary.ilike(f"%{search_query}%")
        )

    bookmarks = query.order_by(BookmarkedNews.created_at.desc()).all()

    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'bookmarked_news.html',
        bookmarks=bookmarks,
        search_query=search_query,
        unread_messages_count=unread_messages_count
    )

@student_bp.route('/messages')
@login_required
def messages_inbox():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    active_msg_id = request.args.get('active_msg', '').strip()

    messages = Message.query.filter_by(student_id=current_user.id).order_by(Message.sent_at.desc()).all()

    selected_msg = None
    if active_msg_id:
        try:
            selected_msg = Message.query.filter_by(id=int(active_msg_id), student_id=current_user.id).first()
            if selected_msg and not selected_msg.is_read:
                selected_msg.is_read = True
                db.session.commit()
        except (ValueError, TypeError):
            pass

    if not selected_msg and messages:
        selected_msg = messages[0]
        if selected_msg and not selected_msg.is_read:
            selected_msg.is_read = True
            db.session.commit()

    return render_template(
        'messages.html',
        messages=messages,
        selected_msg=selected_msg
    )

@student_bp.route('/calendar')
@login_required
def calendar_view():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))

    # Sync events first
    sync_student_events(current_user.id)

    unread_messages_count = Message.query.filter_by(
        student_id=current_user.id, is_read=False
    ).count()

    return render_template(
        'calendar.html',
        unread_messages_count=unread_messages_count
    )


@student_bp.route('/api/calendar/events')
@login_required
def api_calendar_events():
    if current_user.is_admin:
        return {"success": False, "message": "Admin cannot view calendar events."}, 403

    sync_student_events(current_user.id)
    events = PlacementEvent.query.filter_by(user_id=current_user.id).order_by(PlacementEvent.event_date.asc()).all()

    today = datetime.now()
    serialized = []
    
    color_map = {
        'Google': 'google',
        'Microsoft': 'microsoft',
        'Stripe': 'stripe',
        'NVIDIA': 'nvidia',
        'Adobe': 'adobe',
        'Tesla': 'tesla',
        'Airbnb': 'airbnb',
        'Uber': 'uber',
        'Amazon': 'amazon',
        'Meta': 'meta'
    }

    for ev in events:
        days_remaining = (ev.event_date.date() - today.date()).days
        
        # Priority calculation
        if days_remaining <= 3:
            priority = "High"
        elif days_remaining <= 7:
            priority = "Medium"
        else:
            priority = "Low"

        # Resolve location dynamically from sources
        location = "Not Specified"
        if ev.source_type == 'saved_job' and ev.source_id:
            sj = SavedJob.query.get(ev.source_id)
            if sj and sj.live_job:
                location = sj.live_job.location or "Not Specified"
        elif ev.source_type == 'saved_internship' and ev.source_id:
            si = SavedInternship.query.get(ev.source_id)
            if si and si.live_internship:
                location = si.live_internship.location or "Not Specified"
        elif ev.source_type == 'applied_job' and ev.source_id:
            app = Application.query.get(ev.source_id)
            if app and app.job:
                location = app.job.location or "Not Specified"
        elif ev.source_type == 'applied_tracked' and ev.source_id:
            ta = TrackedApplication.query.get(ev.source_id)
            if ta:
                if ta.application_type == 'job' and ta.job_id:
                    lj = LiveJob.query.get(ta.job_id)
                    if lj:
                        location = lj.location or "Not Specified"
                elif ta.application_type == 'internship' and ta.internship_id:
                    li = LiveInternship.query.get(ta.internship_id)
                    if li:
                        location = li.location or "Not Specified"

        serialized.append({
            "id": ev.id,
            "companyName": ev.company_name,
            "roleTitle": ev.role_title,
            "eventType": ev.event_type,
            "eventDate": ev.event_date.isoformat(),
            "description": ev.description,
            "applicationUrl": ev.application_url,
            "location": location,
            "daysRemaining": days_remaining,
            "priority": priority,
            "colorClass": color_map.get(ev.company_name, 'primary')
        })

    return {"success": True, "events": serialized}


@student_bp.route('/api/save-internship/<int:internship_id>', methods=['POST'])
@login_required
def api_save_internship(internship_id):
    if current_user.is_admin:
        return {"success": False, "message": "Admin cannot save internships."}, 403

    existing = SavedInternship.query.filter_by(
        user_id=current_user.id,
        live_internship_id=internship_id
    ).first()

    if existing:
        try:
            db.session.delete(existing)
            db.session.commit()
            sync_student_events(current_user.id)
            return {"success": True, "saved": False, "message": "Internship removed from saved list."}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Server error: {str(e)}"}, 500
    else:
        new_save = SavedInternship(
            user_id=current_user.id,
            live_internship_id=internship_id
        )
        try:
            db.session.add(new_save)
            db.session.commit()
            sync_student_events(current_user.id)
            return {"success": True, "saved": True, "message": "Internship saved successfully!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": f"Server error: {str(e)}"}, 500

@student_bp.route('/settings')
@login_required
def settings_view():
    if current_user.is_admin:
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('settings.html')

@student_bp.route('/settings/password', methods=['POST'])
@login_required
def update_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_new_pw = request.form.get('confirm_new_password')

    if not (current_pw and new_pw and confirm_new_pw):
        flash("All fields are required to update your password.", "danger")
        return redirect(url_for('student.settings_view'))

    from werkzeug.security import generate_password_hash, check_password_hash
    if not check_password_hash(current_user.password_hash, current_pw):
        flash("Incorrect current password. Please try again.", "danger")
        return redirect(url_for('student.settings_view'))

    if new_pw != confirm_new_pw:
        flash("New passwords do not match.", "danger")
        return redirect(url_for('student.settings_view'))

    current_user.password_hash = generate_password_hash(new_pw, method='scrypt')
    try:
        db.session.commit()
        flash("Password updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to update password. Please try again.", "danger")
        print(str(e))

    return redirect(url_for('student.settings_view'))

@student_bp.route('/settings/notifications', methods=['POST'])
@login_required
def update_email_preferences():
    email_notif = request.form.get('email_notifications') == 'true'
    current_user.email_notifications = email_notif
    try:
        db.session.commit()
        flash("Email notification preferences updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to update notification preferences.", "danger")

    return redirect(url_for('student.settings_view'))
