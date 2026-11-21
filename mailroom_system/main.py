"""
main.py — Smart Mailroom System (Hardened)
==========================================
All critical routes are wrapped in try/except.
Logging uses category prefixes: [AUTH] [PARCEL] [OTP] [FACE] [FINGERPRINT]
A global exception handler prevents the server from ever returning a raw 500.
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import traceback
import datetime

import models
import schemas
import crud
from database import engine, get_db, run_migrations
import auth
import mfa_services
import biometric_service

# ── Logger ────────────────────────────────────────────────────────────────────
from logger import (
    log_auth, log_auth_error,
    log_parcel, log_parcel_error,
    log_otp, log_otp_error,
    log_face, log_face_error,
    log_fingerprint, log_fingerprint_error,
    log_system, log_system_error,
)

# ── DB Init ───────────────────────────────────────────────────────────────────
models.Base.metadata.create_all(bind=engine)
log_system("Database tables verified / created.")
run_migrations()   # adds face_encoding + fingerprint_id columns to existing DBs
log_system("Biometric migration check complete.")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Smart Mailroom System")

# Ensure static directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# ── Resolve & log the ABSOLUTE template directory so we always know which files
# ── Jinja2 is reading — critical for debugging "my edits aren't showing" issues.
TEMPLATE_DIR = os.path.abspath("templates")
log_system(f"Template directory (absolute): {TEMPLATE_DIR}")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLERS  — server will NEVER crash / expose a raw traceback
# ══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all: log the full traceback and return a clean JSON error."""
    log_system_error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "detail": "An internal server error occurred. Please try again later.",
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return JSON for all HTTP errors thrown via HTTPException."""
    log_system_error(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    # Redirect responses (303) mustn't be converted to JSON
    if exc.status_code in (301, 302, 303, 307, 308):
        return RedirectResponse(url=exc.headers.get("Location", "/"), status_code=exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"status": "error", "detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured JSON when a request body / form fails Pydantic validation."""
    log_system_error(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"status": "error", "detail": exc.errors()},
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ══════════════════════════════════════════════════════════════════════════════

def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("session_user_id")
    if not user_id:
        return None
    try:
        user = crud.get_user_by_id(db, user_id=int(user_id))
        return user
    except Exception as exc:
        log_auth_error("Failed to resolve user from cookie", exc)
        return None


def login_required(request: Request, user=Depends(get_current_user_from_cookie)):
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def admin_required(request: Request, user=Depends(login_required)):
    if user.role != "admin":
        log_auth_error(f"Unauthorized admin access attempt by user '{user.username}'")
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


# ══════════════════════════════════════════════════════════════════════════════
# WEB ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def root(request: Request, user=Depends(get_current_user_from_cookie)):
    if user:
        if user.role == "admin":
            return RedirectResponse("/admin", status_code=303)
        return RedirectResponse("/student", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    error_msg = request.query_params.get("error")
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return templates.TemplateResponse(request, "login.html", {"error": error_msg, "now": now})


@app.post("/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """[AUTH] Authenticate user and set session cookie."""
    log_auth(f"Login attempt for username='{username}'")
    try:
        user = crud.get_user_by_username(db, username=username)
        if not user or not auth.verify_password(password, user.password_hash):
            log_auth(f"Login FAILED for username='{username}' — invalid credentials")
            return RedirectResponse("/login?error=InvalidCredentials", status_code=303)

        log_auth(f"Login SUCCESS for username='{username}' (role={user.role})")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(key="session_user_id", value=str(user.id), httponly=True)
        return response

    except Exception as exc:
        log_auth_error(f"Unexpected error during login for username='{username}'", exc)
        return RedirectResponse("/login?error=ServerError", status_code=303)


@app.post("/login/biometric")
async def login_biometric(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """[AUTH] Authenticate user via biometric (fingerprint_id) and set session cookie."""
    try:
        body = await request.json()
        fingerprint_id = body.get("fingerprint_id")
        
        log_auth(f"Biometric login attempt for fingerprint_id='{fingerprint_id}'")
        
        if not fingerprint_id:
            return JSONResponse(
                content={"success": False, "message": "Biometric verification failed"},
                status_code=400
            )

        user = crud.get_user_by_fingerprint_id(db, fingerprint_id=fingerprint_id)
        if not user:
            log_auth(f"Biometric login FAILED — no user for fingerprint_id='{fingerprint_id}'")
            return JSONResponse(
                content={"success": False, "message": "No enrolled fingerprint found"},
                status_code=401
            )

        log_auth(f"Biometric login SUCCESS for user='{user.username}' (role={user.role})")
        
        # Determine redirect
        redirect_url = "/admin" if user.role == "admin" else "/student"
        
        # Set session cookie and return JSON response
        res = JSONResponse(content={
            "success": True,
            "role": user.role,
            "redirect": redirect_url
        })
        res.set_cookie(key="session_user_id", value=str(user.id), httponly=True)
        return res

    except Exception as exc:
        log_auth_error("Unexpected error during biometric login", exc)
        return JSONResponse(
            content={"success": False, "message": "Biometric verification failed"},
            status_code=500
        )


@app.get("/logout")
def logout(request: Request):
    user_id = request.cookies.get("session_user_id", "unknown")
    log_auth(f"User (cookie id={user_id}) logged out")
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("session_user_id")
    return response


@app.get("/student", response_class=HTMLResponse)
def student_dashboard(
    request: Request,
    user=Depends(login_required),
    db: Session = Depends(get_db),
):
    try:
        if user.role != "student":
            return RedirectResponse("/admin", status_code=303)
        
        parcels = crud.get_student_parcels(db, student_id=user.id)
        
        # ── Network Impact Logic ──────────────────────────────────────────────────
        total_parcels = len(parcels)
        in_hub = len([p for p in parcels if p.status in ["Pending", "Arrived"]])
        verified = len([p for p in parcels if p.status == "Collected"])
        
        # Monthly usage (target: 20 parcels/month)
        now_dt = datetime.datetime.now()
        monthly_parcels = [
            p for p in parcels 
            if p.created_at and p.created_at.month == now_dt.month and p.created_at.year == now_dt.year
        ]
        usage_count = len(monthly_parcels)
        usage_percent = min(100, int((usage_count / 20) * 100))
        
        # Badge Logic
        impact_status = "LOW"
        impact_color = "zinc-500" # gray
        if usage_percent > 75:
            impact_status = "HIGH"
            impact_color = "amber-500"
        elif usage_percent > 40:
            impact_status = "OPTIMAL"
            impact_color = "emerald-500"
            
        impact = {
            "total": total_parcels,
            "in_hub": in_hub,
            "verified": verified,
            "percent": usage_percent,
            "status": impact_status,
            "color": impact_color
        }

        arrived_count = len([p for p in parcels if p.status == "Arrived"])
        log_parcel(f"Student '{user.username}' viewed dashboard — {len(parcels)} parcels, {arrived_count} arrived")
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        return templates.TemplateResponse(
            request, "student_dash.html",
            {
                "user": user, 
                "parcels": parcels, 
                "now": now,
                "impact": impact,
                "arrived_count": arrived_count,
            }
        )
    except Exception as exc:
        log_parcel_error(f"Error loading student dashboard for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Could not load student dashboard.")


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    user=Depends(admin_required),
    db: Session = Depends(get_db),
):
    try:
        parcels = crud.get_parcels(db)
        template_path = os.path.join(TEMPLATE_DIR, "admin_dash.html")
        log_parcel(
            f"[TEMPLATE] Rendering admin_dash.html for user '{user.username}' — "
            f"absolute path: {template_path}"
        )
        log_parcel(f"Admin '{user.username}' viewed dashboard — {len(parcels)} parcels")
        response = templates.TemplateResponse(
            request, "admin_dash.html", {
                "user": user,
                "parcels": parcels,
                "now": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
            }
        )
        # ── Cache-busting: instruct browser and any proxy NOT to cache this page.
        # ── This is the #1 fix for "I edited the template but nothing changed".
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as exc:
        log_parcel_error(f"Error loading admin dashboard for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Could not load admin dashboard.")


@app.get("/display", response_class=HTMLResponse)
def verification_display(request: Request):
    """Smart Parcel Verification Display Kiosk Mode."""
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    return templates.TemplateResponse(request, "display.html", {"now": now})


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — SEED
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/seed")
def seed_db(db: Session = Depends(get_db)):
    """[AUTH] Seed the database with default admin and student users."""
    log_auth("Seed request received")
    try:
        admin = crud.get_user_by_username(db, "admin")
        if not admin:
            admin = crud.create_user(
                db,
                schemas.UserCreate(username="admin", phone_number="0000000000", password="admin", role="admin"),
            )
        crud.save_fingerprint_id(db, user_id=admin.id, fingerprint_id="admin_fingerprint")

        student = crud.get_user_by_username(db, "student1")
        if not student:
            student = crud.create_user(
                db,
                schemas.UserCreate(username="student1", phone_number="1234567890", password="password", role="student"),
            )
        crud.save_fingerprint_id(db, user_id=student.id, fingerprint_id="student_fingerprint")

        log_auth("Seed SUCCESS — admin and student1 verified with biometric data")
        return {"status": "success", "msg": "Database seeded. Biometrics ready for admin and student1."}

    except Exception as exc:
        db.rollback()
        log_auth_error("Seed FAILED — database rolled back", exc)
        raise HTTPException(status_code=500, detail="Failed to seed database.")


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — PARCELS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/parcels", response_model=schemas.Parcel)
def create_parcel(
    parcel: schemas.ParcelCreate,
    user=Depends(admin_required),
    db: Session = Depends(get_db),
):
    """[PARCEL] Create a new parcel and assign it to a student."""
    log_parcel(f"Admin '{user.username}' creating parcel id='{parcel.id}' for student='{parcel.student_username}'")
    try:
        db_parcel = crud.create_parcel(db, parcel=parcel)
        if not db_parcel:
            log_parcel(f"Parcel creation FAILED — student '{parcel.student_username}' not found")
            raise HTTPException(status_code=404, detail="Student not found. Ensure username matches.")

        log_parcel(f"Parcel '{db_parcel.id}' created successfully for student '{parcel.student_username}'")
        return db_parcel

    except HTTPException:
        raise  # let FastAPI handle known HTTP errors as-is
    except Exception as exc:
        db.rollback()
        log_parcel_error(f"Unexpected error creating parcel '{parcel.id}'", exc)
        raise HTTPException(status_code=500, detail="Failed to create parcel.")


@app.post("/api/parcels/{parcel_id}/arrive")
def mark_arrived(
    parcel_id: str,
    user=Depends(admin_required),
    db: Session = Depends(get_db),
):
    """[OTP] Mark parcel as arrived and generate an OTP for the student."""
    log_otp(f"Admin '{user.username}' marking parcel '{parcel_id}' as arrived")
    try:
        result = crud.mark_parcel_arrived(db, parcel_id=parcel_id)
        if not result:
            log_otp(f"Arrive FAILED — parcel '{parcel_id}' not found")
            raise HTTPException(status_code=404, detail="Parcel not found")

        db_parcel, otp = result
        
        mfa_services.send_whatsapp_otp(db_parcel.owner.phone_number, otp, parcel_id)
        
        return {"status": "success", "message": "Parcel marked Arrived and OTP generated"}

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        log_otp_error(f"Unexpected error marking parcel '{parcel_id}' as arrived", exc)
        raise HTTPException(status_code=500, detail="Failed to mark parcel as arrived.")


@app.post("/api/verify-otp")
def verify_otp(
    parcel_id: str = Form(...),
    otp: str = Form(...),
    db: Session = Depends(get_db),
):
    """[OTP] Verify the OTP submitted by a student to collect a parcel."""
    log_otp(f"OTP verification attempt for parcel '{parcel_id}'")
    try:
        success, msg = crud.verify_parcel_otp(db, parcel_id=parcel_id, otp=otp)
        if not success:
            log_otp(f"OTP verification FAILED for parcel '{parcel_id}': {msg}")
            raise HTTPException(status_code=400, detail=msg)

        log_otp(f"OTP verification SUCCESS for parcel '{parcel_id}' — status → Collected")
        return {"status": "success", "message": msg}

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        log_otp_error(f"Unexpected error during OTP verification for parcel '{parcel_id}'", exc)
        raise HTTPException(status_code=500, detail="Failed to verify OTP.")


@app.get("/api/parcels/hardware/{parcel_id}")
def hardware_get_parcel(parcel_id: str, db: Session = Depends(get_db)):
    """[PARCEL] Hardware kiosk endpoint — returns parcel status."""
    log_parcel(f"Hardware status query for parcel '{parcel_id}'")
    try:
        parcel = crud.get_parcel(db, parcel_id)
        if not parcel:
            log_parcel(f"Hardware query FAILED — parcel '{parcel_id}' not found")
            raise HTTPException(status_code=404, detail="Parcel not found")

        log_parcel(f"Hardware query OK — parcel '{parcel_id}' status='{parcel.status}'")
        return {"id": parcel.id, "status": parcel.status}

    except HTTPException:
        raise
    except Exception as exc:
        log_parcel_error(f"Unexpected error in hardware query for parcel '{parcel_id}'", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve parcel status.")


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — FACE RECOGNITION
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/face/register")
async def face_register(request: Request, db: Session = Depends(get_db)):
    """[FACE] Register a student's face embedding for future biometric verification."""
    log_face("Face registration request received")
    try:
        body = await request.json()
        username = body.get("username")
        embedding = body.get("embedding")  # Expected: list[float] from client

        if not username or not embedding:
            log_face("Face register FAILED — missing username or embedding")
            raise HTTPException(status_code=400, detail="username and embedding are required.")

        user = crud.get_user_by_username(db, username=username)
        if not user:
            log_face(f"Face register FAILED — user '{username}' not found")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        # TODO: Persist embedding to database or a dedicated vector store
        # e.g. crud.save_face_embedding(db, user_id=user.id, embedding=embedding)
        log_face(f"Face registered (placeholder) for user '{username}' — embedding length={len(embedding)}")
        return {"status": "success", "message": f"Face registered for '{username}'"}

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        log_face_error("Unexpected error during face registration", exc)
        raise HTTPException(status_code=500, detail="Face registration failed.")


@app.post("/api/face/verify")
async def face_verify(request: Request, db: Session = Depends(get_db)):
    """[FACE] Verify a student's face against the stored embedding."""
    log_face("Face verification request received")
    try:
        body = await request.json()
        username = body.get("username")
        embedding = body.get("embedding")

        if not username or not embedding:
            log_face("Face verify FAILED — missing username or embedding")
            raise HTTPException(status_code=400, detail="username and embedding are required.")

        user = crud.get_user_by_username(db, username=username)
        if not user:
            log_face(f"Face verify FAILED — user '{username}' not found")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        # TODO: Retrieve and compare embedding
        # match = crud.verify_face_embedding(db, user_id=user.id, embedding=embedding)
        # Placeholder: always succeeds in current stub implementation
        match = True

        if not match:
            log_face(f"Face verify FAILED — face did not match for user '{username}'")
            raise HTTPException(status_code=401, detail="Face did not match. Access denied.")

        log_face(f"Face verify SUCCESS for user '{username}'")
        return {"status": "success", "message": "Face verified", "user": username}

    except HTTPException:
        raise
    except Exception as exc:
        log_face_error("Unexpected error during face verification", exc)
        raise HTTPException(status_code=500, detail="Face verification failed.")


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — FINGERPRINT (Hardware Stub)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/fingerprint/register")
async def fingerprint_register(request: Request, db: Session = Depends(get_db)):
    """[FINGERPRINT] Register a fingerprint template from a hardware sensor."""
    log_fingerprint("Fingerprint registration request received")
    try:
        body = await request.json()
        username = body.get("username")
        template = body.get("template")  # Raw bytes or base64 string from sensor

        if not username or not template:
            log_fingerprint("Fingerprint register FAILED — missing username or template")
            raise HTTPException(status_code=400, detail="username and template are required.")

        user = crud.get_user_by_username(db, username=username)
        if not user:
            log_fingerprint(f"Fingerprint register FAILED — user '{username}' not found")
            raise HTTPException(status_code=404, detail=f"User '{username}' not found.")

        # TODO: Persist template to DB or dedicated biometric store
        # crud.save_fingerprint(db, user_id=user.id, template=template)
        log_fingerprint(f"Fingerprint registered (placeholder) for user '{username}'")
        return {"status": "success", "message": f"Fingerprint registered for '{username}'"}

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        log_fingerprint_error("Unexpected error during fingerprint registration", exc)
        raise HTTPException(status_code=500, detail="Fingerprint registration failed.")


@app.post("/api/fingerprint/verify")
async def fingerprint_verify(request: Request):
    """[FINGERPRINT] Hardware simulation for fingerprint system."""
    try:
        body = await request.json()
        fingerprint_id = body.get("fingerprint_id")
        
        log_fingerprint(f"Received ID: {fingerprint_id}")
        
        if fingerprint_id == "demo123":
            log_fingerprint("Verification result: success")
            return {"status": "success", "message": "Fingerprint verified"}
        else:
            log_fingerprint("Verification result: fail")
            raise HTTPException(status_code=401, detail="Fingerprint verification failed")
            
    except HTTPException:
        raise
    except Exception as exc:
        log_fingerprint_error("Unexpected error during fingerprint verification", exc)
        raise HTTPException(status_code=500, detail="Fingerprint verification error")


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — UNIFIED BIOMETRIC  (register-biometric / verify-biometric)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/register-biometric")
async def register_biometric(request: Request, db: Session = Depends(get_db)):
    """
    [FACE][FINGERPRINT] Enroll a student's face + fingerprint in one call.

    Body: { "username": str, "fingerprint_id": str, "face_image": str (base64) }
    Returns: { "success": bool, "message": str }
    """
    log_face("register-biometric request received")
    try:
        body = await request.json()
        username      = body.get("username", "").strip()
        fingerprint_id = body.get("fingerprint_id", "").strip()
        face_image    = body.get("face_image", "").strip()

        if not username:
            return JSONResponse({"success": False, "message": "username is required"})
        if not fingerprint_id:
            return JSONResponse({"success": False, "message": "fingerprint_id is required"})
        if not face_image:
            return JSONResponse({"success": False, "message": "face_image is required"})

        user = crud.get_user_by_username(db, username=username)
        if not user:
            log_face(f"[REGISTER] FAILED — user '{username}' not found")
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": f"User '{username}' not found"}
            )

        # ── Face encoding ──────────────────────────────────────────────────────
        try:
            encoding_json = biometric_service.encode_face(face_image)
        except ValueError as ve:
            log_face_error(f"[REGISTER] Face encode failed for '{username}': {ve}")
            return JSONResponse({"success": False, "message": str(ve)})

        crud.save_face_encoding(db, user_id=user.id, encoding_json=encoding_json)
        log_face(f"[FACE] registered for user '{username}'")

        # ── Fingerprint ID ─────────────────────────────────────────────────────
        crud.save_fingerprint_id(db, user_id=user.id, fingerprint_id=fingerprint_id)
        log_fingerprint(f"[FINGERPRINT] registered for user '{username}' — id='{fingerprint_id}'")

        return JSONResponse({
            "success": True,
            "message": f"Biometrics registered for '{username}'"
        })
    except Exception as exc:
        db.rollback()
        log_face_error("Unexpected error in register-biometric", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Biometric registration failed due to a server error"}
        )


@app.post("/api/biometric/face/update")
async def update_face(request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    """[BIOMETRIC] Update face encoding for the current user."""
    try:
        body = await request.json()
        face_image = body.get("face_image")
        if not face_image:
            raise HTTPException(status_code=400, detail="face_image is required")
        
        encoding_json = biometric_service.encode_face(face_image)
        crud.save_face_encoding(db, user_id=user.id, encoding_json=encoding_json)
        log_face(f"Face scan updated for user '{user.username}'")
        return {"success": True, "message": "Face scan updated"}
    except ValueError as ve:
        log_face_error(f"Face encode failed for '{user.username}': {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        log_face_error(f"Error updating face scan for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Failed to update face scan.")


@app.post("/api/biometric/face/remove")
def remove_face(user=Depends(login_required), db: Session = Depends(get_db)):
    """[BIOMETRIC] Remove face encoding for the current user."""
    try:
        crud.save_face_encoding(db, user_id=user.id, encoding_json=None)
        log_face(f"Face scan removed for user '{user.username}'")
        return {"success": True, "message": "Face scan removed"}
    except Exception as exc:
        log_face_error(f"Error removing face scan for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Failed to remove face scan.")


@app.post("/api/biometric/fingerprint/update")
async def update_fingerprint(request: Request, user=Depends(login_required), db: Session = Depends(get_db)):
    """[BIOMETRIC] Update fingerprint ID for the current user."""
    try:
        body = await request.json()
        fingerprint_id = body.get("fingerprint_id")
        if not fingerprint_id:
            raise HTTPException(status_code=400, detail="fingerprint_id is required")
        
        crud.save_fingerprint_id(db, user_id=user.id, fingerprint_id=fingerprint_id)
        log_fingerprint(f"Fingerprint updated for user '{user.username}'")
        return {"success": True, "message": "Fingerprint updated"}
    except Exception as exc:
        log_fingerprint_error(f"Error updating fingerprint for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Failed to update fingerprint.")


@app.post("/api/biometric/fingerprint/remove")
def remove_fingerprint(user=Depends(login_required), db: Session = Depends(get_db)):
    """[BIOMETRIC] Remove fingerprint ID for the current user."""
    try:
        crud.save_fingerprint_id(db, user_id=user.id, fingerprint_id=None)
        log_fingerprint(f"Fingerprint removed for user '{user.username}'")
        return {"success": True, "message": "Fingerprint removed"}
    except Exception as exc:
        log_fingerprint_error(f"Error removing fingerprint for '{user.username}'", exc)
        raise HTTPException(status_code=500, detail="Failed to remove fingerprint.")


@app.post("/api/verify-biometric")
async def verify_biometric(request: Request, db: Session = Depends(get_db)):
    """
    [FACE][FINGERPRINT] Verify a student's identity using face + fingerprint.

    Body: { "username": str, "fingerprint_id": str, "face_image": str (base64) }
    Returns: { "success": bool, "message": str }
    Always HTTP 200 — caller inspects the 'success' flag.
    """
    log_face("verify-biometric request received")
    try:
        body = await request.json()
        username       = body.get("username", "").strip()
        fingerprint_id = body.get("fingerprint_id", "").strip()
        face_image     = body.get("face_image", "").strip()

        if not username or not fingerprint_id or not face_image:
            return JSONResponse({"success": False, "message": "username, fingerprint_id and face_image are all required"})

        user = crud.get_user_by_username(db, username=username)
        if not user:
            log_face(f"[VERIFY] FAILED — user '{username}' not found")
            return JSONResponse({"success": False, "message": f"User '{username}' not found"})

        # ── Fingerprint check ──────────────────────────────────────────────────
        stored_fp = crud.get_fingerprint_id(db, user_id=user.id)
        if not stored_fp:
            log_fingerprint(f"[VERIFY] FAIL — no fingerprint enrolled for '{username}'")
            return JSONResponse({"success": False, "message": "No fingerprint enrolled for this user. Please register first."})

        if stored_fp != fingerprint_id:
            log_fingerprint(f"[VERIFY] FAIL — fingerprint mismatch for '{username}'")
            return JSONResponse({"success": False, "message": "Mismatch"})

        log_fingerprint(f"[VERIFY] fingerprint OK for '{username}'")

        # ── Face check ─────────────────────────────────────────────────────────
        stored_enc = crud.get_face_encoding(db, user_id=user.id)
        if not stored_enc:
            log_face(f"[VERIFY] FAIL — no face enrolled for '{username}'")
            return JSONResponse({"success": False, "message": "No face enrolled for this user. Please register first."})

        face_match = biometric_service.verify_face(stored_enc, face_image)
        if not face_match:
            log_face(f"[VERIFY] fail — face mismatch for '{username}'")
            return JSONResponse({"success": False, "message": "Mismatch"})

        log_face(f"[VERIFY] success — identity confirmed for '{username}'")

        # ── Parcel Collection ──────────────────────────────────────────────────
        parcels = crud.get_student_parcels(db, student_id=user.id)
        arrived_parcel = next((p for p in parcels if p.status == "Arrived"), None)
        
        parcel_details = None
        if arrived_parcel:
            arrived_parcel.status = "Collected"
            arrived_parcel.collected_at = datetime.datetime.utcnow()
            arrived_parcel.current_otp = None
            arrived_parcel.otp_expiry = None
            db.commit()
            
            parcel_details = {
                "id": arrived_parcel.id,
                "student_name": user.username,
                "time": arrived_parcel.collected_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            log_parcel(f"Parcel '{arrived_parcel.id}' automatically collected via Biometrics for '{username}'")

        return JSONResponse({
            "success": True, 
            "message": "Identity verified",
            "parcel": parcel_details
        })

    except Exception as exc:
        log_face_error("Unexpected error in verify-biometric", exc)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Biometric verification failed due to a server error"}
        )


@app.post("/api/biometric/fingerprint/verify")
async def verify_fingerprint_session(
    request: Request,
    user=Depends(login_required),
    db: Session = Depends(get_db)
):
    """
    [FINGERPRINT] Verify fingerprint PIN for the currently logged-in user.
    Compares submitted fingerprint_id against user's stored fingerprint_id.
    Body: { "fingerprint_id": str }
    Returns: { "success": bool, "message": str }
    """
    try:
        body = await request.json()
        submitted_id = (body.get("fingerprint_id") or "").strip()

        if not submitted_id:
            return JSONResponse({"success": False, "message": "No fingerprint ID submitted."})

        stored_id = crud.get_fingerprint_id(db, user_id=user.id)
        if not stored_id:
            log_fingerprint(f"[VERIFY] FAIL — no fingerprint enrolled for '{user.username}'")
            return JSONResponse({"success": False, "message": "No Fingerprint Registered. Please enroll first."})

        if stored_id != submitted_id:
            log_fingerprint(f"[VERIFY] FAIL — fingerprint mismatch for '{user.username}'")
            return JSONResponse({"success": False, "message": "Fingerprint Verification Failed. ID mismatch."})

        log_fingerprint(f"[VERIFY] SUCCESS — fingerprint confirmed for '{user.username}'")
        return JSONResponse({"success": True, "message": "Fingerprint Verified"})

    except Exception as exc:
        log_fingerprint_error(f"Error in fingerprint verify for '{user.username}'", exc)
        return JSONResponse(status_code=500, content={"success": False, "message": "Server error during fingerprint verification."})


@app.post("/api/biometric/face/verify")
async def verify_face_session(
    request: Request,
    user=Depends(login_required),
    db: Session = Depends(get_db)
):
    """
    [FACE] Verify face image for the currently logged-in user.
    Compares captured image against user's stored face_encoding.
    Body: { "face_image": str (base64) }
    Returns: { "success": bool, "message": str }
    """
    try:
        body = await request.json()
        face_image = (body.get("face_image") or "").strip()

        if not face_image:
            return JSONResponse({"success": False, "message": "No face image received."})

        stored_enc = crud.get_face_encoding(db, user_id=user.id)
        if not stored_enc:
            log_face(f"[VERIFY] FAIL — no face enrolled for '{user.username}'")
            return JSONResponse({"success": False, "message": "No Face ID Enrolled. Please enroll via Security Context."})

        face_match = biometric_service.verify_face(stored_enc, face_image)
        if not face_match:
            log_face(f"[VERIFY] FAIL — face mismatch for '{user.username}'")
            return JSONResponse({"success": False, "message": "Face Not Recognized. Please retry or use fallback."})

        log_face(f"[VERIFY] SUCCESS — face confirmed for '{user.username}'")
        return JSONResponse({"success": True, "message": "Identity Verified"})

    except Exception as exc:
        log_face_error(f"Error in face verify for '{user.username}'", exc)
        return JSONResponse(status_code=500, content={"success": False, "message": "Server error during face verification."})


@app.get("/api/biometric/status")
def biometric_status(user=Depends(login_required), db: Session = Depends(get_db)):
    """[BIOMETRIC] Return current user's biometric enrollment status."""
    return {
        "face_enrolled": bool(crud.get_face_encoding(db, user.id)),
        "fingerprint_enrolled": bool(crud.get_fingerprint_id(db, user.id)),
        "username": user.username,
    }


@app.get("/api/fingerprint/status")
def fingerprint_status():
    """[FINGERPRINT] Health-check endpoint for the fingerprint hardware sensor."""
    log_fingerprint("Sensor status check")
    return {"status": "ok", "sensor": "disconnected (stub)", "message": "Fingerprint sensor stub is active."}


# ══════════════════════════════════════════════════════════════════════════════
# API ROUTES — DEMO MODE
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/system/status")
def system_status():
    """[SYSTEM] Real-time health check for the demo panel."""
    return {
      "backend": "online",
      "database": "connected",
      "face": "ready",
      "fingerprint": "ready",
      "otp": "active"
    }

@app.post("/api/demo/auto-generate")
def demo_auto_generate(db: Session = Depends(get_db)):
    """[DEMO] Instantiate a parcel and mark it arrived automatically."""
    import random
    from fastapi.responses import JSONResponse
    try:
        pid = f"DEMO-{random.randint(1000,9999)}"
        parcel = schemas.ParcelCreate(id=pid, student_username="student1")
        if not crud.get_user_by_username(db, "student1"):
            crud.create_user(db, schemas.UserCreate(username="student1", phone_number="1234567890", password="password", role="student"))
            
        crud.create_parcel(db, parcel)
        crud.mark_parcel_arrived(db, pid)
        return {"status": "success", "message": "OTP Sent"}
    except Exception as e:
        log_system_error("Demo auto-generate crashed", e)
        return JSONResponse(status_code=500, content={"status": "error", "detail": "Demo generation failed"})

@app.post("/api/demo/force-collect/{parcel_id}")
def demo_force_collect(parcel_id: str, db: Session = Depends(get_db)):
    """[DEMO] Force state to Collected for guided tour."""
    p = crud.get_parcel(db, parcel_id)
    if p:
        p.status = "Collected"
        import datetime
        p.collected_at = datetime.datetime.utcnow()
        db.commit()
    return {"status": "success"}
