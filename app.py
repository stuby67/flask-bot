from flask import Flask, request, jsonify, render_template
import sqlite3
import google.generativeai as genai
import logging
import re

app = Flask(__name__)


genai.configure(api_key="")

logging.basicConfig(level=logging.DEBUG)

def get_gemini_response(question, prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content([prompt[0], question])
        return response.text
    except Exception as e:
        logging.error(f"Error generating response from Generative AI: {e}")
        return None

def read_sql_query(sql, db):
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        headers = [sanitize_header(description[0]) for description in cur.description]
        conn.close()
        return headers, rows
    except Exception as e:
        logging.error(f"Error executing SQL query: {e}")
        raise e

def sanitize_header(header):
    sanitized_header = re.sub(r'[^A-Za-z0-9_]', '', header)
    sanitized_header = re.sub(r'^[0-9]+', '', sanitized_header)
    if sanitized_header == '':
        sanitized_header = 'column'  # Placeholder name if header ends up empty
    return sanitized_header

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask_ajax', methods=['POST'])
def ask_ajax():
    try:
        data = request.get_json()
        question = data['question']
        prompt = ["""
            You are an expert in converting English questions to SQL query!
            The SQL database has the name COMPANY_SALES and has the following tables and columns:
            
            Tables:
            - cust: custid, custname, location
            - products: prodid, companyid, name, price
            - sales: salesid, custid, prodid, qty, price, date
            - company: companyid, name, sector
            
            Example 1: How many sales records are there?
            The SQL command will be something like this: SELECT COUNT(*) FROM sales;
            
            Example 2: Show all sales records for the product with ID 1?
            The SQL command will be something like this: SELECT * FROM sales WHERE prodid = 1;
            
            Example 3: List the salesid and qty for orders placed by the customer with ID 3?
            The SQL command will be something like this: SELECT salesid, qty FROM sales WHERE custid = 3;
            
            Example 4: What is the total quantity sold for the product with ID 5?
            The SQL command will be something like this: SELECT SUM(qty) as QTY_SOLD FROM sales WHERE prodid = 5;

            Strict instruction not to include formula in column name and rename the column using AS to generic suitable name.
            
            Also, the SQL code should not have '''
            in the beginning or end and should not contain the word SQL in the output.
        """]
        
        response = get_gemini_response(question, prompt)
        
        if response is None or "SELECT" not in response.upper():
            return jsonify({"Please rephrase the query."})
        
        try:
            headers, data = read_sql_query(response, "company_sales.db")
            return jsonify({"headers": headers, "data": data})
        except Exception as e:
            logging.error(f"Error reading SQL query results: {e}")
            return jsonify({"error": "Please rephrase the query."})
    except Exception as e:
        logging.error(f"Error in ask_ajax route: {e}")
        return jsonify({"Please rephrase the query. The bot could not understand the Query."})

if __name__ == '__main__':
    app.run(debug=True)


