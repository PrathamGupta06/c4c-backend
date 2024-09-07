from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore
from helper import extract_statement_details
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

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

@app.route('/get_statements', methods=['GET'])
def get_statements():
    try:
        # Retrieve all documents from the 'statements' collection
        statements_ref = db.collection('statements')
        docs = statements_ref.stream()

        # Create a list to store formatted statement data
        statements_list = []

        for doc in docs:
            data = doc.to_dict()

            # Format the data in the required format
            formatted_statement = {
                "date": data.get("date", ""),
                "narration": data.get("narration", ""),
                "withdrawal amount": data.get("withdrawal_amount", ""),
                "deposit amount": data.get("deposit_amount", ""),
                "closing balance": data.get("closing_balance", "")
            }

            # Append formatted statement to the list
            statements_list.append(formatted_statement)

        # Return the list of statements in JSON format
        return jsonify(statements_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
