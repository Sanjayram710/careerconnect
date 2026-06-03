<div align="center">

<!-- LOGO / HERO -->
<img src="screenshots/image/logo.png" alt="CareerConnect Logo" width="120"/>

<h1>CareerConnect</h1>

<p><strong>A full-stack career platform to discover jobs, upload resumes, and track your applications — all in one place.</strong></p>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Render](https://img.shields.io/badge/Deployed_on-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

<br/>

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Visit_Now-4F46E5?style=for-the-badge)](https://careerconnect-4obn.onrender.com/login)
[![Report Bug](https://img.shields.io/badge/🐛_Report-Bug-EF4444?style=for-the-badge)](https://github.com/sanjayram/careerconnect/issues)
[![Request Feature](https://img.shields.io/badge/✨_Request-Feature-F59E0B?style=for-the-badge)](https://github.com/sanjayram/careerconnect/issues)

<br/>



</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Screenshots](#-screenshots)
- [Architecture](#-architecture)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Environment Variables](#-environment-variables)
- [Usage](#-usage)
- [Folder Structure](#-folder-structure)
- [Future Roadmap](#-future-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Author](#-author)

---

## 🌟 Overview

**CareerConnect** is a student-built full-stack web application that centralizes the job search experience. Built with Python, Flask, SQLAlchemy, and Bootstrap 5, it lets users register, browse job and internship listings, upload their resumes, track application statuses, and manage their profile — all from a clean, responsive interface.

The project was developed as a hands-on full-stack learning project, covering backend architecture, database design, user authentication, file handling, and admin controls.

> 💡 **Goal:** Replace scattered spreadsheets and browser tabs with a single organized platform for managing your career search.

---

## ✨ Key Features

<table>
<tr>
<td width="50%">

### 👤 User Authentication
- Register and log in with email & password
- LinkedIn OAuth 2.0 social login
- Secure password hashing with Flask-Bcrypt
- Session management via Flask-Login
- Role-based access: Candidate vs. Admin

### 📄 Resume Upload & Management
- Upload resumes in PDF or DOCX format
- Store and manage uploaded resume files
- File type and size validation

### 🔍 Job & Internship Listings
- Browse job and internship postings
- Filter by role, location, and job type
- Listings managed through the Admin Dashboard

</td>
<td width="50%">

### 📊 Application Tracker
- Track every application with a status label
- Statuses: Applied → Under Review → Interviewed → Offered / Rejected
- View all applications from a personal dashboard

### 🛠️ Admin Dashboard
- Add, edit, and delete job listings
- View and manage registered users
- Basic platform oversight and moderation

### 📱 Responsive UI
- Built with Bootstrap 5.3
- Mobile-friendly layouts across all pages
- Clean, consistent design throughout

</td>
</tr>
</table>

---

## 🛠️ Tech Stack

<table>
<thead>
<tr>
<th>Layer</th>
<th>Technology</th>
<th>Purpose</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Backend</strong></td>
<td>Python 3.11+, Flask 3.x</td>
<td>Core web application framework</td>
</tr>
<tr>
<td><strong>ORM</strong></td>
<td>SQLAlchemy + Flask-Migrate</td>
<td>Database models & schema migrations</td>
</tr>
<tr>
<td><strong>Database</strong></td>
<td>PostgreSQL 15+</td>
<td>Primary relational data store</td>
</tr>
<tr>
<td><strong>Authentication</strong></td>
<td>Flask-Login, Flask-Bcrypt, OAuth 2.0</td>
<td>Session handling, password hashing, LinkedIn SSO</td>
</tr>
<tr>
<td><strong>Frontend</strong></td>
<td>Bootstrap 5.3, HTML5, CSS3, JavaScript</td>
<td>Responsive UI components & styling</td>
</tr>
<tr>
<td><strong>Templating</strong></td>
<td>Jinja2</td>
<td>Server-side HTML rendering</td>
</tr>
<tr>
<td><strong>Forms</strong></td>
<td>WTForms + Flask-WTF</td>
<td>Form handling & CSRF protection</td>
</tr>
<tr>
<td><strong>File Handling</strong></td>
<td>Werkzeug / Flask file utilities</td>
<td>Resume upload & storage</td>
</tr>
<tr>
<td><strong>Deployment</strong></td>
<td>Render</td>
<td>Cloud hosting for the live application</td>
</tr>
<tr>
<td><strong>Version Control</strong></td>
<td>Git + GitHub</td>
<td>Source control & collaboration</td>
</tr>
</tbody>
</table>

## 📸 Screenshots

<div align="center">

<h3>🔐 Login Page</h3>
<img src="screenshots/login.png" alt="CareerConnect Login" width="90%"/>

<br><br>

<h3>👤 Registration Page</h3>
<img src="screenshots/register.png" alt="CareerConnect Registration" width="90%"/>

<br><br>

<h3>💼 Dashboard Page </h3>
<img src="screenshots/dashboard.png" alt="CareerConnect Dashboard" width="90%"/>


<br><br>

<h3>💼 Job Listings</h3>
<img src="screenshots/jobs.png" alt="CareerConnect Jobs" width="90%"/>

</div>

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                         │
│          Bootstrap 5  ·  HTML/CSS  ·  JavaScript            │
└──────────────────────────────┬──────────────────────────────┘
                               │  HTTP / HTTPS
┌──────────────────────────────▼──────────────────────────────┐
│                     FLASK APPLICATION                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Blueprints  │  │  Jinja2      │  │  Flask-Login     │  │
│  │  auth/jobs/  │  │  Templates   │  │  Flask-Bcrypt    │  │
│  │  admin/main  │  │              │  │  OAuth 2.0       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │  WTForms /   │  │  Werkzeug File Handling              │ │
│  │  Flask-WTF   │  │  (Resume Uploads)                    │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                         DATA LAYER                          │
│                                                             │
│   SQLAlchemy ORM  ───────►  PostgreSQL                     │
│   Flask-Migrate              (Users, Jobs, Applications,    │
│                               Resumes)                      │
│                                                             │
│   Static File Storage ───►  app/static/uploads/            │
└─────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                      DEPLOYMENT                             │
│                    Render (Cloud PaaS)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| PostgreSQL | 15+ |
| Git | Latest |
| pip | Latest |

---

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/sanjayram/careerconnect.git
cd careerconnect
```

**2. Create and activate a virtual environment**

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

```bash
cp .env.example .env
# Fill in your values (see Environment Variables section below)
```

**5. Set up the database**

```bash
flask db upgrade
```

**6. (Optional) Seed sample data**

```bash
flask seed-db
```

**7. Run the development server**

```bash
flask run
```

> ✅ Open `http://127.0.0.1:8080/login` in your browser.

---

## 🔐 Environment Variables

Create a `.env` file from the provided template:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key for sessions & CSRF | `a-long-random-secret` |
| `FLASK_ENV` | App environment | `development` |
| `DATABASE_URL` | PostgreSQL connection URI | `postgresql://user:pass@localhost:5432/careerconnect` |
| `LINKEDIN_CLIENT_ID` | LinkedIn OAuth App Client ID | `abc123xyz` |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn OAuth App Secret | `supersecret` |
| `UPLOAD_FOLDER` | Path to save uploaded resumes | `app/static/uploads` |
| `MAX_CONTENT_LENGTH` | Max upload size in bytes | `5242880` *(5 MB)* |

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

---

## 💻 Usage



### Common Flask CLI Commands

```bash
# Start development server
flask run

# Start with debug mode
flask run --debug

# Run database migrations
flask db migrate -m "your message"
flask db upgrade

# Seed the database with sample data
flask seed-db

# Open interactive Flask shell
flask shell
```

---


## 📁 Folder Structure

```text
CareerConnect/
│
├── blueprints/
│   ├── admin.py
│   ├── auth.py
│   ├── linkedin.py
│   └── student.py
│
├── services/
│   ├── __init__.py
│   ├── calendar_service.py
│   ├── job_api.py
│   ├── news_service.py
│   └── scheduler_service.py
│
├── static/
│   └── css/
│       └── style.css
│
├── templates/
│   ├── emails/
│   │   ├── announcement.html
│   │   ├── application_confirmation.html
│   │   ├── status_update.html
│   │   └── tracked_application_confirmation.html
│   │
│   ├── admin_dashboard.html
│   ├── applications.html
│   ├── base.html
│   ├── bookmarked_news.html
│   ├── calendar.html
│   ├── companies.html
│   ├── company_details.html
│   ├── dashboard.html
│   ├── explore_jobs.html
│   ├── forgot_password.html
│   ├── internships.html
│   ├── job_details.html
│   ├── jobs.html
│   ├── linkedin_sandbox.html
│   ├── login.html
│   ├── messages.html
│   ├── profile.html
│   ├── register.html
│   ├── saved_jobs.html
│   ├── settings.html
│   └── verify_otp.html
│
├── uploads/
│
├── app.py
├── create_admin.py
├── init_db.py
├── migrate_sqlite_to_postgres.py
├── models.py
├── scheduler.py
├── requirements.txt
├── runtime.txt
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```



---

## 🗺️ Future Roadmap

These features are planned for upcoming versions:

| Feature | Description | Priority |
|---------|-------------|----------|
| 🤖 **AI Resume Analysis** | Automatically score resumes and suggest improvements | 🔴 High |
| 🎯 **AI Job Recommendations** | Suggest relevant jobs based on user profile and history | 🔴 High |
| 🏢 **Recruiter Dashboard** | Allow recruiters to post jobs and review applicants | 🟡 Medium |
| 🏗️ **Company Portal** | Company profile pages with job listings and info | 🟡 Medium |
| 🌐 **Live Job API Integration** | Pull real-time listings from external job APIs | 🟡 Medium |
| 💬 **In-App Messaging** | Direct messaging between candidates and recruiters | 🟡 Medium |
| 🎤 **Interview Prep Tools** | Practice questions and preparation resources | 🟢 Low |
| 📱 **Mobile App** | Companion app built with React Native | 🟢 Low |

---

## 🤝 Contributing

Contributions, suggestions, and feedback are welcome!

1. **Fork** this repository
2. **Create** a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Commit** your changes
   ```bash
   git commit -m 'feat: describe your change'
   ```
4. **Push** to your branch
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open** a Pull Request

### Guidelines

- Follow **PEP 8** for Python code style
- Use **Black** for formatting: `black .`
- Keep commits small and focused
- Write clear PR descriptions

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full details.

---

## 👨‍💻 Author

<div align="center">



**Sanjay Ram**

*CS Student · Full-Stack Developer · Python Enthusiast*

[![GitHub](https://img.shields.io/badge/GitHub-@sanjayram-181717?style=for-the-badge&logo=github)](https://github.com/Sanjay-ram-srinivasan/careerconnect)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/sanjay-ram-s-498681369/)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail)](mailto:sanjaysrinivasan.ram@email.com)

</div>

---

<div align="center">

**⭐ If you found this project useful or interesting, a star would mean a lot!**

<br/>

Made with ❤️, Python, and a lot of ☕

<br/>

<sub>© 2025 CareerConnect · MIT License · Built with Flask & PostgreSQL · Deployed on Render</sub>

</div>
