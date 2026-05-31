"""
CareerConnect — SQLAlchemy Models
PostgreSQL-optimised with proper indexes, relationships, and constraint definitions.
"""

from flask_sqlalchemy  import SQLAlchemy
from flask_login       import UserMixin
from flask_mail        import Mail
from datetime          import datetime
from sqlalchemy        import Index

db   = SQLAlchemy()
mail = Mail()


# ─────────────────────────────────────────────────────────────────────────────
# Student
# ─────────────────────────────────────────────────────────────────────────────
class Student(db.Model, UserMixin):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)

    # Authentication
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    auth_provider = db.Column(db.String(50),  default='local', index=True)

    # Admin
    is_admin   = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Password Reset OTP
    reset_otp  = db.Column(db.String(10),  nullable=True)
    otp_expiry = db.Column(db.DateTime,    nullable=True)

    # Professional Profile
    phone      = db.Column(db.String(20),  nullable=True)
    location   = db.Column(db.String(100), nullable=True)
    experience = db.Column(db.String(100), nullable=True)
    bio        = db.Column(db.Text,        nullable=True)

    # Skills & Certifications
    skills         = db.Column(db.Text, nullable=True)
    certifications = db.Column(db.Text, nullable=True)

    # Education
    education_10th       = db.Column(db.String(100), nullable=True)
    education_12th       = db.Column(db.String(100), nullable=True)
    education_graduation = db.Column(db.String(255), nullable=True)
    cgpa                 = db.Column(db.Float,        nullable=True)

    # Resume & Portfolio
    resume_link     = db.Column(db.String(255), nullable=True)
    resume_filename = db.Column(db.String(255), nullable=True)
    portfolio_url   = db.Column(db.String(255), nullable=True)
    github_url      = db.Column(db.String(255), nullable=True)
    linkedin_url    = db.Column(db.String(255), nullable=True)

    # LinkedIn OAuth
    linkedin_connected   = db.Column(db.Boolean, default=False, nullable=False)
    linkedin_name        = db.Column(db.String(100), nullable=True)
    linkedin_profile_url = db.Column(db.String(255), nullable=True)
    linkedin_headline    = db.Column(db.String(255), nullable=True)
    linkedin_avatar      = db.Column(db.Text,        nullable=True)
    linkedin_summary     = db.Column(db.Text,        nullable=True)

    # Preferences
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    applications = db.relationship(
        'Application', backref='student', lazy=True, cascade='all, delete-orphan'
    )
    saved_jobs = db.relationship(
        'SavedJob', backref='student', lazy=True, cascade='all, delete-orphan'
    )
    saved_internships = db.relationship(
        'SavedInternship', backref='student', lazy=True, cascade='all, delete-orphan'
    )
    placement_events = db.relationship(
        'PlacementEvent', backref='student', lazy=True, cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Student {self.name} ({self.email})>'


# ─────────────────────────────────────────────────────────────────────────────
# Job  (admin-posted campus-drive listings)
# ─────────────────────────────────────────────────────────────────────────────
class Job(db.Model):
    __tablename__ = 'jobs'

    id           = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False, index=True)
    role         = db.Column(db.String(100), nullable=False)
    description  = db.Column(db.Text,       nullable=False)
    package      = db.Column(db.String(50),  nullable=False)
    job_type     = db.Column(db.String(50),  default='Full-Time')
    last_date    = db.Column(db.Date,        nullable=False, index=True)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

    location           = db.Column(db.String(100), default='Bangalore, India', nullable=False)
    skills_required    = db.Column(db.String(255), default='', nullable=False)
    drive_date         = db.Column(db.Date,        nullable=True)
    about_company      = db.Column(db.Text,        nullable=True)
    website            = db.Column(db.String(255), nullable=True)
    experience_required= db.Column(db.String(100), default='Any', nullable=True)

    applications = db.relationship(
        'Application', backref='job', lazy=True, cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Job {self.role} at {self.company_name}>'


# ─────────────────────────────────────────────────────────────────────────────
# LiveJob  (Adzuna API live feed)
# ─────────────────────────────────────────────────────────────────────────────
class LiveJob(db.Model):
    __tablename__ = 'live_jobs'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(255))
    company     = db.Column(db.String(255))
    salary_min  = db.Column(db.Integer)
    salary_max  = db.Column(db.Integer)
    posted_date = db.Column(db.DateTime)
    company_logo= db.Column(db.Text)
    location    = db.Column(db.String(255))
    description = db.Column(db.Text)
    apply_link  = db.Column(db.Text)
    job_type    = db.Column(db.String(100))
    source      = db.Column(db.String(100))

    updated_at          = db.Column(db.DateTime,    default=datetime.utcnow)
    experience_required = db.Column(db.String(100))

    # Sync tracking
    lastSyncedAt = db.Column(db.DateTime,    nullable=True)
    createdAt    = db.Column(db.DateTime,    default=datetime.utcnow)
    updatedAt    = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
    sourceId     = db.Column(db.String(100), nullable=True, index=True)
    sourceName   = db.Column(db.String(100), nullable=True)
    is_expired   = db.Column(db.Boolean,     default=False, nullable=False, index=True)

    __table_args__ = (
        Index('ix_live_jobs_updated_at',  'updated_at'),
        Index('ix_live_jobs_is_expired_updated', 'is_expired', 'updated_at'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# LiveInternship  (Adzuna API live feed)
# ─────────────────────────────────────────────────────────────────────────────
class LiveInternship(db.Model):
    __tablename__ = 'live_internship'

    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(300))
    company          = db.Column(db.String(200))
    location         = db.Column(db.String(200))
    description      = db.Column(db.Text)
    apply_link       = db.Column(db.Text, unique=True)
    internship_type  = db.Column(db.String(100))
    source           = db.Column(db.String(100))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    # Sync tracking
    lastSyncedAt = db.Column(db.DateTime,    nullable=True)
    createdAt    = db.Column(db.DateTime,    default=datetime.utcnow)
    updatedAt    = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
    sourceId     = db.Column(db.String(100), nullable=True, index=True)
    sourceName   = db.Column(db.String(100), nullable=True)
    is_expired   = db.Column(db.Boolean,     default=False, nullable=False, index=True)

    __table_args__ = (
        Index('ix_live_internship_created_at',  'created_at'),
        Index('ix_live_internship_is_expired_created', 'is_expired', 'created_at'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Application  (campus-drive applications)
# ─────────────────────────────────────────────────────────────────────────────
class Application(db.Model):
    __tablename__ = 'applications'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'job_id', name='uq_student_job'),
        Index('ix_applications_student_id', 'student_id'),
        Index('ix_applications_job_id',     'job_id'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    job_id     = db.Column(db.Integer, db.ForeignKey('jobs.id'),     nullable=False)
    status     = db.Column(db.String(50), nullable=False, default='Applied')
    applied_at = db.Column(db.DateTime,   default=datetime.utcnow)

    def __repr__(self):
        return f'<Application User:{self.student_id} Job:{self.job_id} Status:{self.status}>'


# ─────────────────────────────────────────────────────────────────────────────
# Message  (admin → student notifications)
# ─────────────────────────────────────────────────────────────────────────────
class Message(db.Model):
    __tablename__ = 'messages'
    __table_args__ = (
        Index('ix_messages_student_id', 'student_id'),
        Index('ix_messages_student_is_read', 'student_id', 'is_read'),
    )

    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject    = db.Column(db.String(255), nullable=False)
    body       = db.Column(db.Text,       nullable=False)
    is_read    = db.Column(db.Boolean,    default=False, nullable=False)
    sent_at    = db.Column(db.DateTime,   default=datetime.utcnow)

    student = db.relationship(
        'Student', backref=db.backref('messages', lazy=True, cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f'<Message {self.subject} to User:{self.student_id}>'


# ─────────────────────────────────────────────────────────────────────────────
# SavedJob
# ─────────────────────────────────────────────────────────────────────────────
class SavedJob(db.Model):
    __tablename__ = 'saved_jobs'
    __table_args__ = (
        Index('ix_saved_jobs_user_id',     'user_id'),
        Index('ix_saved_jobs_live_job_id', 'live_job_id'),
    )

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('students.id'),  nullable=False)
    live_job_id = db.Column(db.Integer, db.ForeignKey('live_jobs.id'), nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    live_job = db.relationship('LiveJob', backref=db.backref('saved_by_users', lazy=True))


# ─────────────────────────────────────────────────────────────────────────────
# CompanyNewsCache
# ─────────────────────────────────────────────────────────────────────────────
class CompanyNewsCache(db.Model):
    __tablename__ = 'company_news_cache'

    id           = db.Column(db.Integer,    primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    news_json    = db.Column(db.Text,        nullable=False)
    updated_at   = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# BookmarkedNews
# ─────────────────────────────────────────────────────────────────────────────
class BookmarkedNews(db.Model):
    __tablename__ = 'bookmarked_news'
    __table_args__ = (
        Index('ix_bookmarked_news_student_id', 'student_id'),
    )

    id           = db.Column(db.Integer,    primary_key=True)
    student_id   = db.Column(db.Integer,    db.ForeignKey('students.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    title        = db.Column(db.String(255), nullable=False)
    source       = db.Column(db.String(100), nullable=False)
    published_at = db.Column(db.String(50),  nullable=False)
    summary      = db.Column(db.Text,        nullable=True)
    url          = db.Column(db.String(500), nullable=False)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

    student = db.relationship(
        'Student', backref=db.backref('bookmarked_news', lazy=True, cascade='all, delete-orphan')
    )


# ─────────────────────────────────────────────────────────────────────────────
# TrackedApplication  (live-job / internship applications)
# ─────────────────────────────────────────────────────────────────────────────
class TrackedApplication(db.Model):
    __tablename__ = 'tracked_applications'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'job_id',        'application_type', name='uq_student_job_type'),
        db.UniqueConstraint('student_id', 'internship_id', 'application_type', name='uq_student_internship_type'),
        Index('ix_tracked_apps_student_id',     'student_id'),
        Index('ix_tracked_apps_job_id',         'job_id'),
        Index('ix_tracked_apps_internship_id',  'internship_id'),
    )

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('students.id'),        nullable=False)
    job_id           = db.Column(db.Integer, db.ForeignKey('live_jobs.id'),        nullable=True)
    internship_id    = db.Column(db.Integer, db.ForeignKey('live_internship.id'),  nullable=True)
    company_name     = db.Column(db.String(100), nullable=False)
    role_title       = db.Column(db.String(100), nullable=False)
    application_type = db.Column(db.String(50),  nullable=False)   # 'job' or 'internship'
    status           = db.Column(db.String(50),  nullable=False, default='Applied')
    applied_at       = db.Column(db.DateTime,    default=datetime.utcnow)

    student_rel      = db.relationship('Student',        backref=db.backref('tracked_apps',   lazy=True, cascade='all, delete-orphan'))
    live_job         = db.relationship('LiveJob',        backref=db.backref('tracked_apps',   lazy=True))
    live_internship  = db.relationship('LiveInternship', backref=db.backref('tracked_apps',   lazy=True))

    def __repr__(self):
        return f'<TrackedApplication User:{self.student_id} Type:{self.application_type} Status:{self.status}>'


# ─────────────────────────────────────────────────────────────────────────────
# SavedInternship
# ─────────────────────────────────────────────────────────────────────────────
class SavedInternship(db.Model):
    __tablename__ = 'saved_internships'
    __table_args__ = (
        Index('ix_saved_internships_user_id',           'user_id'),
        Index('ix_saved_internships_live_internship_id','live_internship_id'),
    )

    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('students.id'),          nullable=False)
    live_internship_id  = db.Column(db.Integer, db.ForeignKey('live_internship.id'),   nullable=False)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)

    live_internship = db.relationship('LiveInternship', backref=db.backref('saved_by_users', lazy=True))

    def __repr__(self):
        return f'<SavedInternship User:{self.user_id} Internship:{self.live_internship_id}>'


# ─────────────────────────────────────────────────────────────────────────────
# PlacementEvent  (calendar)
# ─────────────────────────────────────────────────────────────────────────────
class PlacementEvent(db.Model):
    __tablename__ = 'placement_events'
    __table_args__ = (
        Index('ix_placement_events_user_id',    'user_id'),
        Index('ix_placement_events_event_date', 'event_date'),
    )

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    company_id      = db.Column(db.Integer, nullable=True)
    company_name    = db.Column(db.String(100), nullable=False)
    role_title      = db.Column(db.String(100), nullable=False)
    event_type      = db.Column(db.String(50),  nullable=False)
    event_date      = db.Column(db.DateTime,    nullable=False)
    description     = db.Column(db.Text,        nullable=True)
    application_url = db.Column(db.String(500), nullable=True)
    created_at      = db.Column(db.DateTime,    default=datetime.utcnow)

    # Reminder flags
    reminded_7d = db.Column(db.Boolean, default=False, nullable=False)
    reminded_3d = db.Column(db.Boolean, default=False, nullable=False)
    reminded_1d = db.Column(db.Boolean, default=False, nullable=False)
    reminded_0d = db.Column(db.Boolean, default=False, nullable=False)

    # Sync tracking
    source_type = db.Column(db.String(50),  nullable=True)
    source_id   = db.Column(db.Integer,     nullable=True)

    def __repr__(self):
        return f'<PlacementEvent {self.event_type} - {self.company_name} - {self.role_title}>'


# ─────────────────────────────────────────────────────────────────────────────
# SyncLog  (background job sync audit trail)
# ─────────────────────────────────────────────────────────────────────────────
class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    __table_args__ = (
        Index('ix_sync_logs_syncType',   'syncType'),
        Index('ix_sync_logs_startedAt',  'startedAt'),
    )

    id             = db.Column(db.Integer,    primary_key=True)
    syncType       = db.Column(db.String(50), nullable=False)          # 'jobs' | 'internships'
    startedAt      = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)
    completedAt    = db.Column(db.DateTime,   nullable=True)
    recordsAdded   = db.Column(db.Integer,    default=0)
    recordsUpdated = db.Column(db.Integer,    default=0)
    recordsRemoved = db.Column(db.Integer,    default=0)
    status         = db.Column(db.String(20), nullable=False)          # 'RUNNING' | 'SUCCESS' | 'FAILED'
    errorMessage   = db.Column(db.Text,       nullable=True)

    def __repr__(self):
        return f'<SyncLog id={self.id} type={self.syncType} status={self.status}>'