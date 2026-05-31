import os
import requests
import secrets
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from models import db, Student, Message
from datetime import datetime

linkedin_bp = Blueprint('linkedin', __name__)


# ==============================
# LINKEDIN OAUTH LOGIN
# ==============================
@linkedin_bp.route('/linkedin/login')
@login_required
def linkedin_login():

    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    redirect_uri = os.getenv('LINKEDIN_REDIRECT_URI')

    # If API keys missing -> sandbox mode
    if not client_id or not redirect_uri:
        return redirect(url_for('linkedin.linkedin_sandbox'))

    # Generate OAuth state token
    state = secrets.token_hex(16)
    session['oauth_state'] = state

    # LinkedIn OAuth URL
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope=openid%20profile%20email"
    )

    return redirect(auth_url)


# ==============================
# SANDBOX PAGE
# ==============================
@linkedin_bp.route('/linkedin/sandbox')
@login_required
def linkedin_sandbox():
    return render_template('linkedin_sandbox.html')


# ==============================
# SANDBOX CALLBACK
# ==============================
@linkedin_bp.route('/linkedin/sandbox/callback', methods=['POST'])
@login_required
def linkedin_sandbox_callback():

    profile_type = request.form.get('profile_type', 'sanjay')

    mock_profiles = {

        'sanjay': {
            'name': 'Sanjay Ram',
            'headline': 'Aspiring Software Engineer | CSE Student',
            'avatar': 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?q=80&w=256&auto=format&fit=crop',
            'summary': 'Passionate Flask and Python developer.',
            'url': 'https://linkedin.com/in/sanjay-ram',
            'skills': 'Python, Flask, SQL, React'
        },

        'jane': {
            'name': 'Jane Doe',
            'headline': 'AI & ML Enthusiast',
            'avatar': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=256&auto=format&fit=crop',
            'summary': 'Machine Learning Engineer.',
            'url': 'https://linkedin.com/in/jane-doe',
            'skills': 'TensorFlow, Python, AI'
        }
    }

    profile = mock_profiles.get(profile_type, mock_profiles['sanjay'])

    current_user.linkedin_connected = True
    current_user.linkedin_name = profile['name']
    current_user.linkedin_profile_url = profile['url']
    current_user.linkedin_headline = profile['headline']
    current_user.linkedin_avatar = profile['avatar']
    current_user.linkedin_summary = profile['summary']

    if not current_user.skills:
        current_user.skills = profile['skills']

    try:

        db.session.commit()

        msg = Message(
            student_id=current_user.id,
            subject="LinkedIn Connected",
            body=f"Your LinkedIn sandbox profile was connected successfully.",
            sent_at=datetime.utcnow()
        )

        db.session.add(msg)
        db.session.commit()

        flash("LinkedIn Sandbox Profile Connected!", "success")

    except Exception as e:

        db.session.rollback()
        print(e)

        flash("Database Error", "danger")

    return redirect(url_for('student.profile'))


# ==============================
# LINKEDIN CALLBACK
# ==============================
@linkedin_bp.route('/linkedin/callback')
@login_required
def linkedin_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        flash("LinkedIn authentication cancelled or failed.", "danger")
        return redirect(url_for('student.profile'))

    if state != session.get('oauth_state'):
        flash("Security token mismatch.", "danger")
        return redirect(url_for('student.profile'))

    client_id = os.getenv('LINKEDIN_CLIENT_ID')
    client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
    redirect_uri = os.getenv('LINKEDIN_REDIRECT_URI')

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"

    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        # Get access token
        token_response = requests.post(token_url, data=payload)
        token_data = token_response.json()

        print("TOKEN RESPONSE:", token_data)

        access_token = token_data.get('access_token')

        if not access_token:
            flash("Failed to get LinkedIn access token.", "danger")
            return redirect(url_for('student.profile'))

        # Get LinkedIn profile info
        profile_url = "https://api.linkedin.com/v2/userinfo"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        profile_response = requests.get(profile_url, headers=headers)

        print("PROFILE STATUS:", profile_response.status_code)
        print("PROFILE RESPONSE:", profile_response.text)

        profile_data = profile_response.json()

        current_user.linkedin_connected = True
        current_user.linkedin_name = (
            f"{profile_data.get('given_name', '')} "
            f"{profile_data.get('family_name', '')}"
        ).strip()

        current_user.linkedin_profile_url = "https://www.linkedin.com/"
        current_user.linkedin_headline = "LinkedIn Verified User"
        current_user.linkedin_avatar = profile_data.get('picture')

        db.session.commit()

        flash("LinkedIn connected successfully!", "success")

    except Exception as e:
        db.session.rollback()
        print("LINKEDIN ERROR:", str(e))
        flash(f"LinkedIn Error: {str(e)}", "danger")

    return redirect(url_for('student.profile'))


# ==============================
# MANUAL LINKEDIN CONNECT
# ==============================
@linkedin_bp.route('/settings/linkedin/connect', methods=['POST'])
@login_required
def connect_manual():

    profile_url = request.form.get('profile_url')

    if not profile_url:

        flash("LinkedIn URL required.", "danger")
        return redirect(url_for('student.profile'))

    current_user.linkedin_connected = True
    current_user.linkedin_name = current_user.name
    current_user.linkedin_profile_url = profile_url
    current_user.linkedin_headline = "Software Engineer Aspirant"

    current_user.linkedin_avatar = (
        "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6"
    )

    current_user.linkedin_summary = "LinkedIn profile connected manually."

    try:

        db.session.commit()

        flash("LinkedIn profile linked successfully!", "success")

    except Exception as e:

        db.session.rollback()

        print(e)

        flash("Database Error", "danger")

    return redirect(url_for('student.profile'))


# ==============================
# DISCONNECT LINKEDIN
# ==============================
@linkedin_bp.route('/settings/linkedin/disconnect', methods=['POST'])
@login_required
def disconnect():

    current_user.linkedin_connected = False
    current_user.linkedin_name = None
    current_user.linkedin_profile_url = None
    current_user.linkedin_headline = None
    current_user.linkedin_avatar = None
    current_user.linkedin_summary = None

    try:

        db.session.commit()

        flash("LinkedIn disconnected successfully.", "success")

    except Exception as e:

        db.session.rollback()

        print(e)

        flash("Database Error", "danger")

    return redirect(url_for('student.profile'))