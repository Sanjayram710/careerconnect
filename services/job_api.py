import requests
import time
import traceback
from datetime import datetime
from models import db, LiveJob, LiveInternship, SyncLog

APP_ID = "b2d1cf70"
APP_KEY = "89654003b4f0859722eae1559cc7929f"


class JobSyncService:
    @staticmethod
    def sync():
        """
        Automatically refresh and sync Jobs data:
        - Fetch from Adzuna API page-by-page.
        - Prevent duplicates using sourceId (Adzuna ID) or apply_link.
        - Update existing records, avoiding writing/committing unchanged ones.
        - Mark expired jobs (not returned in latest run) as is_expired=True if saved/applied, otherwise delete them.
        - Run with automatic retries up to 3 times on failure.
        - Track stats and duration in SyncLog.
        """
        started_at = datetime.utcnow()
        db_log = SyncLog(
            syncType='jobs',
            startedAt=started_at,
            status='RUNNING'
        )
        db.session.add(db_log)
        db.session.commit()

        records_added = 0
        records_updated = 0
        records_removed = 0
        
        seen_apply_links = set()
        seen_source_ids = set()

        try:
            for page in range(1, 6):
                url = (
                    f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"
                    f"?app_id={APP_ID}"
                    f"&app_key={APP_KEY}"
                    f"&results_per_page=50"
                    f"&what=software developer"
                )
                
                response = None
                for attempt in range(1, 4):
                    try:
                        response = requests.get(url, timeout=15)
                        response.raise_for_status()
                        break
                    except Exception as e:
                        if attempt == 3:
                            raise e
                        print(f"JobSyncService: Attempt {attempt} failed for page {page}. Retrying in 2 seconds...")
                        time.sleep(2)

                data = response.json()
                if 'results' not in data:
                    continue

                for item in data['results']:
                    apply_link = item.get('redirect_url', '#')
                    source_id = str(item.get('id', ''))
                    
                    if not source_id or not apply_link or apply_link == '#':
                        continue
                    
                    seen_apply_links.add(apply_link)
                    seen_source_ids.add(source_id)

                    existing_job = LiveJob.query.filter(
                        (LiveJob.sourceId == source_id) | (LiveJob.apply_link == apply_link)
                    ).first()

                    title = item.get('title', 'N/A')
                    company = item.get('company', {}).get('display_name', 'Unknown')
                    company_logo = f"https://logo.clearbit.com/{company.replace(' ', '').lower()}.com"
                    salary_min = item.get('salary_min')
                    salary_max = item.get('salary_max')
                    location = item.get('location', {}).get('display_name', 'Remote')
                    experience_required = item.get('experience', 'Freshers')
                    description = item.get('description', '')
                    job_type = 'Full-time'
                    source = 'Adzuna'

                    if existing_job:
                        changed = False
                        if existing_job.title != title:
                            existing_job.title = title
                            changed = True
                        if existing_job.company != company:
                            existing_job.company = company
                            changed = True
                        if existing_job.company_logo != company_logo:
                            existing_job.company_logo = company_logo
                            changed = True
                        if existing_job.salary_min != salary_min:
                            existing_job.salary_min = salary_min
                            changed = True
                        if existing_job.salary_max != salary_max:
                            existing_job.salary_max = salary_max
                            changed = True
                        if existing_job.location != location:
                            existing_job.location = location
                            changed = True
                        if existing_job.experience_required != experience_required:
                            existing_job.experience_required = experience_required
                            changed = True
                        if existing_job.description != description:
                            existing_job.description = description
                            changed = True
                        if existing_job.job_type != job_type:
                            existing_job.job_type = job_type
                            changed = True
                        if existing_job.source != source:
                            existing_job.source = source
                            changed = True
                        if existing_job.sourceId != source_id:
                            existing_job.sourceId = source_id
                            changed = True
                        if existing_job.sourceName != 'Adzuna':
                            existing_job.sourceName = 'Adzuna'
                            changed = True
                        if existing_job.is_expired:
                            existing_job.is_expired = False
                            changed = True

                        if changed:
                            existing_job.lastSyncedAt = datetime.utcnow()
                            existing_job.updatedAt = datetime.utcnow()
                            records_updated += 1
                        else:
                            existing_job.lastSyncedAt = datetime.utcnow()
                    else:
                        new_job = LiveJob(
                            title=title,
                            company=company,
                            company_logo=company_logo,
                            salary_min=salary_min,
                            salary_max=salary_max,
                            location=location,
                            experience_required=experience_required,
                            description=description,
                            apply_link=apply_link,
                            job_type=job_type,
                            source=source,
                            sourceId=source_id,
                            sourceName='Adzuna',
                            lastSyncedAt=datetime.utcnow(),
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow(),
                            is_expired=False
                        )
                        db.session.add(new_job)
                        records_added += 1

            # Handle expired jobs
            all_active_jobs = LiveJob.query.filter_by(is_expired=False).all()
            for job in all_active_jobs:
                if job.sourceId not in seen_source_ids and job.apply_link not in seen_apply_links:
                    from models import SavedJob, TrackedApplication
                    is_saved = SavedJob.query.filter_by(live_job_id=job.id).first() is not None
                    is_applied = TrackedApplication.query.filter_by(job_id=job.id, application_type='job').first() is not None
                    
                    if is_saved or is_applied:
                        job.is_expired = True
                        job.updatedAt = datetime.utcnow()
                    else:
                        db.session.delete(job)
                    records_removed += 1

            db_log.completedAt = datetime.utcnow()
            db_log.recordsAdded = records_added
            db_log.recordsUpdated = records_updated
            db_log.recordsRemoved = records_removed
            db_log.status = 'SUCCESS'
            db.session.commit()
            print(f"JobSyncService: Success. Added: {records_added}, Updated: {records_updated}, Removed: {records_removed}")
            return {
                'added': records_added,
                'updated': records_updated,
                'removed': records_removed,
                'status': 'SUCCESS'
            }

        except Exception as e:
            db.session.rollback()
            err_msg = traceback.format_exc()
            print("JobSyncService Error:", err_msg)
            try:
                db_log.completedAt = datetime.utcnow()
                db_log.status = 'FAILED'
                db_log.errorMessage = str(e)
                db.session.commit()
            except Exception as commit_err:
                print("Failed to save error sync log:", commit_err)
            return {
                'status': 'FAILED',
                'error': str(e)
            }


class InternshipSyncService:
    @staticmethod
    def sync():
        """
        Automatically refresh and sync Internships data:
        - Fetch from Adzuna API page-by-page.
        - Prevent duplicates using sourceId (Adzuna ID) or apply_link.
        - Update existing records, avoiding writing/committing unchanged ones.
        - Mark expired internships (not returned in latest run) as is_expired=True if saved/applied, otherwise delete them.
        - Run with automatic retries up to 3 times on failure.
        - Track stats and duration in SyncLog.
        """
        started_at = datetime.utcnow()
        db_log = SyncLog(
            syncType='internships',
            startedAt=started_at,
            status='RUNNING'
        )
        db.session.add(db_log)
        db.session.commit()

        records_added = 0
        records_updated = 0
        records_removed = 0
        
        seen_apply_links = set()
        seen_source_ids = set()

        try:
            for page in range(1, 3):
                url = (
                    f"https://api.adzuna.com/v1/api/jobs/in/search/{page}"
                    f"?app_id={APP_ID}"
                    f"&app_key={APP_KEY}"
                    f"&results_per_page=20"
                    f"&what=software internship"
                )
                
                response = None
                for attempt in range(1, 4):
                    try:
                        response = requests.get(url, timeout=15)
                        response.raise_for_status()
                        break
                    except Exception as e:
                        if attempt == 3:
                            raise e
                        print(f"InternshipSyncService: Attempt {attempt} failed for page {page}. Retrying in 2 seconds...")
                        time.sleep(2)

                data = response.json()
                if 'results' not in data:
                    continue

                for item in data['results']:
                    apply_link = item.get('redirect_url', '#')
                    source_id = str(item.get('id', ''))
                    
                    if not source_id or not apply_link or apply_link == '#':
                        continue
                    
                    seen_apply_links.add(apply_link)
                    seen_source_ids.add(source_id)

                    existing = LiveInternship.query.filter(
                        (LiveInternship.sourceId == source_id) | (LiveInternship.apply_link == apply_link)
                    ).first()

                    title = item.get('title', 'N/A')
                    company = item.get('company', {}).get('display_name', 'Unknown')
                    location = item.get('location', {}).get('display_name', 'Remote')
                    description = item.get('description', '')
                    internship_type = 'Internship'
                    source = 'Adzuna'

                    if existing:
                        changed = False
                        if existing.title != title:
                            existing.title = title
                            changed = True
                        if existing.company != company:
                            existing.company = company
                            changed = True
                        if existing.location != location:
                            existing.location = location
                            changed = True
                        if existing.description != description:
                            existing.description = description
                            changed = True
                        if existing.internship_type != internship_type:
                            existing.internship_type = internship_type
                            changed = True
                        if existing.source != source:
                            existing.source = source
                            changed = True
                        if existing.sourceId != source_id:
                            existing.sourceId = source_id
                            changed = True
                        if existing.sourceName != 'Adzuna':
                            existing.sourceName = 'Adzuna'
                            changed = True
                        if existing.is_expired:
                            existing.is_expired = False
                            changed = True

                        if changed:
                            existing.lastSyncedAt = datetime.utcnow()
                            existing.updatedAt = datetime.utcnow()
                            records_updated += 1
                        else:
                            existing.lastSyncedAt = datetime.utcnow()
                    else:
                        new_intern = LiveInternship(
                            title=title,
                            company=company,
                            location=location,
                            description=description,
                            apply_link=apply_link,
                            internship_type=internship_type,
                            source=source,
                            sourceId=source_id,
                            sourceName='Adzuna',
                            lastSyncedAt=datetime.utcnow(),
                            createdAt=datetime.utcnow(),
                            updatedAt=datetime.utcnow(),
                            is_expired=False
                        )
                        db.session.add(new_intern)
                        records_added += 1

            # Handle expired internships
            all_active_internships = LiveInternship.query.filter_by(is_expired=False).all()
            for intern in all_active_internships:
                if intern.sourceId not in seen_source_ids and intern.apply_link not in seen_apply_links:
                    from models import SavedInternship, TrackedApplication
                    is_saved = SavedInternship.query.filter_by(live_internship_id=intern.id).first() is not None
                    is_applied = TrackedApplication.query.filter_by(internship_id=intern.id, application_type='internship').first() is not None
                    
                    if is_saved or is_applied:
                        intern.is_expired = True
                        intern.updatedAt = datetime.utcnow()
                    else:
                        db.session.delete(intern)
                    records_removed += 1

            db_log.completedAt = datetime.utcnow()
            db_log.recordsAdded = records_added
            db_log.recordsUpdated = records_updated
            db_log.recordsRemoved = records_removed
            db_log.status = 'SUCCESS'
            db.session.commit()
            print(f"InternshipSyncService: Success. Added: {records_added}, Updated: {records_updated}, Removed: {records_removed}")
            return {
                'added': records_added,
                'updated': records_updated,
                'removed': records_removed,
                'status': 'SUCCESS'
            }

        except Exception as e:
            db.session.rollback()
            err_msg = traceback.format_exc()
            print("InternshipSyncService Error:", err_msg)
            try:
                db_log.completedAt = datetime.utcnow()
                db_log.status = 'FAILED'
                db_log.errorMessage = str(e)
                db.session.commit()
            except Exception as commit_err:
                print("Failed to save error sync log:", commit_err)
            return {
                'status': 'FAILED',
                'error': str(e)
            }


# Backwards compatibility function definitions
def fetch_jobs():
    return JobSyncService.sync()

def fetch_internships():
    return InternshipSyncService.sync()