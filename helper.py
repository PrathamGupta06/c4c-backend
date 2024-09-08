import tabula
import google.generativeai as genai
import re
import json
import requests
from firebase_admin import credentials, firestore
import firebase_admin
# dfs = tabula.read_pdf("hdfc_statement.pdf", pages='all')
API_KEY = "AIzaSyDfMvCnVyJaOxIIUhmGeX_TsHHAsWMfll4"
genai.configure(api_key=API_KEY) 
model = genai.GenerativeModel("gemini-1.5-flash")
cred = credentials.Certificate('./serviceAccountKey.json')  # Update this path
firebase_admin.initialize_app(cred)
db = firestore.client()

PROMPT = """
I will give you a bank statement in csv format. Extract the following details from the statements in the json format with following schema:

{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "Transaction date in the format dd/mm/yy."
      },
      "narration": {
        "type": "string",
        "description": "Description or details of the transaction."
      },
      "ref_number": {
        "type": "string",
        "description": "Cheque or reference number associated with the transaction."
      },
      "value_date": {
        "type": "string",
        "description": "Date when the transaction is processed/valued."
      },
      "withdrawal_amount": {
        "type": "string",
        "description": "Amount withdrawn, if applicable."
      },
      "deposit_amount": {
        "type": "string",
        "description": "Amount deposited, if applicable."
      },
      "closing_balance": {
        "type": "string",
        "description": "Closing balance after the transaction."
      },
      "payment_method": {
        "type": "string",
        "enum": ["UPI", "EMI", "NEFT", "Net Banking", "Credit Card", "Debit Card", "Others"],
        "description": "Payment method used for the transaction."
      },
      "transaction_type": {
        "type": "string",
        "enum": ["Deposited", "Credited"],
        "description": "Type of transaction, either deposited or credited."
      },
      "category": {
        "type": "string",
        "enum": ["Educational", "Transfers", "Groceries", "Medical", "Travel", "Bills and Recharges", "Others"],
        "description": "Category of the transaction."
      },
      "classification": {
        "type": "string",
        "enum": ["Fixed", "Necessary", "Variable"],
        "description": "Classification of the transaction based on whether it's a fixed, necessary, or variable expense."
      }
    },
    "required": ["date", "narration", "value_date", "closing_balance", "payment_method", "transaction_type", "category", "classification"]
  }
}
"""


def extract_statement_details(file_path):
    tabula.convert_into(file_path, "output.csv", output_format="csv", pages='all')
    with open("output.csv", "r") as f:
        bank_statements = f.readlines()[:25]
        bank_statements = "\n".join(bank_statements)
    PROMPT2 = f"""
    ---BANK STATEMENTS BEGINS---
    {bank_statements}
    ---BANK STATEMENTS ENDS---
    """
    PROMPT3 = PROMPT + PROMPT2
    print(PROMPT3)
    response = model.generate_content(PROMPT3)
    statement_details = response.text
    # with open("content.json", "r") as f:
    #     statement_details = f.read()
    pattern = r'json\s*(.*?)```'
    statement_details =  re.findall(pattern, statement_details, re.DOTALL)[0]
    with open("content.json", "w") as f:
        f.write(statement_details)
    return json.loads(statement_details)
EXTRACTION_PROMPT = """
Extract the any of the properties in the following json schema from the query:

{
    "properties": {
      "date": {
        "type": "string",
        "description": "Transaction date in the format dd/mm/yy."
      },
      "narration": {
        "type": "string",
        "description": "Description or details of the transaction."
      },
      "ref_number": {
        "type": "string",
        "description": "Cheque or reference number associated with the transaction."
      },
      "value_date": {
        "type": "string",
        "description": "Date when the transaction is processed/valued."
      },
      "withdrawal_amount": {
        "type": "string",
        "description": "Amount withdrawn, if applicable."
      },
      "deposit_amount": {
        "type": "string",
        "description": "Amount deposited, if applicable."
      },
      "closing_balance": {
        "type": "string",
        "description": "Closing balance after the transaction."
      },
      "payment_method": {
        "type": "string",
        "enum": ["UPI", "EMI", "NEFT", "Net Banking", "Credit Card", "Debit Card", "Others"],
        "description": "Payment method used for the transaction."
      },
      "transaction_type": {
        "type": "string",
        "enum": ["Deposited", "Credited"],
        "description": "Type of transaction, either deposited or credited."
      },
      "category": {
        "type": "string",
        "enum": ["Educational", "Transfers", "Groceries", "Medical", "Travel", "Bills and Recharges", "Others"],
        "description": "Category of the transaction."
      },
      "classification": {
        "type": "string",
        "enum": ["Fixed", "Necessary", "Variable"],
        "description": "Classification of the transaction based on whether it's a fixed, necessary, or variable expense."
      }
    }
}
Only provide with a json response of key : value pair where key is the property and value is the value of the property found in the query.
E.g. 
---QUERY---
What are my variable costs?
---RESPONSE---
{"classification": "Variable"}
---QUERY---
How much did I spend on Bills and Recharges?
---RESPONSE---
{"category": "Bills and Recharges"}
---QUERY---
How much amount did I withdraw on 28 feb 2024
---RESPONSE---
{"date": 28/02/24}
"""
def extract_json(content: str) -> str:
    pattern = r'json\s*(.*?)```'
    json_content =  re.findall(pattern, content, re.DOTALL)[0]
    return json_content

def extract_intent(query: str) -> str:
    PROMPT2 = f"""
--QUERY--
{query}
"""
    extracted_intents = extract_json(model.generate_content(EXTRACTION_PROMPT + PROMPT2).text)
    print(extracted_intents)
    return extracted_intents

def query_database(filter_str: str):
    try:
        transactions_ref = db.collection('statements')
        
        if filter_str and filter_str.strip():
            j_filter = json.loads(filter_str)
            
            if j_filter:  # Check if the parsed JSON is not empty
                query = transactions_ref
                for key, value in j_filter.items():
                    query = query.where(key, "==", value)
                
                results = query.get()
                return [doc.to_dict() for doc in results]
        # If filter_str is empty, None, or contains no keys, return first 20 documents
        results = transactions_ref.limit(20).get()
        return [doc.to_dict() for doc in results]
    except json.JSONDecodeError:
        print("Invalid JSON filter string")
        # Return first 20 documents if JSON is invalid
        results = transactions_ref.limit(20).get()
        return [doc.to_dict() for doc in results]
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []

def get_llm_response(query: str, queried_db: list):
    PROMPT3 = f"""
Use the following Json data to answer the query of the user. You are a finance assistant.

--DATA STARTS--
{str(queried_db)}
--DATA ENDS--
--QUERY--
{query}
"""
    response = model.generate_content(PROMPT3).text
    return response

def answer_query(query: str):
    filter = extract_intent(query)
    queried_db = query_database(filter)
    response = get_llm_response(query, queried_db)
    return response