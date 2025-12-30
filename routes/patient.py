"""
Patient Routes for MediFriend
"""
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from routes.auth import role_required
from database import (
    get_all_doctors, create_appointment, get_patient_appointments,
    cancel_appointment, get_patient_prescriptions,
    create_uploaded_prescription, get_patient_uploaded_prescriptions,
    delete_uploaded_prescription as db_delete_uploaded_prescription,
    get_user_notifications, get_unread_notification_count, mark_notifications_as_read,
    delete_read_notifications,
    create_rating, check_existing_rating, get_doctor_ratings, get_doctor_average_rating,
    search_doctors,
    create_lab_report, get_patient_lab_reports, get_lab_report_by_id, delete_lab_report,
    get_lab_report_trends, execute_query
)
from config import allowed_file, Config
from datetime import date, datetime
from functools import wraps
from werkzeug.utils import secure_filename
import os
import json
import base64
import uuid
import traceback
import google.generativeai as genai
import PIL.Image

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')


@patient_bp.route('/dashboard')
@role_required('PATIENT')
def dashboard():
    """
    Patient dashboard - main hub
    """
    user_id = session.get('user_id')
    full_name = session.get('full_name')
    
    return render_template('patient_dashboard.html', 
                         user_name=full_name,
                         user_id=user_id)


@patient_bp.route('/appointments')
@role_required('PATIENT')
def appointments():
    """
    View patient's appointments (excluding rejected ones)
    """
    user_id = session.get('user_id')
    appointments_list = get_patient_appointments(user_id)
    
    return render_template('patient_appointments.html', 
                         appointments=appointments_list)


@patient_bp.route('/book-appointment', methods=['GET', 'POST'])
@role_required('PATIENT')
def book_appointment():
    """
    Book new appointment
    """
    if request.method == 'POST':
        patient_id = session.get('user_id')
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('date')
        appointment_time = request.form.get('time')
        symptoms = request.form.get('symptoms', '').strip()
        
        # Validation
        if not doctor_id or not appointment_date or not appointment_time:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('patient.book_appointment'))
        
        try:
            # Create appointment
            appointment_id = create_appointment(
                patient_id=patient_id,
                doctor_id=int(doctor_id),
                date=appointment_date,
                time=appointment_time,
                symptoms=symptoms if symptoms else None
            )
            
            flash('Appointment scheduled successfully! Waiting for doctor confirmation.', 'success')
            return redirect(url_for('patient.dashboard'))
            
        except Exception as e:
            flash(f'Error booking appointment: {str(e)}', 'danger')
            return redirect(url_for('patient.book_appointment'))
    
    # GET request - show booking form
    doctors = get_all_doctors()
    today = date.today().isoformat()
    
    return render_template('book_appointment.html', 
                         doctors=doctors,
                         today=today)


@patient_bp.route('/cancel-appointment/<int:appointment_id>', methods=['POST'])
@role_required('PATIENT')
def cancel_appointment_route(appointment_id):
    """
    Cancel an appointment
    """
    try:
        cancel_appointment(appointment_id)
        flash('Appointment cancelled successfully.', 'success')
    except Exception as e:
        flash(f'Error cancelling appointment: {str(e)}', 'danger')
    
    return redirect(url_for('patient.appointments'))


@patient_bp.route('/prescriptions')
@role_required('PATIENT')
def prescriptions():
    """
    View patient's prescriptions (both doctor-written and uploaded)
    """
    user_id = session.get('user_id')
    
    # Get doctor-written prescriptions
    prescriptions_list = get_patient_prescriptions(user_id)
    
    # Get uploaded prescriptions
    uploaded_prescriptions_list = get_patient_uploaded_prescriptions(user_id)
    
    return render_template('patient_prescriptions.html',
                         prescriptions=prescriptions_list,
                         uploaded_prescriptions=uploaded_prescriptions_list)


@patient_bp.route('/upload-prescription-api', methods=['POST'])
@role_required('PATIENT')
def upload_prescription_api():
    """
    API endpoint to upload and process prescription image
    """
    try:
        user_id = session.get('user_id')
        
        # Check if file is present
        if 'prescription_image' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['prescription_image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Read file data
        file_data = file.read()
        
        # Import extraction function from app
        from app import extract_prescription_from_image
        
        # Extract data using Gemini
        extracted_data, explanation = extract_prescription_from_image(file_data)
        
        if extracted_data is None:
            return jsonify({'success': False, 'error': explanation}), 500
        
        # Save to database
        create_uploaded_prescription(
            patient_id=user_id,
            filename=file.filename,
            extracted_data=json.dumps(extracted_data),
            explanation=explanation
        )
        
        return jsonify({'success': True, 'message': 'Prescription uploaded successfully'})
        
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@patient_bp.route('/delete-uploaded-prescription/<int:upload_id>', methods=['POST'])
@role_required('PATIENT')
def delete_uploaded_prescription(upload_id):
    """
    Delete an uploaded prescription
    """
    try:
        db_delete_uploaded_prescription(upload_id)
        flash('Prescription deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting prescription: {str(e)}', 'danger')
    
    return redirect(url_for('patient.prescriptions'))


@patient_bp.route('/upload-prescription')
@role_required('PATIENT')
def upload_prescription():
    """
    Upload handwritten prescription for AI reading
    """
    # TODO: Link to existing prescription reader
    return render_template('upload_prescription.html')


# --------------------------------------------------
# 📬 Notification API Routes
# --------------------------------------------------

@patient_bp.route('/api/notifications', methods=['GET'])
@role_required('PATIENT')
def get_notifications():
    """
    Get all unread notifications for the current patient
    """
    user_id = session.get('user_id')
    notifications = get_user_notifications(user_id, unread_only=True)
    return jsonify({'success': True, 'notifications': notifications})


@patient_bp.route('/api/notifications/count', methods=['GET'])
@role_required('PATIENT')
def get_notification_count():
    """
    Get count of unread notifications
    """
    user_id = session.get('user_id')
    count = get_unread_notification_count(user_id)
    return jsonify({'success': True, 'count': count})


@patient_bp.route('/api/notifications/mark-read', methods=['POST'])
@role_required('PATIENT')
def mark_notifications_read():
    """
    Mark all notifications as read and delete them
    """
    user_id = session.get('user_id')
    mark_notifications_as_read(user_id)
    delete_read_notifications(user_id)
    return jsonify({'success': True})


# --------------------------------------------------
# ⭐ Doctor Rating Routes
# --------------------------------------------------

@patient_bp.route('/rate-doctor/<int:appointment_id>', methods=['GET', 'POST'])
@role_required('PATIENT')
def rate_doctor(appointment_id):
    """
    Rate a doctor after completed appointment
    """
    patient_id = session.get('user_id')
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        review_text = request.form.get('review_text', '').strip()
        
        # Validation
        if not rating:
            flash('Please select a rating.', 'danger')
            return redirect(url_for('patient.rate_doctor', appointment_id=appointment_id))
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                flash('Rating must be between 1 and 5.', 'danger')
                return redirect(url_for('patient.rate_doctor', appointment_id=appointment_id))
            
            # Check if already rated
            existing_rating = check_existing_rating(patient_id, appointment_id)
            if existing_rating:
                flash('You have already rated this appointment.', 'warning')
                return redirect(url_for('patient.appointments'))
            
            # Get appointment details to get doctor_id
            query = "SELECT doctor_id, status FROM appointments WHERE id = ? AND patient_id = ?"
            appointment = execute_query(query, (appointment_id, patient_id), fetchone=True)
            
            if not appointment:
                flash('Appointment not found.', 'danger')
                return redirect(url_for('patient.appointments'))
            
            if appointment['status'] not in ['COMPLETED', 'REJECTED']:
                flash('You can only rate completed or rejected appointments.', 'warning')
                return redirect(url_for('patient.appointments'))
            
            # Create rating
            create_rating(
                doctor_id=appointment['doctor_id'],
                patient_id=patient_id,
                appointment_id=appointment_id,
                rating=rating,
                review_text=review_text if review_text else None
            )
            
            flash('Thank you for your feedback!', 'success')
            return redirect(url_for('patient.appointments'))
            
        except ValueError:
            flash('Invalid rating value.', 'danger')
            return redirect(url_for('patient.rate_doctor', appointment_id=appointment_id))
        except Exception as e:
            flash(f'Error submitting rating: {str(e)}', 'danger')
            return redirect(url_for('patient.rate_doctor', appointment_id=appointment_id))
    
    # GET request - show rating form
    query = """
        SELECT a.id, a.date, a.time, u.full_name as doctor_name, dd.specialization
        FROM appointments a
        JOIN users u ON a.doctor_id = u.id
        JOIN doctor_details dd ON u.id = dd.user_id
        WHERE a.id = ? AND a.patient_id = ? AND (a.status = 'COMPLETED' OR a.status = 'REJECTED')
    """
    appointment = execute_query(query, (appointment_id, patient_id), fetchone=True)
    
    if not appointment:
        flash('Appointment not found or not eligible for rating.', 'danger')
        return redirect(url_for('patient.appointments'))
    
    # Check if already rated
    existing_rating = check_existing_rating(patient_id, appointment_id)
    if existing_rating:
        flash('You have already rated this appointment.', 'warning')
        return redirect(url_for('patient.appointments'))
    
    return render_template('rate_doctor.html', appointment=appointment)


@patient_bp.route('/api/search-doctors', methods=['GET'])
@role_required('PATIENT')
def api_search_doctors():
    """
    AJAX endpoint for searching doctors
    Returns JSON results for live search
    """
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 1:
        return jsonify({'success': False, 'message': 'Query too short', 'doctors': []})
    
    try:
        doctors = search_doctors(query)
        
        # Format results for frontend
        results = [{
            'id': doc['id'],
            'name': doc['full_name'],
            'specialization': doc['specialization'],
            'qualification': doc['qualification'] or 'N/A',
            'experience_years': doc['experience_years'],
            'consultation_fee': doc['consultation_fee'],
            'average_rating': doc['average_rating'] or 0.0,
            'total_ratings': doc['total_ratings'] or 0
        } for doc in doctors]
        
        return jsonify({
            'success': True,
            'count': len(results),
            'doctors': results
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'doctors': []})


@patient_bp.route('/test-reports')
@role_required('PATIENT')
def test_reports():
    """
    View patient's lab test reports with timeline
    """
    user_id = session.get('user_id')
    reports = get_patient_lab_reports(user_id)
    
    # Group reports by test type for easy filtering
    reports_by_type = {}
    for report in reports:
        test_type = report['test_type']
        if test_type not in reports_by_type:
            reports_by_type[test_type] = []
        reports_by_type[test_type].append(report)
    
    return render_template('patient_test_reports.html',
                         reports=reports,
                         reports_by_type=reports_by_type)


@patient_bp.route('/upload-test-report', methods=['GET', 'POST'])
@role_required('PATIENT')
def upload_test_report():
    """
    Upload lab test report with AI extraction
    """
    if request.method == 'POST':
        # Validate file
        if 'test_report' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('patient.upload_test_report'))
        
        file = request.files['test_report']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('patient.upload_test_report'))
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Only PNG, JPG, JPEG, PDF allowed', 'danger')
            return redirect(url_for('patient.upload_test_report'))
        
        # Get form data
        test_type = request.form.get('test_type', '').strip()
        test_date = request.form.get('test_date', '').strip()
        notes = request.form.get('notes', '').strip()
        
        if not test_type or not test_date:
            flash('Test type and date are required', 'danger')
            return redirect(url_for('patient.upload_test_report'))
        
        try:
            # Save file
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            
            # Extract values using Gemini AI
            extracted_values = extract_health_values_from_report(file_path, test_type)
            
            # Save to database
            user_id = session.get('user_id')
            create_lab_report(
                patient_id=user_id,
                test_type=test_type,
                test_date=test_date,
                report_image=unique_filename,
                extracted_values_json=json.dumps(extracted_values) if extracted_values else None,
                notes=notes
            )
            
            flash('Test report uploaded successfully!', 'success')
            return redirect(url_for('patient.test_reports'))
            
        except Exception as e:
            flash(f'Error uploading report: {str(e)}', 'danger')
            return redirect(url_for('patient.upload_test_report'))
    
    # GET request - show upload form
    return render_template('upload_test_report.html')


@patient_bp.route('/delete-test-report/<int:report_id>', methods=['POST'])
@role_required('PATIENT')
def delete_test_report(report_id):
    """
    Delete a test report
    """
    user_id = session.get('user_id')
    
    # Verify ownership
    report = get_lab_report_by_id(report_id)
    if not report or report['patient_id'] != user_id:
        flash('Report not found or unauthorized', 'danger')
        return redirect(url_for('patient.test_reports'))
    
    try:
        # Delete file from filesystem
        file_path = os.path.join(Config.UPLOAD_FOLDER, report['report_image'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        delete_lab_report(report_id)
        flash('Test report deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'danger')
    
    return redirect(url_for('patient.test_reports'))


def extract_health_values_from_report(image_path, test_type):
    """
    Use Gemini AI to extract health parameter values from lab report image
    """
    try:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Load image
        img = PIL.Image.open(image_path)
        
        # Simple, generalized prompt that works for ANY medical report
        prompt = f'''Analyze this medical lab report image.

Extract ALL numerical test values and health parameters you can find.
Look for any test results, measurements, or health indicators - blood tests, vitals, chemistry panels, etc.

Return your response as a valid JSON object where:
- Keys are the parameter names (use underscores instead of spaces, keep names clear and descriptive)
- Values are ONLY the numeric measurements (just numbers, no units or text)

For example: {{"Hemoglobin": 13.5, "WBC_Count": 7500, "Blood_Pressure_Systolic": 120}}

IMPORTANT RULES:
1. Extract EVERY value you can see in the image
2. Use clear, descriptive names for each parameter
3. Include ONLY numbers as values (no units like "mg/dL" or ranges)
4. Return ONLY the JSON object - no explanations, no markdown formatting, no extra text
5. If you truly cannot find ANY numerical values, return: {{}}

Test type context (to help you identify relevant values): {test_type}

JSON output:'''
        
        # Generate response with detailed logging
        print(f"\n{'='*70}")
        print(f"🔬 PROCESSING: {test_type} report")
        print(f"📁 Image: {image_path}")
        print(f"{'='*70}")
        
        response = model.generate_content([prompt, img])
        result_text = response.text.strip()
        
        # Show raw AI response
        print(f"\n📥 RAW AI RESPONSE:")
        print(f"{'-'*70}")
        print(result_text)
        print(f"{'-'*70}\n")
        
        # Clean response - handle various markdown formats
        original_text = result_text
        result_text = result_text.strip()
        
        # Remove markdown code blocks
        if result_text.startswith('```json'):
            result_text = result_text[7:]
        elif result_text.startswith('```'):
            result_text = result_text[3:]
        
        if result_text.endswith('```'):
            result_text = result_text[:-3]
        
        result_text = result_text.strip()
        
        # Try to find JSON in the response if it contains extra text
        if '{' in result_text and '}' in result_text:
            start = result_text.index('{')
            end = result_text.rindex('}') + 1
            result_text = result_text[start:end]
        else:
            print("⚠️  WARNING: No JSON object found in AI response!")
            print(f"This usually means the AI couldn't read the image or didn't find values.")
            return {}
        
        print(f"📤 CLEANED JSON:")
        print(f"{'-'*70}")
        print(result_text)
        print(f"{'-'*70}\n")
        
        # Parse JSON
        extracted_values = json.loads(result_text)
        
        if extracted_values:
            print(f"✅ SUCCESS: Extracted {len(extracted_values)} values")
            for key, value in extracted_values.items():
                print(f"   • {key}: {value}")
        else:
            print(f"⚠️  EMPTY RESULT: AI returned empty JSON object")
        
        print(f"\n{'='*70}\n")
        return extracted_values
        
    except json.JSONDecodeError as e:
        print(f"\n❌ JSON PARSING ERROR!")
        print(f"Error: {e}")
        print(f"Attempted to parse:")
        print(f"{'-'*70}")
        print(result_text if 'result_text' in locals() else "No text available")
        print(f"{'-'*70}\n")
        return {}
    except Exception as e:
        print(f"\n❌ EXTRACTION ERROR!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        print(f"\n{'='*70}\n")
        return {}


