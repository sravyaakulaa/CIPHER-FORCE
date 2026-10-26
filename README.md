# ResumeIQ — AI Resume Builder & Analyzer

A full-stack student project built with **Python Flask, MySQL, HTML, CSS, JavaScript, Gemini API, PyMuPDF and ReportLab**.

## Features

- User registration and login with hashed passwords
- Resume builder with PDF export
- Upload a text-based PDF resume for review
- AI-generated strengths, improvements, formatting suggestions and keyword feedback using the Gemini API
- Optional job-description matching
- Basic keyword-based fallback when no Gemini key is configured
- MySQL-backed accounts and analysis history
- Delete history records
- Responsive desktop/mobile UI

> The score is an advisory estimate only. It does not reproduce any employer's proprietary ATS and cannot guarantee interview selection. The app sends resume text and the optional job description to the configured AI provider when Gemini analysis is enabled. Get user consent before processing sensitive personal information.

## Requirements

- Windows 10/11
- Python 3.10+ (Python 3.11 or 3.12 recommended)
- MySQL Server 8.x, with a MySQL user and password
- Gemini API key for real AI feedback: https://aistudio.google.com/app/apikey
- Internet connection for Gemini API and Google Fonts

## Windows setup

### 1. Install Python

Download Python from https://www.python.org/downloads/windows/. During installation, tick **Add python.exe to PATH**. Open a new PowerShell terminal and verify:

```powershell
py --version
python --version
```

If `py` isn't recognized, try `python --version`; if neither works, rerun the installer and enable PATH.

### 2. Install MySQL

Install MySQL Community Server from https://dev.mysql.com/downloads/installer/. Remember the root password you create and make sure the MySQL service is running.

### 3. Extract and open the project

Extract the ZIP. In PowerShell, change to the extracted project directory, for example:

```powershell
cd "$HOME\Downloads\AI-Resume-Builder"
```

### 4. Create a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use this for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Or use Command Prompt activation: `.venv\Scripts\activate.bat`.

### 5. Configure environment variables

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set your MySQL password in `DB_PASSWORD`. Replace `FLASK_SECRET_KEY` with a long random value. Add your Gemini key to `GEMINI_API_KEY`. Never commit `.env` or share your API key.

Example:

```dotenv
FLASK_SECRET_KEY=use-a-long-random-secret
FLASK_DEBUG=true
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password
DB_NAME=ai_resume_builder
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
ALLOW_BASIC_ANALYSIS=true
```

If you don't set `GEMINI_API_KEY`, the analyzer uses a simple keyword-based fallback when `ALLOW_BASIC_ANALYSIS=true`. That fallback is not generative AI.

### 6. Start the application

Make sure the MySQL service is running. In the project folder with the virtual environment activated:

```powershell
python app.py
```

On first startup, the app creates the `ai_resume_builder` database and tables using the configured MySQL account. The account needs permission to create a database and tables. If your database user does not have that permission, run `schema.sql` using MySQL Workbench and change `database.py` so it skips database creation.

Open http://127.0.0.1:5000 in your browser. Register an account, build a resume, or open Analyze resume.

Stop the development server with `Ctrl+C`.

## MySQL option: create schema manually

Open MySQL Workbench, connect to your local server, open `schema.sql`, and execute it. The app still expects the credentials in `.env` to have access to `ai_resume_builder`.

## Upload to GitHub

1. Create a new empty repository on https://github.com/new.
2. Ensure `.env` is not uploaded; `.gitignore` excludes it.
3. From the project folder:

```powershell
git init
git add .
git status
git commit -m "Initial AI Resume Builder and Analyzer project"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace the example remote URL with your repository URL. Never commit passwords, API keys, user resumes, or generated files.

## Project structure

```text
AI-Resume-Builder/
├── app.py
├── database.py
├── ai_analyzer.py
├── resume_parser.py
├── pdf_generator.py
├── requirements.txt
├── .env.example
├── schema.sql
├── templates/
├── static/css/style.css
├── static/js/script.js
├── uploads/
└── generated_resumes/
```

## Troubleshooting

- **`py` or `python` not recognized:** install Python and enable PATH, then reopen PowerShell.
- **MySQL access denied:** check `DB_USER`, `DB_PASSWORD`, host, port and that the service is running.
- **Gemini API error:** verify the key, model availability, network access and API quota. Never paste the key into a public issue.
- **Could not read PDF:** use a text-based PDF. Scanned/image-only PDFs need OCR, which this project does not include.
- **Port 5000 is busy:** change the last line of `app.py` to `app.run(port=5001, ...)` and open `http://127.0.0.1:5001`.
- **Unicode symbols in PDF:** ReportLab's default Helvetica has limited glyph support. Prefer plain punctuation or configure a Unicode TTF font if your resume needs special symbols.

## Security notes before public deployment

This project is for local learning/demo use. Before deploying publicly, disable debug mode, use a strong secret, add CSRF protection and rate limiting, restrict upload content more strictly, set HTTPS and secure cookie options, define data-retention rules, and use a least-privilege MySQL user. Never run Flask's debug server as a production server.
