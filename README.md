<<<<<<< HEAD
# Interview AI

An AI-powered mock interview and performance analysis platform built with **Python + Flask**, **MongoDB (PyMongo)**, **Chart.js**, and **vanilla HTML, CSS, and JavaScript**.

## Features

- **Authentication & Protection**: Registration and Login with `bcrypt` password hashing, Flask session + JWT support, and protected routes.
- **Dashboard**: Real-time MongoDB-computed stats (Total Interviews Attended, Average Score, Skills Improved, Practice Time), last-10 performance trend chart, and Recent Interviews table.
- **AI Mock Interview**:
  - Configurable **Job Role** (7 tracks: Web Developer, Software Developer, Data Analyst, Python Developer, Full Stack Developer, AI/ML Engineer, HR/Other), **Difficulty Level** (Beginner, Intermediate, Advanced), **Question Type** (Technical, HR, Mixed), and **Question Count** (5, 10, 20).
  - 600+ curated non-repeating questions (`services/question_bank.py`).
  - Live timer, progress bar, question navigator, auto-save to MongoDB, and optional **Voice Input** via the Web Speech API.
- **AI Feedback & Evaluation**:
  - Dual evaluation engine (`services/evaluator.py`): uses **Google Gemini API** if `GEMINI_API_KEY` is provided, with automatic fallback to a deterministic **rule-based evaluator** (keyword coverage, answer depth, clarity/structure, reasoning markers, and confidence).
  - Animated score ring, 4-skill radar & delta comparison vs previous attempt, and expandable per-question cards with strengths, weaknesses, improvements, and ideal answer hints.
- **Performance Analytics**: Best/lowest score, most practiced role, score trend over time, skill radar, scores by role, scores by question type, and difficulty comparison.
- **Interview History**: Searchable, filterable (role, type, level, date range), paginated table with Resume, View Feedback, and Delete actions.
- **My Profile Settings & Help**: Edit profile & upload avatar photo, change password, delete account, interactive FAQ accordion, and MongoDB-backed support form.

## Folder Structure

```text
interview-ai/
├── app.py
├── config.py
├── seed.py
├── requirements.txt
├── .env.example
├── README.md
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── dashboard.py
│   ├── interview.py
│   └── profile.py
├── services/
│   ├── __init__.py
│   ├── question_bank.py
│   └── evaluator.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── interview.html
│   ├── feedback.html
│   ├── performance.html
│   ├── history.html
│   ├── profile.html
│   └── help.html
└── static/
    ├── css/style.css
    ├── js/
    │   ├── common.js
    │   ├── auth.js
    │   ├── dashboard.js
    │   ├── interview.js
    │   ├── feedback.js
    │   ├── performance.js
    │   ├── history.js
    │   ├── profile.js
    │   └── help.js
    └── img/
        ├── logo.svg
        └── default-avatar.svg
```

## Setup & Running Locally

### 1. Create a Virtual Environment & Install Requirements

```bash
cd interview-ai
python -m venv venv
```

Activate the virtual environment:

- **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
- **macOS / Linux**: `source venv/bin/activate`

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start MongoDB

Ensure your local MongoDB server is running on port `27017` (default `mongodb://localhost:27017/interview_ai`):

- **Windows**: Start the `MongoDB` service (`net start MongoDB`) or run `mongod`.
- **macOS / Linux**: `brew services start mongodb-community` or `sudo systemctl start mongod`.

### 3. Configure `.env`

Copy `.env.example` to `.env` and update values as needed:

```bash
cp .env.example .env
```

Example `.env`:

```env
MONGO_URI=mongodb://localhost:27017/interview_ai
SECRET_KEY=replace-with-a-secure-random-secret-key
GEMINI_API_KEY=
FLASK_DEBUG=True
PORT=5000
```

> **Note:** `GEMINI_API_KEY` is optional. Leave it blank to use the built-in rule-based AI evaluator.

### 4. Seed Sample Data (Optional)

Populate MongoDB with a demo account and 8 sample interviews:

```bash
python seed.py
```

Demo login credentials:
- **Email**: `demo@interviewai.com`
- **Password**: `DemoUser123!`

### 5. Run the Application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.
=======
# InterviewAI
>>>>>>> 8fc4fe9ef59155b6bfbb2fa594ddd70dda38b09d
