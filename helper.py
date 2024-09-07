import tabula
import google.generativeai as genai
import re
import json
# dfs = tabula.read_pdf("hdfc_statement.pdf", pages='all')
API_KEY = "AIzaSyDfMvCnVyJaOxIIUhmGeX_TsHHAsWMfll4"
genai.configure(api_key=API_KEY) 
model = genai.GenerativeModel("gemini-1.5-flash")

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
        bank_statements = f.readlines()[:20]
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