import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, send_from_directory, jsonify
from flask_login import login_required, current_user
from flask_mail import Message as MailMessage
from models import db, Student, Job, Application, Message, mail, SyncLog, LiveJob, LiveInternship
from datetime import datetime
from services.calendar_service import sync_student_events
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Access denied. Administrator privileges required.", "danger")
            return redirect(url_for('student.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users_only = Student.query.filter_by(is_admin=False).order_by(Student.name.asc()).all()
    jobs = Job.query.order_by(Job.company_name.asc()).all()
    applications = Application.query.order_by(Application.applied_at.desc()).all()
    offers_count = Application.query.filter(Application.status.in_(['Offered', 'Selected'])).count()

    # Location distribution for analytics
    location_stats = {}
    for u in users_only:
        loc = u.location or 'Not Set'
        location_stats[loc] = location_stats.get(loc, 0) + 1

    # Application status funnel for Chart.js
    status_stats = {
        'Applied': 0,
        'Shortlisted': 0,
        'Interviewing': 0,
        'Offered': 0,
        'Rejected': 0
    }
    for app in applications:
        status_name = 'Offered' if app.status in ['Offered', 'Selected'] else app.status
        if status_name in status_stats:
            status_stats[status_name] += 1

    return render_template(
        'admin_dashboard.html',
        users_only=users_only,
        jobs=jobs,
        applications=applications,
        offers_count=offers_count,
        location_stats=location_stats,
        status_stats=status_stats
    )

@admin_bp.route('/admin/job/add', methods=['POST'])
@login_required
@admin_required
def add_job():
    company_name = request.form.get('company_name', '').strip()
    role = request.form.get('role', '').strip()
    package = request.form.get('package', '').strip()
    job_type = request.form.get('job_type', 'Full-Time').strip()
    last_date_str = request.form.get('last_date', '').strip()
    description = request.form.get('description', '').strip()
    location = request.form.get('location', 'Remote').strip()
    skills_required = request.form.get('skills_required', '').strip()
    drive_date_str = request.form.get('drive_date', '').strip()
    website = request.form.get('website', '').strip()
    experience_required = request.form.get('experience_required', 'Any').strip()

    if not (company_name and role and package and last_date_str and description):
        flash("All required fields must be filled to post a listing.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    try:
        last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid deadline date format.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    drive_date = None
    if drive_date_str:
        try:
            drive_date = datetime.strptime(drive_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    new_job = Job(
        company_name=company_name,
        role=role,
        package=package,
        job_type=job_type,
        last_date=last_date,
        description=description,
        location=location,
        skills_required=skills_required,
        drive_date=drive_date,
        experience_required=experience_required,
        about_company=f"{company_name} is a forward-thinking company offering exceptional career opportunities and professional growth.",
        website=website
    )

    try:
        db.session.add(new_job)
        db.session.commit()

        # Broadcast to all users
        users = Student.query.filter_by(is_admin=False).all()
        for usr in users:
            broad_msg = Message(
                student_id=usr.id,
                subject=f"New {job_type} opportunity posted by {company_name}!",
                body=(
                    f"Dear {usr.name},\n\n"
                    f"A new {job_type} listing has been posted on CareerConnect:\n\n"
                    f"- Company: {company_name}\n"
                    f"- Position: {role}\n"
                    f"- Compensation: {package}\n"
                    f"- Type: {job_type}\n"
                    f"- Location: {location}\n"
                    f"- Experience: {experience_required}\n"
                    f"- Deadline: {last_date.strftime('%d %b %Y')}\n\n"
                    f"Visit the Jobs page to apply now!"
                ),
                sent_at=datetime.utcnow()
            )
            db.session.add(broad_msg)

        db.session.commit()
        flash(f"New {job_type} listing posted and broadcasted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to add job listing.", "danger")
        print("Add job error:", str(e))

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/job/edit/<int:job_id>', methods=['POST'])
@login_required
@admin_required
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)

    job.company_name = request.form.get('company_name', job.company_name)
    job.role = request.form.get('role', job.role)
    job.package = request.form.get('package', job.package)
    job.job_type = request.form.get('job_type', job.job_type)
    job.location = request.form.get('location', job.location)
    job.skills_required = request.form.get('skills_required', job.skills_required)
    job.website = request.form.get('website', job.website)
    job.description = request.form.get('description', job.description)
    job.experience_required = request.form.get('experience_required', job.experience_required)

    last_date_str = request.form.get('last_date', '')
    drive_date_str = request.form.get('drive_date', '')

    try:
        if last_date_str:
            job.last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        if drive_date_str:
            job.drive_date = datetime.strptime(drive_date_str, '%Y-%m-%d').date()
        db.session.commit()
        flash(f"Job listing for {job.company_name} updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to update job details.", "danger")
        print(str(e))

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/job/delete/<int:job_id>', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    try:
        db.session.delete(job)
        db.session.commit()
        flash(f"Job listing for {job.company_name} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete job listing.", "danger")
        print(str(e))
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/user/edit/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def edit_student(student_id):
    user = Student.query.get_or_404(student_id)
    user.name = request.form.get('name', user.name)
    user.location = request.form.get('location', user.location)
    user.experience = request.form.get('experience', user.experience)

    try:
        db.session.commit()
        flash(f"Profile for {user.name} updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to update user profile.", "danger")
        print(str(e))

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/user/delete/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    user = Student.query.get_or_404(student_id)
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f"User account for {user.name} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete user.", "danger")
        print(str(e))
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/application/status/<int:app_id>', methods=['POST'])
@login_required
@admin_required
def update_status(app_id):
    app_record = Application.query.get_or_404(app_id)
    new_status = request.form.get('status')

    valid_statuses = ['Applied', 'Shortlisted', 'Interviewing', 'Offered', 'Selected', 'Rejected']
    if new_status not in valid_statuses:
        flash("Invalid application status.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    app_record.status = new_status

    try:
        db.session.commit()

        status_subject = f"Application Update: {app_record.job.role} at {app_record.job.company_name}"
        status_body = (
            f"Hi {app_record.student.name},\n\n"
            f"Your application for {app_record.job.role} at {app_record.job.company_name} "
            f"has been updated.\n\n"
            f"New Status: {new_status}\n"
            f"Updated On: {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
            f"Track your application in the 'My Applications' tab."
        )

        new_msg = Message(
            student_id=app_record.student_id,
            subject=status_subject,
            body=status_body,
            sent_at=datetime.utcnow()
        )
        db.session.add(new_msg)
        db.session.commit()

        if app_record.student.email_notifications:
            try:
                email_msg = MailMessage(
                    subject=f"CareerConnect: Application Status Updated — {app_record.job.company_name}",
                    recipients=[app_record.student.email]
                )
                email_msg.html = render_template(
                    'emails/status_update.html',
                    student=app_record.student,
                    job=app_record.job,
                    status=new_status,
                    updated_at=datetime.now()
                )
                mail.send(email_msg)
            except Exception as mail_err:
                print("Mail server error during status dispatch:", str(mail_err))

        # Trigger calendar event sync on status update
        sync_student_events(app_record.student_id)

        flash(f"Status updated to '{new_status}' for {app_record.student.name}.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to update applicant status.", "danger")
        print("Status update error:", str(e))

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/message/send', methods=['POST'])
@login_required
@admin_required
def admin_send_message():
    student_id = request.form.get('student_id')
    subject = request.form.get('subject')
    body = request.form.get('body')

    if not (student_id and subject and body):
        flash("All fields are required to send a notification.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    try:
        std_id = int(student_id)
        user = Student.query.get_or_404(std_id)

        new_msg = Message(
            student_id=user.id,
            subject=subject,
            body=body,
            sent_at=datetime.utcnow()
        )
        db.session.add(new_msg)
        db.session.commit()

        if user.email_notifications:
            try:
                email_msg = MailMessage(
                    subject=f"CareerConnect: {subject}",
                    recipients=[user.email]
                )
                email_msg.body = f"Hello {user.name},\n\nYou have received a new message from CareerConnect:\n\n---\nSubject: {subject}\n\n{body}\n---\n\nLog in to view the full message.\n\nBest Regards,\nCareerConnect Team"
                mail.send(email_msg)
            except Exception as mail_err:
                print("Announcement email failed:", str(mail_err))

        flash(f"Notification sent successfully to {user.name}!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to send notification.", "danger")
        print("Admin message send error:", str(e))

    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/admin/resume/download/<int:student_id>')
@login_required
@admin_required
def download_resume(student_id):
    user = Student.query.get_or_404(student_id)
    if not user.resume_filename:
        flash(f"{user.name} has not uploaded a PDF resume yet.", "warning")
        return redirect(url_for('admin.admin_dashboard'))

    upload_folder = os.path.join(current_app.root_path, 'uploads', 'resumes')
    return send_from_directory(upload_folder, user.resume_filename, as_attachment=True)

@admin_bp.route('/admin/broadcast-announcement', methods=['POST'])
@login_required
@admin_required
def broadcast_announcement():
    subject = request.form.get('subject')
    body = request.form.get('body')

    if not (subject and body):
        flash("Subject and body are required for broadcasting.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    recipients = Student.query.filter_by(is_admin=False).all()

    try:
        sent_count = 0
        for usr in recipients:
            db_msg = Message(
                student_id=usr.id,
                subject=subject,
                body=body,
                sent_at=datetime.utcnow()
            )
            db.session.add(db_msg)

            if usr.email_notifications:
                try:
                    email_msg = MailMessage(
                        subject=f"[CareerConnect] {subject}",
                        recipients=[usr.email]
                    )
                    email_msg.html = render_template(
                        'emails/announcement.html',
                        student=usr,
                        subject=subject,
                        body=body.replace('\n', '<br>')
                    )
                    mail.send(email_msg)
                except Exception as inner_err:
                    print(f"Failed broadcast email to {usr.email}:", str(inner_err))

            sent_count += 1

        db.session.commit()
        flash(f"Broadcast sent to {sent_count} users successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to broadcast announcement.", "danger")
        print(str(e))

    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/api/system/sync-status', methods=['GET'])
@login_required
def get_sync_status():
    from services.scheduler_service import scheduler

    # Get jobs scheduler next run time
    job_sync_job = scheduler.get_job('job_sync')
    next_jobs_sync = job_sync_job.next_run_time.isoformat() if (job_sync_job and job_sync_job.next_run_time) else None

    # Get internships scheduler next run time
    internship_sync_job = scheduler.get_job('internship_sync')
    next_internships_sync = internship_sync_job.next_run_time.isoformat() if (internship_sync_job and internship_sync_job.next_run_time) else None

    # Fetch last logs
    last_job_log = SyncLog.query.filter_by(syncType='jobs').order_by(SyncLog.startedAt.desc()).first()
    last_internship_log = SyncLog.query.filter_by(syncType='internships').order_by(SyncLog.startedAt.desc()).first()

    # Total active jobs/internships count
    total_jobs = LiveJob.query.filter_by(is_expired=False).count()
    total_internships = LiveInternship.query.filter_by(is_expired=False).count()

    # Formulate last sync results
    last_job_result = {
        'startedAt': last_job_log.startedAt.isoformat() if last_job_log else None,
        'completedAt': last_job_log.completedAt.isoformat() if (last_job_log and last_job_log.completedAt) else None,
        'status': last_job_log.status if last_job_log else 'NEVER_RUN',
        'recordsAdded': last_job_log.recordsAdded if last_job_log else 0,
        'recordsUpdated': last_job_log.recordsUpdated if last_job_log else 0,
        'recordsRemoved': last_job_log.recordsRemoved if last_job_log else 0,
        'errorMessage': last_job_log.errorMessage if last_job_log else None
    }

    last_internship_result = {
        'startedAt': last_internship_log.startedAt.isoformat() if last_internship_log else None,
        'completedAt': last_internship_log.completedAt.isoformat() if (last_internship_log and last_internship_log.completedAt) else None,
        'status': last_internship_log.status if last_internship_log else 'NEVER_RUN',
        'recordsAdded': last_internship_log.recordsAdded if last_internship_log else 0,
        'recordsUpdated': last_internship_log.recordsUpdated if last_internship_log else 0,
        'recordsRemoved': last_internship_log.recordsRemoved if last_internship_log else 0,
        'errorMessage': last_internship_log.errorMessage if last_internship_log else None
    }

    return jsonify({
        'lastJobsSyncTime': last_job_log.completedAt.isoformat() if (last_job_log and last_job_log.completedAt) else (last_job_log.startedAt.isoformat() if last_job_log else None),
        'nextJobsSyncTime': next_jobs_sync,
        'lastInternshipSyncTime': last_internship_log.completedAt.isoformat() if (last_internship_log and last_internship_log.completedAt) else (last_internship_log.startedAt.isoformat() if last_internship_log else None),
        'nextInternshipSyncTime': next_internships_sync,
        'totalJobs': total_jobs,
        'totalInternships': total_internships,
        'lastJobResult': last_job_result,
        'lastInternshipResult': last_internship_result
    })


@admin_bp.route('/api/system/trigger-sync', methods=['POST'])
@login_required
@admin_required
def trigger_sync():
    sync_type = request.json.get('syncType') if request.is_json else request.form.get('syncType')
    if sync_type == 'jobs':
        from services.job_api import JobSyncService
        res = JobSyncService.sync()
        return jsonify(res)
    elif sync_type == 'internships':
        from services.job_api import InternshipSyncService
        res = InternshipSyncService.sync()
        return jsonify(res)
    else:
        return jsonify({'status': 'FAILED', 'error': 'Invalid sync type'}), 400

