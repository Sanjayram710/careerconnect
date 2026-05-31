import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load env variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Fetch PostgreSQL connection URL
raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url and raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

POSTGRES_URL = raw_db_url or "postgresql://postgres:postgres@localhost:5432/placement_portal"
DB_URI = None


def verify_or_create_postgres_db():
    """
    Parse DATABASE_URL, connect to PostgreSQL default database 'postgres',
    and verify/create the target database if we are running locally.
    If local PostgreSQL is unreachable, sets DB_URI to SQLite fallback.
    """
    global DB_URI
    
    # 1. Parse connection parameters to see if it is a local or remote host
    from urllib.parse import urlparse
    try:
        result = urlparse(POSTGRES_URL)
        dbname = result.path.lstrip('/')
        is_local = (not result.hostname or 
                    'localhost' in result.hostname or 
                    '127.0.0.1' in result.hostname or 
                    'postgres' in result.hostname)
    except Exception:
        is_local = True
        dbname = 'placement_portal'

    # If it is a remote PostgreSQL, we assume production/managed environment and use it directly
    if raw_db_url and not is_local:
        logger.info("Remote/Production Database detected in environment. Using PostgreSQL directly.")
        DB_URI = POSTGRES_URL
        return True

    # Otherwise, it's a local database — test the connection to verify it's reachable
    logger.info("Checking local PostgreSQL database connection...")
    try:
        # Connect to 'postgres' administrative database first
        admin_url = POSTGRES_URL.replace(f"/{dbname}", "/postgres")
        conn = psycopg2.connect(admin_url, connect_timeout=1)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (dbname,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Database '{dbname}' does not exist. Creating...")
            cursor.execute(f"CREATE DATABASE {dbname};")
            logger.info(f"Database '{dbname}' created successfully.")
        else:
            logger.info(f"Database '{dbname}' already exists.")
        
        cursor.close()
        conn.close()
        DB_URI = POSTGRES_URL
        return True
    except Exception as e:
        # Fall back to SQLite
        db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "placement.db")
        logger.warning(
            "Local PostgreSQL connection failed. Falling back to local SQLite database at: %s", db_path
        )
        DB_URI = f"sqlite:///{db_path}"
        return True


def seed_database():
    from flask import Flask
    from models import db, Student, Job, Message, LiveJob, LiveInternship, SavedJob, SavedInternship, Application, TrackedApplication, PlacementEvent
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        logger.info("Initializing schemas (Drop & Recreate)...")
        # For seeding a clean environment, drop and recreate tables
        db.drop_all()
        db.create_all()
        
        # Seed Administrator Account
        admin_email = "admin@placement.edu"
        logger.info("Seeding default Administrator user...")
        admin_pw = generate_password_hash('admin', method='scrypt')
        default_admin = Student(
            name="Admin Portal",
            email=admin_email,
            password_hash=admin_pw,
            is_admin=True,
            skills="Management, HR, Systems Administration"
        )
        db.session.add(default_admin)
        db.session.commit()
        logger.info(f"Admin created successfully (Login: {admin_email} / password: admin)")
            
        # Seed Sanjay Ram student account
        student_email = "sanjay@university.edu"
        student_pw = generate_password_hash('student', method='scrypt')
        logger.info("Seeding Sanjay Ram student user account...")
        student_sanjay = Student(
            name="Sanjay Ram",
            email=student_email,
            password_hash=student_pw,
            is_admin=False,
            skills="Python, SQL, HTML/CSS, React, Javascript, Flask, Git",
            linkedin_connected=True,
            linkedin_name="Sanjay Ram",
            linkedin_profile_url="https://linkedin.com/in/sanjay-ram-2005",
            linkedin_headline="Aspiring Software Engineer | CSE Student at University",
            linkedin_avatar="https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=256&auto=format&fit=crop",
            linkedin_summary="Enthusiastic Computer Science student passionate about web development, database engineering, and backend services. Proficient in Python, Flask, and React.",
            certifications="AWS Certified Developer Associate, Oracle Certified Associate Java SE 8",
            email_notifications=True
        )
        db.session.add(student_sanjay)
        db.session.commit()
        logger.info(f"Student created successfully (Login: {student_email} / password: student)")

        logger.info("Seeding sample placement job opportunities...")
        today = datetime.now().date()
        
        sample_jobs = [
            Job(
                company_name="Google",
                role="Software Engineer (L3)",
                description="We are looking for passionate developers to build next-generation search systems, cloud infrastructure, and AI tools. Strong understanding of algorithms, data structures, and operating systems is required. Experience with C++, Java, or Python is preferred.",
                package="32.5 LPA",
                last_date=today + timedelta(days=15),
                location="Bangalore, India",
                skills_required="C++, Python, Data Structures, Algorithms, OS",
                drive_date=today + timedelta(days=20),
                about_company="Google's mission is to organize the world's information and make it universally accessible and useful. Google is a global technology leader focusing on search, cloud, AI, and advertising.",
                website="https://careers.google.com"
            ),
            Job(
                company_name="Microsoft",
                role="Software Engineering Analyst",
                description="Join the Azure Cloud platform team to design and build massive scale distributed systems. You will work on microservices, virtualization, networking software, and developer tools. Candidates should exhibit collaboration skills and a passion for engineering excellence.",
                package="28.0 LPA",
                last_date=today + timedelta(days=10),
                location="Hyderabad, India",
                skills_required="C#, Azure, SQL, Distributed Systems, Algorithms",
                drive_date=today + timedelta(days=15),
                about_company="Microsoft enables digital transformation for the era of an intelligent cloud and an intelligent edge. Its mission is to empower every person and every organization on the planet to achieve more.",
                website="https://careers.microsoft.com"
            ),
            Job(
                company_name="NVIDIA",
                role="AI Infrastructure Engineer",
                description="Work at the cutting edge of accelerated computing. Developers will work on GPU optimization pipelines, deep learning frameworks, and driver-level APIs. Familiarity with parallel programming (CUDA), C/C++, and machine learning architecture is highly valued.",
                package="35.0 LPA",
                last_date=today + timedelta(days=20),
                location="Pune, India",
                skills_required="C++, CUDA, Deep Learning, Parallel Programming",
                drive_date=today + timedelta(days=25),
                about_company="NVIDIA pioneered accelerated computing to tackle challenges no one else can solve. Our work in AI, graphics, and robotics is transforming industries and society.",
                website="https://nvidia.com/careers"
            ),
            Job(
                company_name="Stripe",
                role="Full-Stack Engineer",
                description="Build financial infrastructure for the internet. Work across web services, frontend dashboards, and robust API endpoints. You will focus on developer experience, reliability, and security of globally distributed payment rails.",
                package="24.0 LPA",
                last_date=today + timedelta(days=12),
                location="Remote (India)",
                skills_required="Ruby on Rails, Javascript, React, SQL, API Design",
                drive_date=today + timedelta(days=17),
                about_company="Stripe is a financial infrastructure platform for the internet. Millions of companies—from the world's largest enterprises to the most ambitious startups—use Stripe to accept payments, grow their revenue, and accelerate new business opportunities.",
                website="https://stripe.com/jobs"
            ),
            Job(
                company_name="Adobe",
                role="Product Engineer (Creative Cloud)",
                description="Create experiences that empower artists and designers globally. This role involves designing elegant user interfaces, optimizing rendering engines, and building collaborative cloud platforms. Strong web fundamentals (JS, React) and Python backend experience are required.",
                package="22.0 LPA",
                last_date=today + timedelta(days=7),
                location="Noida, India",
                skills_required="Python, React, Node.js, REST APIs, Web Fundamentals",
                drive_date=today + timedelta(days=12),
                about_company="Adobe is the global leader in digital media and digital marketing solutions. Our creative, marketing and document solutions empower everyone – from individual artists to global brands – to bring digital creations to life.",
                website="https://adobe.com/careers"
            ),
            Job(
                company_name="Tesla",
                role="Embedded Systems Engineer",
                description="Develop real-time control software for vehicle systems, battery management, and autopilot hardware. Requires proficiency in C/C++, low-level hardware debugging, microcontrollers, and real-time operating systems (RTOS).",
                package="30.0 LPA",
                last_date=today + timedelta(days=18),
                location="Bangalore, India",
                skills_required="C, Embedded RTOS, Microcontrollers, Firmware Development",
                drive_date=today + timedelta(days=23),
                about_company="Tesla is accelerating the world's transition to sustainable energy. We design, manufacture, sell, and service electric vehicles, solar energy systems, and energy storage products.",
                website="https://tesla.com/careers"
            )
        ]
        
        db.session.bulk_save_objects(sample_jobs)
        db.session.commit()
        logger.info(f"Successfully seeded {len(sample_jobs)} job opportunities.")
        
        logger.info("Seeding sample messages for Sanjay Ram...")
        sample_messages = [
            Message(
                student_id=student_sanjay.id,
                subject="Your profile has been shortlisted by Stripe",
                body="Dear Sanjay Ram,\n\nCongratulations! We are pleased to inform you that your profile has been shortlisted by the Stripe engineering recruitment team for the Full-Stack Engineer position. Your technical skills and project experience align well with our needs.\n\nNext Steps:\nAn technical screening interview has been scheduled for you. Please check the Calendar tab for interview details.\n\nBest Regards,\nStripe Talent Acquisition",
                sent_at=datetime.utcnow() - timedelta(hours=3),
                is_read=False
            ),
            Message(
                student_id=student_sanjay.id,
                subject="New drive scheduled by Microsoft on 01 Jun 2026",
                body="Dear Student,\n\nA new recruitment drive has been posted by Microsoft for the Software Engineering Analyst position. \n\nDetails:\n- CTC: 28.0 LPA\n- Cutoff CGPA: 7.5\n- Last date to apply: 01 Jun 2026\n\nPlease ensure your profile details are fully updated, including your CGPA and resume link, and apply through the active recruitment drives in the dashboard.\n\nBest Regards,\nCareerConnect Team",
                sent_at=datetime.utcnow() - timedelta(hours=5),
                is_read=True
            ),
            Message(
                student_id=student_sanjay.id,
                subject="Welcome to the redesigned CareerConnect!",
                body="Hello Sanjay Ram,\n\nWelcome to your brand-new, modern student CareerConnect dashboard! Here, you can easily update your profile metrics, upload your resume link, connect your LinkedIn account, browse active recruitment drives, apply with a single click, track your pipeline statuses, view calendar events, and receive critical notifications.\n\nIf you have any feedback or face any issues, feel free to contact the administrator office.\n\nBest of luck with your career journey!\n\nBest Regards,\nRedesign Tech Support Team",
                sent_at=datetime.utcnow() - timedelta(days=1),
                is_read=True
            )
        ]
        db.session.bulk_save_objects(sample_messages)
        db.session.commit()
        logger.info("Successfully seeded sample messages.")

        logger.info("Seeding sample LiveJobs and LiveInternships...")
        live_jobs = [
            LiveJob(
                title="Frontend Developer",
                company="Airbnb",
                salary_min=1800000,
                salary_max=2400000,
                posted_date=datetime.utcnow() - timedelta(days=2),
                company_logo="https://logo.clearbit.com/airbnb.com",
                location="Bangalore, India",
                experience_required="Fresher",
                description="Join us in building the future of travel. We need a frontend engineer with solid knowledge of React, HTML, CSS, and JavaScript.",
                apply_link="https://careers.airbnb.com/frontend-dev",
                job_type="Full-time",
                source="Adzuna"
            ),
            LiveJob(
                title="Backend Systems Engineer",
                company="Uber",
                salary_min=2200000,
                salary_max=3000000,
                posted_date=datetime.utcnow() - timedelta(days=3),
                company_logo="https://logo.clearbit.com/uber.com",
                location="Hyderabad, India",
                experience_required="Fresher",
                description="Work on scale. Optimize routing and dispatch algorithms in Go and Java. Strong database skills are highly preferred.",
                apply_link="https://careers.uber.com/backend-eng",
                job_type="Full-time",
                source="Adzuna"
            )
        ]
        
        live_internships = [
            LiveInternship(
                title="Software Engineering Intern",
                company="Amazon",
                location="Bangalore, India",
                description="We are looking for software development engineering interns. You will work on real projects under the guidance of experienced mentors.",
                apply_link="https://careers.amazon.com/internship-sde",
                internship_type="Internship",
                source="Adzuna",
                created_at=datetime.utcnow() - timedelta(days=4)
            ),
            LiveInternship(
                title="Full-Stack Developer Intern",
                company="Meta",
                location="Remote",
                description="Work across the stack using React and Python. Gain hands-on experience building features for billions of users.",
                apply_link="https://careers.meta.com/intern-fullstack",
                internship_type="Internship",
                source="Adzuna",
                created_at=datetime.utcnow() - timedelta(days=1)
            )
        ]
        
        for lj in live_jobs:
            db.session.add(lj)
        for li in live_internships:
            db.session.add(li)
        db.session.commit()
        
        logger.info("Seeding saved items and applications for Sanjay Ram...")
        airbnb_job = LiveJob.query.filter_by(company="Airbnb").first()
        if airbnb_job:
            saved_job = SavedJob(
                user_id=student_sanjay.id,
                live_job_id=airbnb_job.id
            )
            db.session.add(saved_job)
            
        amazon_intern = LiveInternship.query.filter_by(company="Amazon").first()
        if amazon_intern:
            saved_intern = SavedInternship(
                user_id=student_sanjay.id,
                live_internship_id=amazon_intern.id
            )
            db.session.add(saved_intern)
            
        google_local = Job.query.filter_by(company_name="Google").first()
        if google_local:
            app1 = Application(
                student_id=student_sanjay.id,
                job_id=google_local.id,
                status="Interviewing",
                applied_at=datetime.utcnow() - timedelta(days=5)
            )
            db.session.add(app1)
            
        stripe_local = Job.query.filter_by(company_name="Stripe").first()
        if stripe_local:
            app2 = Application(
                student_id=student_sanjay.id,
                job_id=stripe_local.id,
                status="Shortlisted",
                applied_at=datetime.utcnow() - timedelta(days=7)
            )
            db.session.add(app2)

        uber_job = LiveJob.query.filter_by(company="Uber").first()
        if uber_job:
            tracked_app = TrackedApplication(
                student_id=student_sanjay.id,
                job_id=uber_job.id,
                company_name=uber_job.company,
                role_title=uber_job.title,
                application_type="job",
                status="Applied",
                applied_at=datetime.utcnow() - timedelta(days=2)
            )
            db.session.add(tracked_app)
            
        db.session.commit()
        logger.info("Successfully seeded saved items and applications.")

        try:
            from services.calendar_service import sync_student_events
            sync_student_events(student_sanjay.id)
            logger.info("Successfully executed initial calendar sync for Sanjay Ram!")
        except Exception as sync_err:
            logger.warning(f"Could not sync calendar during database seeding: {sync_err}")


if __name__ == "__main__":
    if verify_or_create_postgres_db():
        seed_database()
        if DB_URI.startswith("sqlite"):
            logger.info("SQLite Database initialization & seeding complete!")
        else:
            logger.info("PostgreSQL Database verification & initialization complete!")
    else:
        logger.error("Failed to initialize Database.")
