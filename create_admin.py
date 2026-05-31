import os
import sys
import logging
from app import app
from models import db, Student
from werkzeug.security import generate_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

with app.app_context():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@portal.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    existing_admin = Student.query.filter_by(email=admin_email).first()

    if not existing_admin:
        logger.info(f"Creating administrator account with email: {admin_email}...")
        admin = Student(
            name="Administrator",
            email=admin_email,
            password_hash=generate_password_hash(admin_password, method='scrypt'),
            is_admin=True,
            skills="Administration, Management"
        )

        try:
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin created successfully!")
        except Exception as e:
            db.session.rollback()
            logger.critical(f"Failed to create admin: {e}")
            sys.exit(1)
    else:
        logger.info(f"Admin user with email {admin_email} already exists.")