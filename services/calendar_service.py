import os
from datetime import datetime, timedelta
from flask import render_template
from flask_mail import Message as MailMessage
from models import (
    db, Student, Job, LiveJob, LiveInternship, Application,
    TrackedApplication, SavedJob, SavedInternship, PlacementEvent, Message, mail
)

def sync_student_events(student_id):
    """
    Synchronizes placement events for a given student based on their:
    - Saved Jobs
    - Saved Internships
    - Applied Jobs (Applications)
    - Applied Internships (Tracked Applications)
    Also updates/adds status-based events (Assessment, Interview, Offer)
    and removes any orphaned events.
    """
    student = Student.query.get(student_id)
    if not student:
        return

    # Keep track of active event IDs during this sync run to delete orphans later
    active_event_ids = []

    # ----------------------------------------------------
    # 1. SYNC SAVED JOBS (Application Deadline)
    # ----------------------------------------------------
    saved_jobs = SavedJob.query.filter_by(user_id=student_id).all()
    for sj in saved_jobs:
        live_job = LiveJob.query.get(sj.live_job_id)
        if not live_job:
            continue
        
        # Calculate deadline: posted_date + 14 days, or updated_at + 14 days
        base_date = live_job.posted_date or live_job.updated_at or sj.created_at
        deadline_date = base_date + timedelta(days=14)

        # Check if event already exists
        event = PlacementEvent.query.filter_by(
            user_id=student_id,
            source_type='saved_job',
            source_id=sj.id
        ).first()

        if not event:
            event = PlacementEvent(
                user_id=student_id,
                company_id=live_job.id,
                company_name=live_job.company,
                role_title=live_job.title,
                event_type='Application Deadline',
                event_date=deadline_date,
                description=f"Saved Job: Submit application for {live_job.title} at {live_job.company}.",
                application_url=live_job.apply_link or '#',
                source_type='saved_job',
                source_id=sj.id
            )
            db.session.add(event)
            db.session.flush() # Populate ID
        else:
            # Sync date/details if changed
            event.company_name = live_job.company
            event.role_title = live_job.title
            event.event_date = deadline_date
            event.application_url = live_job.apply_link or '#'

        active_event_ids.append(event.id)

    # ----------------------------------------------------
    # 2. SYNC SAVED INTERNSHIPS (Application Deadline)
    # ----------------------------------------------------
    saved_internships = SavedInternship.query.filter_by(user_id=student_id).all()
    for si in saved_internships:
        live_intern = LiveInternship.query.get(si.live_internship_id)
        if not live_intern:
            continue

        base_date = live_intern.created_at or si.created_at
        deadline_date = base_date + timedelta(days=14)

        # Check if event already exists
        event = PlacementEvent.query.filter_by(
            user_id=student_id,
            source_type='saved_internship',
            source_id=si.id
        ).first()

        if not event:
            event = PlacementEvent(
                user_id=student_id,
                company_id=live_intern.id,
                company_name=live_intern.company,
                role_title=live_intern.title,
                event_type='Application Deadline',
                event_date=deadline_date,
                description=f"Saved Internship: Submit application for {live_intern.title} at {live_intern.company}.",
                application_url=live_intern.apply_link or '#',
                source_type='saved_internship',
                source_id=si.id
            )
            db.session.add(event)
            db.session.flush()
        else:
            event.company_name = live_intern.company
            event.role_title = live_intern.title
            event.event_date = deadline_date
            event.application_url = live_intern.apply_link or '#'

        active_event_ids.append(event.id)

    # ----------------------------------------------------
    # 3. SYNC APPLIED LOCAL JOBS (Application model)
    # ----------------------------------------------------
    local_applications = Application.query.filter_by(student_id=student_id).all()
    for app in local_applications:
        job = Job.query.get(app.job_id)
        if not job:
            continue

        # A. Deadline Event
        deadline_event = PlacementEvent.query.filter_by(
            user_id=student_id,
            source_type='applied_job',
            source_id=app.id,
            event_type='Application Deadline'
        ).first()

        deadline_val = datetime.combine(job.last_date, datetime.min.time()) if job.last_date else app.applied_at + timedelta(days=14)
        if not deadline_event:
            deadline_event = PlacementEvent(
                user_id=student_id,
                company_id=job.id,
                company_name=job.company_name,
                role_title=job.role,
                event_type='Application Deadline',
                event_date=deadline_val,
                description=f"Application Deadline for {job.role} at {job.company_name}.",
                application_url=url_for_job_details(job.id),
                source_type='applied_job',
                source_id=app.id
            )
            db.session.add(deadline_event)
            db.session.flush()
        else:
            deadline_event.event_date = deadline_val
            deadline_event.company_name = job.company_name
            deadline_event.role_title = job.role
        active_event_ids.append(deadline_event.id)

        # B. Hiring Drive / Campus Placement Event
        if job.drive_date:
            drive_val = datetime.combine(job.drive_date, datetime.min.time())
            drive_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_job',
                source_id=app.id,
                event_type='Hiring Drive'
            ).first()

            if not drive_event:
                drive_event = PlacementEvent(
                    user_id=student_id,
                    company_id=job.id,
                    company_name=job.company_name,
                    role_title=job.role,
                    event_type='Hiring Drive',
                    event_date=drive_val,
                    description=f"Campus Placement Drive for {job.role} at {job.company_name}.",
                    application_url=url_for_job_details(job.id),
                    source_type='applied_job',
                    source_id=app.id
                )
                db.session.add(drive_event)
                db.session.flush()
            else:
                drive_event.event_date = drive_val
                drive_event.company_name = job.company_name
                drive_event.role_title = job.role
            active_event_ids.append(drive_event.id)

        # C. Status-Based Events (Assessment, Interview, Offer)
        # If status is "Shortlisted" -> Assessment Date
        if app.status == 'Shortlisted':
            assessment_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_job',
                source_id=app.id,
                event_type='Assessment Date'
            ).first()

            if not assessment_event:
                assessment_event = PlacementEvent(
                    user_id=student_id,
                    company_id=job.id,
                    company_name=job.company_name,
                    role_title=job.role,
                    event_type='Assessment Date',
                    event_date=app.applied_at + timedelta(days=3),
                    description=f"Technical Assessment for {job.role} at {job.company_name}.",
                    application_url=url_for_job_details(job.id),
                    source_type='applied_job',
                    source_id=app.id
                )
                db.session.add(assessment_event)
                db.session.flush()
            active_event_ids.append(assessment_event.id)

        # If status is "Interviewing" -> Interview Date
        elif app.status == 'Interviewing':
            interview_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_job',
                source_id=app.id,
                event_type='Interview Date'
            ).first()

            if not interview_event:
                interview_event = PlacementEvent(
                    user_id=student_id,
                    company_id=job.id,
                    company_name=job.company_name,
                    role_title=job.role,
                    event_type='Interview Date',
                    event_date=app.applied_at + timedelta(days=5),
                    description=f"Placement Interview Round for {job.role} at {job.company_name}.",
                    application_url=url_for_job_details(job.id),
                    source_type='applied_job',
                    source_id=app.id
                )
                db.session.add(interview_event)
                db.session.flush()
            active_event_ids.append(interview_event.id)

        # If status is "Offered" or "Selected" -> Offer Deadline
        elif app.status in ['Offered', 'Selected']:
            offer_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_job',
                source_id=app.id,
                event_type='Offer Deadline'
            ).first()

            if not offer_event:
                offer_event = PlacementEvent(
                    user_id=student_id,
                    company_id=job.id,
                    company_name=job.company_name,
                    role_title=job.role,
                    event_type='Offer Deadline',
                    event_date=app.applied_at + timedelta(days=7),
                    description=f"Response deadline for job offer from {job.company_name}.",
                    application_url=url_for_job_details(job.id),
                    source_type='applied_job',
                    source_id=app.id
                )
                db.session.add(offer_event)
                db.session.flush()
            active_event_ids.append(offer_event.id)

    # ----------------------------------------------------
    # 4. SYNC APPLIED EXTERNAL JOBS/INTERNSHIPS (TrackedApplication)
    # ----------------------------------------------------
    tracked_applications = TrackedApplication.query.filter_by(student_id=student_id).all()
    for ta in tracked_applications:
        # A. Deadline Event
        deadline_event = PlacementEvent.query.filter_by(
            user_id=student_id,
            source_type='applied_tracked',
            source_id=ta.id,
            event_type='Application Deadline'
        ).first()

        # Try to resolve deadline date
        base_date = ta.applied_at
        app_url = '#'
        if ta.application_type == 'job' and ta.job_id:
            live_job = LiveJob.query.get(ta.job_id)
            if live_job:
                base_date = live_job.posted_date or live_job.updated_at or ta.applied_at
                app_url = live_job.apply_link or '#'
        elif ta.application_type == 'internship' and ta.internship_id:
            live_intern = LiveInternship.query.get(ta.internship_id)
            if live_intern:
                base_date = live_intern.created_at or ta.applied_at
                app_url = live_intern.apply_link or '#'

        deadline_val = base_date + timedelta(days=14)

        if not deadline_event:
            deadline_event = PlacementEvent(
                user_id=student_id,
                company_id=ta.job_id or ta.internship_id,
                company_name=ta.company_name,
                role_title=ta.role_title,
                event_type='Application Deadline',
                event_date=deadline_val,
                description=f"Application Deadline for {ta.role_title} at {ta.company_name} ({ta.application_type.capitalize()}).",
                application_url=app_url,
                source_type='applied_tracked',
                source_id=ta.id
            )
            db.session.add(deadline_event)
            db.session.flush()
        else:
            deadline_event.event_date = deadline_val
            deadline_event.company_name = ta.company_name
            deadline_event.role_title = ta.role_title
            deadline_event.application_url = app_url
        active_event_ids.append(deadline_event.id)

        # B. Status-Based Events (Assessment, Interview, Offer)
        if ta.status == 'Shortlisted':
            assessment_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_tracked',
                source_id=ta.id,
                event_type='Assessment Date'
            ).first()

            if not assessment_event:
                assessment_event = PlacementEvent(
                    user_id=student_id,
                    company_id=ta.job_id or ta.internship_id,
                    company_name=ta.company_name,
                    role_title=ta.role_title,
                    event_type='Assessment Date',
                    event_date=ta.applied_at + timedelta(days=3),
                    description=f"Technical Assessment for {ta.role_title} at {ta.company_name}.",
                    application_url=app_url,
                    source_type='applied_tracked',
                    source_id=ta.id
                )
                db.session.add(assessment_event)
                db.session.flush()
            active_event_ids.append(assessment_event.id)

        elif ta.status == 'Interviewing':
            interview_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_tracked',
                source_id=ta.id,
                event_type='Interview Date'
            ).first()

            if not interview_event:
                interview_event = PlacementEvent(
                    user_id=student_id,
                    company_id=ta.job_id or ta.internship_id,
                    company_name=ta.company_name,
                    role_title=ta.role_title,
                    event_type='Interview Date',
                    event_date=ta.applied_at + timedelta(days=5),
                    description=f"Interview Round for {ta.role_title} at {ta.company_name}.",
                    application_url=app_url,
                    source_type='applied_tracked',
                    source_id=ta.id
                )
                db.session.add(interview_event)
                db.session.flush()
            active_event_ids.append(interview_event.id)

        elif ta.status in ['Offered', 'Selected']:
            offer_event = PlacementEvent.query.filter_by(
                user_id=student_id,
                source_type='applied_tracked',
                source_id=ta.id,
                event_type='Offer Deadline'
            ).first()

            if not offer_event:
                offer_event = PlacementEvent(
                    user_id=student_id,
                    company_id=ta.job_id or ta.internship_id,
                    company_name=ta.company_name,
                    role_title=ta.role_title,
                    event_type='Offer Deadline',
                    event_date=ta.applied_at + timedelta(days=7),
                    description=f"Response deadline for offer from {ta.company_name}.",
                    application_url=app_url,
                    source_type='applied_tracked',
                    source_id=ta.id
                )
                db.session.add(offer_event)
                db.session.flush()
            active_event_ids.append(offer_event.id)

    # ----------------------------------------------------
    # 5. REMOVE ORPHANED EVENTS
    # ----------------------------------------------------
    # Query all events for user that have a source, but are NOT in our active_event_ids list
    orphans = PlacementEvent.query.filter(
        PlacementEvent.user_id == student_id,
        PlacementEvent.source_type.isnot(None),
        ~PlacementEvent.id.in_(active_event_ids)
    ).all()

    for orphan in orphans:
        db.session.delete(orphan)

    db.session.commit()

def url_for_job_details(job_id):
    # Standard URL for a local job
    return f"/job/{job_id}"

def check_and_send_event_reminders():
    """
    Checks all placement events in the database against today's date.
    Sends inbox messages and email alerts at 7, 3, 1, and 0 days remaining.
    """
    # Use current local date
    today = datetime.now().date()
    events = PlacementEvent.query.all()

    reminders_sent = 0

    for ev in events:
        student = Student.query.get(ev.user_id)
        if not student:
            continue

        event_date_only = ev.event_date.date()
        days_left = (event_date_only - today).days

        # Determine if we should trigger a reminder
        trigger_reminder = False
        reminder_type = None

        if days_left == 7 and not ev.reminded_7d:
            trigger_reminder = True
            reminder_type = '7d'
        elif days_left == 3 and not ev.reminded_3d:
            trigger_reminder = True
            reminder_type = '3d'
        elif days_left == 1 and not ev.reminded_1d:
            trigger_reminder = True
            reminder_type = '1d'
        elif days_left == 0 and not ev.reminded_0d:
            trigger_reminder = True
            reminder_type = '0d'

        if trigger_reminder and reminder_type:
            # Build subjects and bodies based on urgency
            time_phrase = {
                '7d': 'in 7 days',
                '3d': 'in 3 days',
                '1d': 'tomorrow',
                '0d': 'TODAY'
            }[reminder_type]

            subject = f"Reminder: {ev.event_type} - {ev.company_name} is {time_phrase}!"
            body = (
                f"Dear {student.name},\n\n"
                f"This is an automated notification regarding an upcoming event in your placement calendar:\n\n"
                f"- Event: {ev.event_type}\n"
                f"- Company: {ev.company_name}\n"
                f"- Role: {ev.role_title}\n"
                f"- Date: {ev.event_date.strftime('%d %B %Y, %I:%M %p')}\n"
                f"- Details: {ev.description or 'No details available.'}\n\n"
                f"Please ensure you complete any required preparations and actions before the deadline.\n\n"
                f"Best Regards,\n"
                f"CareerConnect Portal"
            )

            # A. Send In-App Message
            msg = Message(
                student_id=student.id,
                subject=subject,
                body=body,
                sent_at=datetime.utcnow()
            )
            db.session.add(msg)

            # B. Send Email if notifications are active
            if student.email_notifications:
                try:
                    email = MailMessage(
                        subject=f"[CareerConnect Alert] {subject}",
                        recipients=[student.email]
                    )
                    email.body = body
                    mail.send(email)
                    print(f"Sent reminder email to {student.email} for {ev.event_type} at {ev.company_name}")
                except Exception as mail_err:
                    print(f"Mail dispatch failed during reminder checking to {student.email}:", str(mail_err))

            # Mark reminder flag as True
            if reminder_type == '7d':
                ev.reminded_7d = True
            elif reminder_type == '3d':
                ev.reminded_3d = True
            elif reminder_type == '1d':
                ev.reminded_1d = True
            elif reminder_type == '0d':
                ev.reminded_0d = True

            reminders_sent += 1

    if reminders_sent > 0:
        db.session.commit()

    print(f"Reminder checking process completed. Sent {reminders_sent} notifications.")
    return reminders_sent
