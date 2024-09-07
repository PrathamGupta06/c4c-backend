from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore
from helper import extract_statement_details
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('./serviceAccountKey.json')  # Update this path
firebase_admin.initialize_app(cred)
db = firestore.client()

# Function to check if file type is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Save statement details to Firebase
def save_to_firebase(statement_details):
    for item in statement_details:
        # Add each transaction as a document to the 'statements' collection
        db.collection('statements').add(item)

# API endpoint to upload the PDF and process it
@app.route('/upload_statement_pdf', methods=['POST'])
def upload_statement_pdf():
    print(request.files)
    if 'file' not in request.files:
        print("HERE")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Extract details from the uploaded PDF
        statement_details = extract_statement_details(file_path)

        # Save to Firebase
        save_to_firebase(statement_details)

        return jsonify({"message": "Statement uploaded and processed successfully!", "data": statement_details}), 201

    return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(debug=True)
