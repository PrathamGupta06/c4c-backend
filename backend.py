from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore
from helper import extract_statement_details, answer_query
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
# firebase_admin.initialize_app(cred)
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
                "withdrawal_amount": data.get("withdrawal_amount", ""),
                "deposit_amount": data.get("deposit_amount", ""),
                "closing_balance": data.get("closing_balance", ""),
                "payment_method": data.get("payment_method", ""),
                "category": data.get("category", ""),
                "classification": data.get("classification", "")
            }

            # Append formatted statement to the list
            statements_list.append(formatted_statement)

        # Return the list of statements in JSON format
        return jsonify(statements_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/dashboard', methods=['GET'])
def dashboard():
    statements = get_statements().get_json()

    expenditure_category_data = {}
    for statement in statements:
        category = statement["category"]
        withdrawal_amount = statement["withdrawal_amount"]
        if not withdrawal_amount:
            continue
        
        if category in expenditure_category_data:
            expenditure_category_data[category] += float(withdrawal_amount.replace(",", ""))
        else:
            expenditure_category_data[category] = float(withdrawal_amount.replace(",", ""))
        
    payment_methods_data = {}
    for statement in statements:
        payment_method = statement["payment_method"]
        payment_methods_data[payment_method] = payment_methods_data.get(payment_method, 0) + 1

    fixed_categories = ['Bills and Recharges', 'Medical']
    necessary_categories = ['Educational', 'Groceries', 'Medical']
    variable_categories = ['Travel', 'Transfers', 'Others']

    expense_segmentation = [{'data': [0 for _ in range(12)]} for _ in range(3)]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    for statement in statements:
        date = statement["date"]
        month = int(date.split("/")[1])
        category = statement["category"]
        withdrawal_amount = statement["withdrawal_amount"]
        if not withdrawal_amount:
            continue
        if category in fixed_categories:
            expense_segmentation[0]['data'][month-1] += float(withdrawal_amount.replace(",", ""))
        elif category in necessary_categories:
            expense_segmentation[1]['data'][month-1] += float(withdrawal_amount.replace(",", ""))
        elif category in variable_categories:
            expense_segmentation[2]['data'][month-1] += float(withdrawal_amount.replace(",", ""))

    # account_balance_over_time_y= [0 for _ in range(len(statements))]
    # account_balance_over_time_x = [0 for _ in range(len(statements))]
    # for statement in statements:
    #     date = statement["date"]
    #     month = int(date.split("/")[1])
    #     closing_balance = statement["closing_balance"]
    #     account_balance_over_time_y[month-1] = float(closing_balance.replace(",", ""))

    return jsonify({
        "expenditure_category_data": expenditure_category_data,
        "payment_methods_data": payment_methods_data,
        "expense_segmentation": expense_segmentation,
        # "account_balance_over_time": account_balance_over_time
    }), 200

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    query = data.get('query', '')
    response = answer_query(query)
    return jsonify({"response": response}), 200

if __name__ == '__main__':
    app.run(debug=True)
