# Secure Smart Mailroom Parcel Authentication System

A complete full-stack web application for managing mailroom parcels securely, with built-in hardware API endpoints for ESP32 and Raspberry Pi integration. Built with **FastAPI**, **SQLite**, **Tailwind CSS**, and **Jinja2**.

## Features
- **Role-Based Dashboards:** Distinct views for Students and Admin (Mailroom Staff).
- **OTP Generation & Verification:** Generates random OTPs and securely validates them.
- **Hardware-Ready API:** Dedicated endpoints designed for simple ESP32/Pi IoT integration.
- **Beautiful UI:** Modern interface built with Tailwind CSS.

## Getting Started Locally

### 1. Requirements
Ensure you have Python 3.8+ installed on your system.

### 2. Setup Database & Install Dependencies

If you haven't, create a Virtual Environment and install the required modules:

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install fastapi uvicorn sqlalchemy jinja2 python-multipart passlib bcrypt
```

### 3. Run the Server
Run the FastAPI developer server via Uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

### 4. Seed Data & Login
1. Open your browser and navigate to: `http://localhost:8000/login`
2. Click **"Seed Test Data"** at the bottom of the sign-in form to create the initial users and database.
3. You can now log in using the example accounts:

**Admin (Mailroom Staff)**
- Username: `admin`
- Password: `admin`

**Student**
- Username: `student1`
- Password: `password`

## API Testing (For Future Hardware Integration)
FastAPI automatically generates an interactive swagger documentation.
Simply go to: [http://localhost:8000/docs](http://localhost:8000/docs)

### Hardware Flow Example using `curl`

**1. Create a Package (Admin Dashboard does this normally):**
```bash
curl -X POST http://localhost:8000/api/parcels \
  -H "Content-Type: application/json" \
  -d '{"id": "PKG-123", "student_username": "student1"}'
```

**2. Physical Hardware gets Parcel Status:**
*Your ESP32 can send a GET request via the tracking number*
```bash
curl http://localhost:8000/api/parcels/hardware/PKG-123
```

**3. Hardware verifies the OTP when student enters it on a Keypad:**
```bash
curl -X POST http://localhost:8000/api/verify-otp \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "parcel_id=PKG-123&otp=123456"
```
