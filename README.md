# 🏥 MediFriend

A complete Healthcare Management Platform built with Flask, SQLite, and integrated AI features (Chatbot & Prescription Reader).

## ✨ Features

### 🤒 Patient Features
- **User Registration & Login**: Secure signup and authentication
- **Dashboard**: Centralized hub for all patient activities
- **Book Appointments**: Schedule visits with doctors (Coming Soon)
- **View Appointments**: Track appointment history and status (Coming Soon)
- **Prescription Reader**: Upload handwritten prescriptions and get AI-powered explanations
- **View Prescriptions**: Access all doctor-prescribed medications (Coming Soon)
- **MediFriend Chatbot**: Get instant medical assistance and health advice
- **Profile Management**: Update personal and medical information

### 👨‍⚕️ Doctor Features
- **Doctor Login**: Secure authentication for medical professionals
- **Dashboard**: Centralized hub for doctor activities
- **View Appointments**: Manage patient appointments (Coming Soon)
- **Patient Records**: Access patient medical history (Coming Soon)
- **Write Prescriptions**: Create formal prescriptions for patients (Coming Soon)
- **Prescription Reader**: View and analyze uploaded prescriptions
- **MediFriend Chatbot**: Access medical information chatbot
- **Profile Management**: Update professional information

### 🤖 AI Features
- **Prescription Reader**: Uses Google Gemini Vision AI to read and explain handwritten prescriptions
- **MediFriend Chatbot**: AI-powered medical assistant for health queries and guidance

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite3
- **AI/ML**: Google Gemini AI (gemini-2.5-pro, gemini-2.5-flash)
- **Image Processing**: OpenCV
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Flask Sessions with password hashing (Werkzeug)

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Google Gemini API Key

### Setup Steps

1. **Activate Virtual Environment (Windows PowerShell)**
   ```powershell
   .\env\Scripts\Activate.ps1
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize Database**
   ```bash
   python -c "from database import init_db; init_db()"
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

The application will start at: `http://127.0.0.1:5000`

## 📊 Database Schema

### Tables
- **users**: Stores both patients and doctors
- **patient_details**: Patient-specific information
- **doctor_details**: Doctor-specific information
- **appointments**: Appointment bookings
- **prescriptions**: Formal prescriptions by doctors
- **uploads**: Uploaded prescription images and documents

## 🎨 Design Theme

MediFriend features a modern, professional healthcare theme:
- **Primary Colors**: Purple/Blue gradient (#667eea → #764ba2)
- **Accent Colors**: Medical blue (#2a7de1)
- **Clean Layout**: Card-based responsive design
- **Icons**: Font Awesome medical icons
- **Typography**: Poppins font family

## 📝 Next Steps & Roadmap

### Phase 2: Appointment System ⏳
- Doctor availability schedule management
- Appointment booking flow
- Appointment status updates
- Email/SMS notifications

### Phase 3: Prescription Management ⏳
- Link uploaded prescriptions to patient records
- Doctor prescription writing interface
- Prescription download/print functionality

### Phase 4: Advanced Features ⏳
- Lab reports upload and management
- Video consultation integration
- Billing and payment system
- Medical history timeline

---

**Built with ❤️ for better healthcare management**

