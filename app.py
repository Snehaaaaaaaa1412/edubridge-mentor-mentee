
from fastapi import FastAPI, HTTPException, Form, File, UploadFile,Request, Depends, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND
from passlib.context import CryptContext
from typing import Optional, List
from datetime import datetime
import os, traceback, bcrypt, shutil, mysql.connector,uuid
from datetime import datetime, date
from pydantic import BaseModel
import io,logging


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="supersecretkey123")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
IMAGES_DIR = os.path.join(FRONTEND_DIR, "images")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploaded_photos")
UPLOAD_RESUMES_DIR = os.path.join(BASE_DIR, "uploaded_resumes")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# Create directories if they do not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_RESUMES_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static directories
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")
if os.path.exists(UPLOAD_FOLDER):
    app.mount("/uploaded_photos", StaticFiles(directory=UPLOAD_FOLDER), name="uploaded_photos")
if os.path.exists(UPLOAD_RESUMES_DIR):
    app.mount("/uploaded_resumes", StaticFiles(directory=UPLOAD_RESUMES_DIR), name="uploaded_resumes")

# Mount the general uploads directory
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Jinja2 templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Jaanu@0711",
        database="mentor_mentee_db"
    )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    return {"filename": file.filename}

# Route to serve files from the /uploads directory
@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return {"error": "File not found"}
    

@app.get("/", response_class=HTMLResponse)
async def home():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=500, detail="index.html not found.")
    with open(index_path, "r") as file:
        return HTMLResponse(content=file.read())

@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def get_about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/mentor-login", response_class=HTMLResponse)
async def show_mentor_login(request: Request, success: str = None):
    return templates.TemplateResponse("mentor-login.html", {
        "request": request,
        "message": "Password changed successfully. Please login again." if success == "password" else ""
    })

@app.get("/mentor_registration", response_class=HTMLResponse)
async def serve_mentor_registration(request: Request):
    return templates.TemplateResponse("mentor_registration.html", {"request": request})

@app.get("/mentor-home", response_class=HTMLResponse)
async def mentor_home(request: Request):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/mentor-login", status_code=303)
    
    return templates.TemplateResponse("mentor-home.html", {"request": request, "email": mentor_email})

@app.get("/mentor-profile", response_class=HTMLResponse)
async def mentor_profile(request: Request):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/mentor-login", status_code=303)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM mentor WHERE email = %s", (mentor_email,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Mentor not found.")

        photo_filename = os.path.basename(user["profile_photo"])
        photo_url = f"/uploaded_photos/{photo_filename}"

        return templates.TemplateResponse("mentor-profile.html", {
            "request": request,
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "department": user.get("department", ""),
            "designation": user.get("designation", ""),
            "qualification": user.get("qualification", ""),
            "interests": user.get("interests", ""),
            "profile_photo": photo_url
        })

    except:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching profile.")

    finally:
        cursor.close()
        conn.close()

@app.get("/mentee_registration", response_class=HTMLResponse)
async def serve_mentor_registration(request: Request):
    return templates.TemplateResponse("mentee_registration.html", {"request": request})


@app.get("/mentee_profile", response_class=HTMLResponse)
async def mentee_profile(request: Request):
    mentee_email = request.session.get("mentee_email")
    if not mentee_email:
        return RedirectResponse(url="/mentee_login", status_code=303)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query to fetch mentee details from the database using the email
        cursor.execute("SELECT * FROM mentee WHERE email = %s", (mentee_email,))
        mentee = cursor.fetchone()

        if not mentee:
            raise HTTPException(status_code=404, detail="Mentee not found.")

        # Handle profile photo path
        photo_filename = os.path.basename(mentee["profile_photo"])
        photo_url = f"/uploaded_photos/{photo_filename}"

        # Return the profile page with mentee details
        return templates.TemplateResponse("mentee_profile.html", {
            "request": request,
            "name": mentee.get("name", ""),
            "email": mentee.get("email", ""),
            "course": mentee.get("course", ""),
            "year": mentee.get("year", ""),
            "branch": mentee.get("branch", ""),
            "roll_no": mentee.get("roll_no", ""),
            "profile_photo": photo_url
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/find_mentor", response_class=HTMLResponse)
async def get_find_mentor(request: Request):
    # Fetch available departments (you can modify this as needed)
    departments = [
        "Computer Science and Engineering",
        "Electronics and Communication Engineering",
        "Electrical Engineering",
        "Mechanical Engineering",
        "Applied Sciences"
    ]
    
    return templates.TemplateResponse("find_mentor.html", {"request": request, "departments": departments})

@app.get("/request_mentor/{mentor_email}", response_class=HTMLResponse)
async def request_mentor(mentor_email: str, request: Request):
    # Replace underscore (_) with @ in the mentor's email
    mentor_email = mentor_email.replace('_', '@')

    # Establish database connection
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query to get the mentor's details based on email
    query = "SELECT * FROM mentor WHERE email = %s"
    cursor.execute(query, (mentor_email,))
    mentor = cursor.fetchone()

    cursor.close()
    conn.close()

    if not mentor:
        return HTMLResponse("Mentor not found", status_code=404)
    return templates.TemplateResponse("request_mentor.html", {"request": request, "mentor": mentor})

@app.get("/mentor-project-requests")
async def mentor_project_requests(request: Request, email: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM mentor_requests WHERE mentor_email = %s AND status = 'pending'", (email,))
    project_requests = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("mentor-project-requests.html", {
        "request": request,
        "email": email,
        "project_requests": project_requests
    })

@app.get("/mentor/home/{mentor_email}", response_class=HTMLResponse)
async def mentor_home(mentor_email: str, request: Request):
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query to fetch the mentor data
    query = "SELECT * FROM mentor WHERE email = %s"
    cursor.execute(query, (mentor_email,))
    mentor = cursor.fetchone()

    # Query to fetch accepted projects for the mentor
    query_projects = """
    SELECT p.project_id, p.project_name, p.description
    FROM projects p
    JOIN mentor_requests mr ON p.project_id = mr.project_id
    WHERE mr.mentor_email = %s AND mr.status = 'accepted'
    """
    cursor.execute(query_projects, (mentor_email,))
    projects = cursor.fetchall()

    cursor.close()
    conn.close()

    # Return the template with mentor data and accepted projects
    return templates.TemplateResponse("mentor_home.html", {
        "request": request,
        "email": mentor_email,
        "projects": projects
    })


@app.get("/request_mentor/{mentor_email}", response_class=HTMLResponse)
async def request_mentor_page(request: Request, mentor_email: str, mentee_email: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch mentor data
    cursor.execute("SELECT * FROM mentor WHERE email = %s", (mentor_email,))
    mentor = cursor.fetchone()

    cursor.close()
    conn.close()

    print(f"Received: {mentee_email} {mentor_email}")

    return templates.TemplateResponse("request_mentor.html", {
        "request": request,
        "mentor": mentor,
        "mentee_email": mentee_email  
    })

@app.get("/project_requests/{mentor_email}", response_class=HTMLResponse)
async def project_requests(request: Request, mentor_email: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            m.name AS mentee_name,
            m.email AS mentee_email,
            m.roll_no,
            m.branch,
            m.course,
            m.year,
            r.project_name,
            r.project_description,
            r.status
        FROM mentor_requests r
        JOIN mentee m ON r.mentee_email = m.email
        WHERE r.mentor_email = %s;
    """
    cursor.execute(query, (mentor_email,))
    requests = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("project_requests.html", {
        "request": request,
        "mentor_email": mentor_email,
        "requests": requests
    })

@app.get("/mentee_requests", response_class=HTMLResponse)
async def mentee_requests(request: Request, email: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM mentor_requests WHERE mentee_email = %s"
        cursor.execute(query, (email,))
        requests = cursor.fetchall()

        return templates.TemplateResponse("mentee_requests.html", {
            "request": request,
            "requests": requests,
            "email": email
        })

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching requests")

    finally:
        cursor.close()
        conn.close()

@app.get("/mentee/request-status-page", response_class=HTMLResponse)
async def mentee_request_status_page(request: Request):
    mentee_email = request.session.get("mentee_email")
    if not mentee_email:
        return RedirectResponse(url="/mentee_login", status_code=303)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT 
                mr.project_name,
                mr.project_description,
                mr.status,
                mr.mentor_email,
                m.name AS mentor_name
            FROM mentor_requests mr
            JOIN mentor m ON mr.mentor_email = m.email
            WHERE mr.mentee_email = %s
            ORDER BY mr.request_date DESC
        """
        cursor.execute(query, (mentee_email,))
        requests = cursor.fetchall()

        cursor.close()
        conn.close()

        return templates.TemplateResponse("mentee_request_status.html", {
            "request": request,
            "requests": requests,
            "mentee_email": mentee_email
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/mentee_login", response_class=HTMLResponse)
async def mentee_login_page(request: Request):
    return templates.TemplateResponse("mentee_login.html", {"request": request})

@app.post("/mentee_login")
async def mentee_login(request: Request, email: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()  
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM mentee WHERE email = %s", (email,))
    mentee = cursor.fetchone()

    if mentee and bcrypt.checkpw(password.encode('utf-8'), mentee['password'].encode('utf-8')):
        request.session['mentee_email'] = email  
        
        return RedirectResponse("/mentee_home", status_code=303)  

    return {"error": "Invalid credentials"}

@app.get("/mentee_home", response_class=HTMLResponse)
async def mentee_home(request: Request):

    if 'mentee_email' not in request.session:
        return RedirectResponse("/mentee_login")  
    
    return templates.TemplateResponse("mentee_home.html", {"request": request})



@app.post("/register/mentor")
async def register_mentor(request: Request, 
                          name: str = Form(...),
                          email: str = Form(...),
                          password: str = Form(...),
                          phone: str = Form(...),
                          department: str = Form(...),
                          designation: str = Form(...),
                          qualification: str = Form(...),
                          interests: str = Form(...),
                          profile_photo: UploadFile = File(...)):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    photo_path = f"uploaded_photos/{profile_photo.filename}"
    with open(photo_path, "wb") as f:
        f.write(await profile_photo.read())
    try:
        connection =get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO mentor 
            (name, email, password, phone, profile_photo, department, designation, qualification, interests)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            name, email, hashed_password, phone, profile_photo.filename,
            department, designation, qualification, interests
        ))
        connection.commit()
        cursor.close()
        connection.close()
        return RedirectResponse(url="/mentor-login", status_code=303)
    except mysql.connector.Error as err:
        return HTMLResponse(content=f"<h2>Error: {err}</h2>", status_code=500)
    

@app.post("/mentor-login", response_class=HTMLResponse)
async def process_mentor_login(request: Request):
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM mentor WHERE email = %s", (email,))
    mentor = cursor.fetchone()

    cursor.close()
    conn.close()

    if mentor and bcrypt.checkpw(password.encode('utf-8'), mentor['password'].encode('utf-8')):
        request.session["mentor_email"] = email
        return RedirectResponse(url=f"/mentor-home?email={email}", status_code=303)
    else:
        return templates.TemplateResponse("mentor-login.html", {
            "request": request,
            "message": "Invalid email or password"
        })


@app.post("/update-mentor-profile")
async def update_mentor_profile(
    request: Request,
    original_email: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    designation: str = Form(...),
    qualification: str = Form(...),
    interests: List[str] = Form(...)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        interests_str = ",".join(interests)

        cursor.execute("""
            UPDATE mentor 
            SET email = %s, department = %s, designation = %s, qualification = %s, interests = %s 
            WHERE email = %s
        """, (email, department, designation, qualification, interests_str, original_email))

        conn.commit()
        return RedirectResponse(url=f"/mentor-profile?email={email}&success=true", status_code=HTTP_302_FOUND)
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(content=f"<h3>Error updating profile: {e}</h3>", status_code=500)
    finally:
        cursor.close()
        conn.close()


@app.post("/update-mentor-photo")
async def update_mentor_photo(email: str = Form(...), file: UploadFile = File(...)):
    try:
        filename = file.filename
        filepath = os.path.join("uploaded_photos", filename)

        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update DB with just the filename
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE mentor SET profile_photo = %s WHERE email = %s", (filename, email))
        conn.commit()

        return {"message": "Mentor profile photo updated successfully."}
    except:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error updating mentor profile photo.")
    finally:
        cursor.close()
        conn.close()

# Change Password
@app.post("/update-mentor-password")
async def update_mentor_password(
    request: Request,
    email: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    try:
        if new_password != confirm_password:
            return HTMLResponse("<h3 style='color:red;'>New passwords do not match.</h3>")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM mentor WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or not pwd_context.verify(current_password, user["password"]):
            return HTMLResponse("<h3 style='color:red;'>Current password is incorrect.</h3>")

        hashed_password = pwd_context.hash(new_password)
        cursor.execute("UPDATE mentor SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()

        return RedirectResponse(url="/mentor-login?success=password", status_code=HTTP_302_FOUND)
    except:
        traceback.print_exc()
        return HTMLResponse("<h3 style='color:red;'>An error occurred while updating password.</h3>")
    finally:
        cursor.close()
        conn.close()


@app.post("/mentee-register")
async def mentee_register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    course: str = Form(...),       # B.Tech / M.Tech
    year: str = Form(...),
    branch: str = Form(...),
    roll_no: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    try:
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Save profile photo
        photo_ext = os.path.splitext(profile_photo.filename)[-1]
        photo_filename = f"{uuid.uuid4().hex}{photo_ext}"
        photo_path = os.path.join("uploaded_photos", photo_filename)
        with open(photo_path, "wb") as buffer:
            shutil.copyfileobj(profile_photo.file, buffer)

        # Insert into database
        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO mentee (name, email, password, course, year, branch, roll_no, profile_photo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            name, email, hashed_password, course, year, branch, roll_no, photo_filename
        )
        cursor.execute(insert_query, values)
        conn.commit()

        return RedirectResponse(url="/mentee_login", status_code=303)

    except mysql.connector.Error as err:
        traceback.print_exc()
        return HTMLResponse(content=f"<h2>Database Error: {err}</h2>", status_code=500)
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse(content=f"<h2>Error: {str(e)}</h2>", status_code=500)
    finally:
        cursor.close()
        conn.close()
    
@app.post("/update-mentee-photo")
async def update_mentee_photo(request: Request, email: str = Form(...), file: UploadFile = File(...)):
    try:
        file_extension = os.path.splitext(file.filename)[1]
        photo_filename = f"{email}{file_extension}"  # Save the file with the email as its name
        photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
        
        # Save the uploaded file to the defined path
        with open(photo_path, "wb") as photo_file:
            photo_file.write(await file.read())
        
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update the mentee's profile photo in the database
        cursor.execute(
            "UPDATE mentee SET profile_photo = %s WHERE email = %s",
            (photo_path, email)
        )
        conn.commit()

        # Close the cursor and connection
        cursor.close()
        conn.close()

        # Redirect back to the mentee profile page after successfully updating the photo
        return RedirectResponse(f"/mentee_profile?email={email}", status_code=303)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating profile photo: {str(e)}")
    
@app.post("/update-mentee-profile")
async def update_mentee_profile(
    original_email: str = Form(...),
    email: str = Form(...),
    name: str = Form(...),
    course: str = Form(...),
    year: str = Form(...),
    branch: str = Form(...),
):
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update the mentee details in the database (excluding password and profile photo)
    update_query = """
    UPDATE mentee
    SET name = %s, email = %s, course = %s, year = %s, branch = %s
    WHERE email = %s
    """
    cursor.execute(
        update_query,
        (name, email, course, year, branch, original_email)
    )
    conn.commit()

    # Close the cursor and connection
    cursor.close()
    conn.close()

    return HTMLResponse(content="Profile Updated Successfully!", status_code=200)

@app.post("/update-mentee-password")
async def update_mentee_password(
    request: Request,
    email: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    try:
        # Check if new password and confirm password match
        if new_password != confirm_password:
            return HTMLResponse("<h3 style='color:red;'>New passwords do not match.</h3>")

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the current password from the database for the mentee
        cursor.execute("SELECT password FROM mentee WHERE email = %s", (email,))
        user = cursor.fetchone()

        # If user doesn't exist or current password is incorrect
        if not user or not pwd_context.verify(current_password, user["password"]):
            return HTMLResponse("<h3 style='color:red;'>Current password is incorrect.</h3>")

        # Hash the new password
        hashed_password = pwd_context.hash(new_password)

        # Update the password in the database
        cursor.execute("UPDATE mentee SET password = %s WHERE email = %s", (hashed_password, email))
        conn.commit()

        # Redirect after successful password update
        return RedirectResponse(url="/mentee_login?success=password", status_code=302)
    
    except Exception as e:
        traceback.print_exc()
        return HTMLResponse("<h3 style='color:red;'>An error occurred while updating password.</h3>")
    
    finally:
        cursor.close()
        conn.close()


@app.post("/find_mentor", response_class=HTMLResponse)
async def find_mentor(request: Request, department: str = Form(...), interests: List[str] = Form(...)):
    mentee_email = request.session.get("mentee_email")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Properly format the WHERE clause with the correct column name 'interests'
    interest_query = " OR ".join([f"interests LIKE '%{i}%'" for i in interests])
    query = f"""
        SELECT * FROM mentor
        WHERE department = %s AND ({interest_query})
    """

    cursor.execute(query, (department,))
    mentors = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("find_mentor.html", {
        "request": request,
        "mentors": mentors,
        "mentee_email": mentee_email
    })
@app.post("/submit_mentor_request", response_class=HTMLResponse)
async def submit_mentor_request(
    request: Request,
    mentor_email: str = Form(...),
    project_name: str = Form(...),
    project_description: str = Form(...)
):
    # Get mentee email from session
    mentee_email = request.session.get("mentee_email")
    
    if not mentee_email:
        return RedirectResponse(url="/mentee_login", status_code=303)

    print("Received:", mentor_email, mentee_email, project_name) 

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the request into the database
    query = """
        INSERT INTO mentor_requests (mentor_email, mentee_email, project_name, project_description, status)
        VALUES (%s, %s, %s, %s, 'Pending')
    """
    cursor.execute(query, (mentor_email, mentee_email, project_name, project_description))
    conn.commit()

    # Close the database connection
    cursor.close()
    conn.close()

    # Render a success page or message
    return templates.TemplateResponse("request_success.html", {
        "request": request,
        "mentor_email": mentor_email
    })

@app.post("/update_request_status")
async def update_request_status(
    request: Request,
    mentee_email: str = Form(...),
    mentor_email: str = Form(...),
    project_name: str = Form(...),
    project_description: str = Form(...),
    status: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    update_query = """
        UPDATE mentor_requests
        SET status = %s
        WHERE mentee_email = %s AND mentor_email = %s AND project_name = %s AND project_description = %s
    """
    cursor.execute(update_query, (status, mentee_email, mentor_email, project_name, project_description))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url=f"/project_requests/{mentor_email}", status_code=303)

@app.get("/start_chat/{mentor_email}")
async def start_chat(request: Request, mentor_email: str):
    request.session["mentor_email"] = mentor_email
    return RedirectResponse(url="/chat", status_code=303)

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, mentor_email: str, mentee_email: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT sender, message, timestamp FROM chats 
            WHERE mentor_email = %s AND mentee_email = %s
            ORDER BY timestamp ASC
        """, (mentor_email, mentee_email))
        messages = cursor.fetchall()

        cursor.close()
        conn.close()

        return templates.TemplateResponse("chat_page.html", {
            "request": request,
            "mentor_email": mentor_email,
            "mentee_email": mentee_email,
            "messages": messages
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/send")
async def send_message(request: Request):
    form = await request.form()
    
    sender = form.get("sender")
    mentor_email = form.get("mentor_email")
    mentee_email = form.get("mentee_email")
    message = form.get("message")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chats (mentor_email, mentee_email, sender, message)
        VALUES (%s, %s, %s, %s)
    """, (mentor_email, mentee_email, sender, message))

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url=f"/chat?mentor_email={mentor_email}&mentee_email={mentee_email}", status_code=303)

@app.get("/mentor/chat-mentees", response_class=HTMLResponse)
async def mentor_chat_mentees(request: Request):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/mentor-login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            m.mentee_email, 
            me.name AS mentee_name,
            me.branch, 
            me.roll_no,
            MAX(c.timestamp) AS last_msg_time,
            (SELECT message FROM chats WHERE mentor_email = %s AND mentee_email = m.mentee_email ORDER BY timestamp DESC LIMIT 1) AS last_message,
            (SELECT COUNT(*) FROM chats WHERE mentor_email = %s AND mentee_email = m.mentee_email AND sender = 'mentee' AND is_read = 0) AS unread_count
        FROM mentor_requests m
        JOIN mentee me ON m.mentee_email = me.email
        LEFT JOIN chats c ON m.mentee_email = c.mentee_email AND m.mentor_email = c.mentor_email
        WHERE m.mentor_email = %s AND m.status = 'accepted'
        GROUP BY m.mentee_email
        ORDER BY last_msg_time DESC
    """
    cursor.execute(query, (mentor_email, mentor_email, mentor_email))
    mentees = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("mentor_chat_mentees.html", {
        "request": request,
        "mentees": mentees
    })

@app.get("/mentor/chat-with-mentee/{mentee_email}", response_class=HTMLResponse)
async def mentor_chat_with_mentee(request: Request, mentee_email: str):
    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse(url="/mentor-login", status_code=303)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Mark mentee messages as read
    cursor.execute("""
        UPDATE chats SET is_read = 1 
        WHERE mentor_email = %s AND mentee_email = %s AND sender = 'mentee'
    """, (mentor_email, mentee_email))
    conn.commit()

    # Fetch messages
    cursor.execute("""
        SELECT sender, message, timestamp FROM chats
        WHERE mentor_email = %s AND mentee_email = %s
        ORDER BY timestamp ASC
    """, (mentor_email, mentee_email))
    messages = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("mentor_chat_page.html", {
        "request": request,
        "mentee_email": mentee_email,
        "messages": messages,
        "mentor_email": mentor_email
    })

@app.post("/mentor/chat/send")
async def mentor_send_message(request: Request):
    form = await request.form()
    mentor_email = form.get("mentor_email")
    mentee_email = form.get("mentee_email")
    message = form.get("message")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO chats (mentor_email, mentee_email, sender, message, is_read)
        VALUES (%s, %s, 'mentor', %s, 0)
    """, (mentor_email, mentee_email, message))

    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url=f"/mentor/chat-with-mentee/{mentee_email}", status_code=303)

@app.post("/mentor/schedule-meeting")
async def schedule_meeting(request: Request):
    form = await request.form()
    mentor_email = request.session.get("mentor_email")
    mentee_email = form.get("mentee_email")
    link = form.get("meeting_link")
    date = form.get("meeting_date")
    time = form.get("meeting_time")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meetings (mentor_email, mentee_email, meeting_link, meeting_date, meeting_time)
        VALUES (%s, %s, %s, %s, %s)
    """, (mentor_email, mentee_email, link, date, time))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(f"/mentor/chat-with-mentee/{mentee_email}", status_code=303)

@app.get("/mentee/meetings")
async def get_meetings(mentee_email: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT meeting_link, meeting_date, meeting_time
        FROM meetings
        WHERE mentee_email = %s
        ORDER BY meeting_date DESC, meeting_time DESC
        LIMIT 1
        """
        cursor.execute(query, (mentee_email,))
        meeting = cursor.fetchone()

        if meeting:
            return {
                "status": "success",
                "meeting_link": meeting["meeting_link"],
                "meeting_date": str(meeting["meeting_date"]),
                "meeting_time": str(meeting["meeting_time"])
            }
        else:
            return {"status": "no_meeting", "message": "No meeting scheduled."}

    except Exception as e:
        print("Error fetching meetings:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch meeting data.")
    finally:
        cursor.close()
        conn.close()

@app.get("/mentee/view-meeting", response_class=HTMLResponse)
async def mentee_view_meeting(request: Request):
    mentee_email = request.session.get("mentee_email")
    
    if not mentee_email:
        return RedirectResponse("/login", status_code=302)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get current date and time to filter for upcoming or not-done meetings
        current_date = datetime.now().date()
        current_time = datetime.now().time()

        # Fetch all upcoming or not attended meetings
        cursor.execute("""
            SELECT m.meeting_link, m.meeting_date, m.meeting_time, mentor.name 
            FROM meetings m
            JOIN mentor ON m.mentor_email = mentor.email
            WHERE m.mentee_email = %s
            AND (m.meeting_date > %s OR (m.meeting_date = %s AND m.meeting_time > %s))
            ORDER BY m.meeting_date ASC, m.meeting_time ASC
        """, (mentee_email, current_date, current_date, current_time))

        meetings = cursor.fetchall()

        meeting_list = []
        for meeting in meetings:
            link, date, time, mentor_name = meeting
            hour = int(str(time).split(":")[0])
            meridian = "AM" if hour < 12 else "PM"

            meeting_list.append({
                "mentor_name": mentor_name,
                "meeting_date": date,
                "meeting_time": time,
                "meeting_link": link,
                "meridian": meridian
            })

        return templates.TemplateResponse("mentee_meetings.html", {
            "request": request,
            "meetings": meeting_list
        })

    finally:
        cursor.close()
        conn.close()

def get_current_user(request: Request) -> str:
    # Retrieve the mentor's email from the session stored in request.state
    mentor_email = request.session.get("mentor_email")
    if mentor_email is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return mentor_email

class TaskRequest(BaseModel):
    task_name: str
    task_description: str


@app.get("/assign-task", response_class=HTMLResponse)
async def show_assign_task_page(request: Request):
    mentor_email = request.session.get("mentor_email")  # Assuming mentor is logged in
    if not mentor_email:
        raise HTTPException(status_code=401, detail="You must be logged in to assign tasks")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get accepted mentees and their names
    cursor.execute("""
        SELECT m.mentee_email AS email, me.name
        FROM mentor_requests m
        JOIN mentee me ON m.mentee_email = me.email
        WHERE m.mentor_email = %s AND m.status = 'accepted'
    """, (mentor_email,))
    
    mentee_list = cursor.fetchall()

    cursor.close()
    db.close()

    return templates.TemplateResponse(
        "assign_task.html", 
        {
            "request": request, 
            "mentee_list": mentee_list, 
            "mentor_email": mentor_email
        }
    )

@app.post("/assign_task")
async def assign_task(
    task_name: str = Form(...),
    task_description: str = Form(...),
    mentee_email: str = Form(...),
    mentor_email: str = Form(...),
):
    db = get_db_connection()
    cursor = db.cursor()

    # Get project_name for accepted mentor request
    cursor.execute("""
        SELECT project_name 
        FROM mentor_requests 
        WHERE mentor_email = %s AND mentee_email = %s AND status = 'accepted'
    """, (mentor_email, mentee_email))
    result = cursor.fetchone()

    if not result:
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="No accepted request found for this mentee.")

    project_name = result[0]

    # Get next task_id_within_project for this project
    cursor.execute("""
        SELECT MAX(task_id_within_project) 
        FROM tasks 
        WHERE mentor_email = %s AND mentee_email = %s AND project_name = %s
    """, (mentor_email, mentee_email, project_name))
    max_task_id = cursor.fetchone()[0]
    next_task_id = 1 if max_task_id is None else max_task_id + 1

    # Insert new task with task_id_within_project
    cursor.execute("""
        INSERT INTO tasks (mentor_email, mentee_email, task_name, task_description, project_name, task_id_within_project)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (mentor_email, mentee_email, task_name, task_description, project_name, next_task_id))

    db.commit()
    cursor.close()
    db.close()

    return JSONResponse(content={"message": f"Task #{next_task_id} assigned successfully!"}, status_code=200)


@app.get("/view_tasks", response_class=HTMLResponse)
async def view_tasks(request: Request):
    mentee_email = request.session.get("mentee_email")  # Assuming mentee is logged in
    if not mentee_email:
        raise HTTPException(status_code=401, detail="You must be logged in to view tasks")

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get distinct tasks assigned to the mentee
    cursor.execute("""
        SELECT DISTINCT 
            t.task_id_within_project AS task_no, 
            t.task_name, 
            t.task_description, 
            t.project_name, 
            mr.mentor_email
        FROM tasks t
        JOIN mentor_requests mr ON t.mentor_email = mr.mentor_email
        WHERE t.mentee_email = %s
    """, (mentee_email,))

    tasks = cursor.fetchall()

    cursor.close()
    db.close()

    return templates.TemplateResponse(
        "view_tasks.html", 
        {"request": request, "tasks": tasks}
    )

@app.get("/task_submission/{task_no}", response_class=HTMLResponse)
async def task_submission_page(request: Request, task_no: int):
    mentee_email = request.session.get("mentee_email")

    if not mentee_email:
        return RedirectResponse("/mentee_login", status_code=302)

    # Get task details by task_no
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, task_name, task_description 
        FROM tasks
        WHERE task_id_within_project = %s
    """, (task_no,))
    task = cursor.fetchone()
    
    # ✅ Ensure previous result is cleared before next query
    while cursor.nextset():
        pass

    if not task:
        return HTMLResponse("Task not found", status_code=404)

    task_id, task_name, task_description = task

    # Check if task is already submitted
    cursor.execute("""
        SELECT * FROM task_submissions WHERE task_id = %s AND mentee_email = %s
    """, (task_id, mentee_email))
    submission = cursor.fetchone()

    cursor.close()
    conn.close()

    return templates.TemplateResponse("task_submission.html", {
        "request": request,
        "task_no": task_no,
        "task_name": task_name,
        "task_description": task_description,
        "submitted": bool(submission),
        "submission": submission
    })


@app.post("/submit_task/{task_no}")
async def submit_task(request: Request, task_no: int, code_file: UploadFile = File(...), issues: str = Form("")):
    mentee_email = request.session.get("mentee_email")

    if not mentee_email:
        return RedirectResponse("/mentee_login", status_code=302)

    # Get task ID by task_no
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure no unread result is left from previous queries
        cursor.execute("""SELECT id FROM tasks WHERE task_id_within_project = %s""", (task_no,))
        task = cursor.fetchone()

        if not task:
            return HTMLResponse("Task not found", status_code=404)

        task_id = task[0]

        # Clear the result set before executing another query (to avoid 'Unread result found' error)
        cursor.fetchall()  # Ensuring no result is left

        # Save the uploaded file
        file_location = os.path.join(UPLOAD_DIR, f"{mentee_email}_task{task_no}_{code_file.filename}")
        with open(file_location, "wb") as f:
            shutil.copyfileobj(code_file.file, f)

        # Insert task submission into the database
        cursor.execute("""
            INSERT INTO task_submissions (task_id, mentee_email, code_file_path, issues, status)
            VALUES (%s, %s, %s, %s, 'submitted')
        """, (task_id, mentee_email, file_location, issues))
        conn.commit()

        return RedirectResponse(f"/task_submission/{task_no}", status_code=302)

    except Exception as e:
        conn.rollback()
        return HTMLResponse(f"Error occurred: {e}", status_code=500)

    finally:
        cursor.close()
        conn.close()

@app.get("/mentor/task_submissions", response_class=HTMLResponse)
async def mentor_task_submissions(request: Request):
    logging.info("mentor_task_submissions route accessed.")

    mentor_email = request.session.get("mentor_email")
    if not mentor_email:
        return RedirectResponse("/mentor_login", status_code=302)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT ts.id, ts.task_id, ts.mentee_email, ts.code_file_path, ts.issues, ts.status, t.task_name
            FROM task_submissions ts
            JOIN tasks t ON ts.task_id = t.id
            WHERE t.mentor_email = %s
        """
        cursor.execute(query, (mentor_email,))
        submissions = cursor.fetchall()

        return templates.TemplateResponse("mentor_task_submissions.html", {
            "request": request,
            "submissions": submissions
        })
    except Exception as e:
        logging.error(f"Error fetching task submissions: {e}")
        return HTMLResponse(f"An error occurred: {e}", status_code=500)
    finally:
        cursor.close()
        conn.close()


@app.post("/mentor/feedback/{submission_id}")
async def mentor_feedback(request: Request, submission_id: int, feedback: str = Form(...)):
    mentor_email = request.session.get("mentor_email")

    if not mentor_email:
        return RedirectResponse("/mentor_login", status_code=302)

    # Insert feedback into the task_feedback table
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO task_feedback (task_submission_id, mentor_email, feedback)
        VALUES (%s, %s, %s)
    """, (submission_id, mentor_email, feedback))
    conn.commit()

    return RedirectResponse("/mentor/task_submissions", status_code=302)

# Directly serve files from the uploaded_code directory
@app.get("/uploaded_code/{file_name}")
async def serve_file(file_name: str):
    file_location = os.path.join(UPLOAD_DIR, file_name)

    # Check if the file exists
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")

    # Return the file as a response
    return FileResponse(file_location)

UPLOAD_DIR = "uploaded_code"  # Path where the files are stored.
app.mount("/uploaded_code", StaticFiles(directory=UPLOAD_DIR), name="uploaded_code")


@app.get("/contact", response_class=HTMLResponse)
async def contact_form(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.post("/submit_contact", response_class=HTMLResponse)
async def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    try:
        conn=get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO contact_messages (name, email, message)
            VALUES (%s, %s, %s)
        """, (name, email, message))
        conn.commit()
        cursor.close()
        conn.close()
        return templates.TemplateResponse("contact.html", {
            "request": request,
            "message": "Thank you! Your message has been received."
        })
    except Exception as e:
        return templates.TemplateResponse("contact.html", {
            "request": request,
            "message": f"Error: {e}"
        })
    
@app.get("/mentee_forgot_password", response_class=HTMLResponse)
async def show_forgot_password(request: Request):
    return templates.TemplateResponse("mentee_forgot_password.html", {"request": request})

@app.post("/mentee_reset_password")
async def reset_password(email: str = Form(...), new_password: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    cursor.execute("UPDATE mentee SET password = %s WHERE email = %s", (hashed_pw, email))
    conn.commit()
    cursor.close()
    conn.close()
    return RedirectResponse(url="/mentee_login", status_code=302)

@app.get("/mentor_forgot_password", response_class=HTMLResponse)
async def show_forgot_password(request: Request):
    return templates.TemplateResponse("mentor_forgot_password.html", {"request": request})

@app.post("/mentor_reset_password")
async def reset_mentor_password(request: Request, email: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    if new_password != confirm_password:
        return HTMLResponse(content="<h3>Passwords do not match.</h3>", status_code=400)
    
    # Hash the new password
    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    # Update password in DB (using raw MySQL)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE mentor SET password=%s WHERE email=%s", (hashed_pw, email))
    conn.commit()
    cursor.close()
    conn.close()

    # Redirect to login with success message
    return RedirectResponse(url="/mentor-login?success=password", status_code=303)