from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire application

# Database connection details
db_config = {
    'dbname': 'autointelli',
    'user': 'autointelli',
    'password': 'Wigtra@autointelli',
    'host': 'localhost',
    'port': 5432
}

TARGET_DIR = "/etc/telegraf/telegraf.d"

# Database connection function
def get_db_connection():
    try:
        conn = psycopg2.connect(**db_config)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

@app.route('/icmp', methods=['POST'])
def add_icmp_record():
    """Insert a new record into the ICMP table and create config files."""
    try:
        data = request.get_json()
        ip = data.get('ip')
        serial_no = data.get('serial_no')
        sysname = data.get('sysname')
        category = data.get('category')
        location = data.get('location')
        type = "icmp"

        if not ip or not serial_no or not sysname or not category or not location:
            return jsonify({"error": "Missing required fields"}), 400

        config_file_path = os.path.join(TARGET_DIR, f"{ip}.conf")

        if os.path.exists(config_file_path):
            return jsonify({
                "error": f"Configuration file for IP {ip} already exists. Duplicate files are not allowed."
            }), 409

        os.makedirs(TARGET_DIR, exist_ok=True)

        config_content = f"""[[inputs.ping]]
  urls = ["{ip}"]
  interval = "60s"
  count = 3
  ping_interval = 1.0
  timeout = 1.0
  deadline = 10
  [inputs.ping.tags]
    serialnumber="{serial_no}"
    sysname="{sysname}"
    category="{category}"
"""

        try:
            with open(config_file_path, "w") as config_file:
                config_file.write(config_content)
        except Exception as e:
            return jsonify({"error": "Failed to create configuration file"}), 500

        created_at = datetime.utcnow()
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        try:
            with conn.cursor() as cursor:
                query = """
                INSERT INTO autointelli_task (ip, type, serial_no, sysname, category, location, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                cursor.execute(query, (ip, type, serial_no, sysname, category, location, created_at))
                conn.commit()
        except Exception as e:
            conn.rollback()
            return jsonify({"error": "Failed to insert data into the database"}), 500
        finally:
            conn.close()

        return jsonify({"message": "Record added successfully"}), 201

    except Exception as e:
        return jsonify({"error": "Failed to handle the request"}), 500


@app.route('/icmp/delete', methods=['DELETE'])
def delete_icmp_record_by_id():
    """Delete a record from the ICMP table based on its 'id'."""
    try:
        data = request.get_json()  # Parse JSON from the request body
        record_id = data.get('id')

        # Check if the id is provided in the request
        if not record_id:
            return jsonify({"error": "Missing 'id' in request body"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Fetch the record to get the IP address using the id
                cursor.execute("SELECT ip FROM autointelli_task WHERE id = %s;", (record_id,))
                record = cursor.fetchone()

                if not record:
                    return jsonify({"error": f"No record found with id {record_id}"}), 404

                ip = record['ip']
                config_file_path = os.path.join(TARGET_DIR, f"{ip}.conf")

                # Delete the record from the database
                cursor.execute("DELETE FROM autointelli_task WHERE id = %s;", (record_id,))
                conn.commit()

                # Remove the associated configuration file if it exists
                if os.path.exists(config_file_path):
                    os.remove(config_file_path)

        except Exception as e:
            conn.rollback()
            return jsonify({"error": "Failed to delete record from the database"}), 500
        finally:
            conn.close()

        return jsonify({"message": f"Record with id {record_id} deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to handle the DELETE request"}), 500


@app.route('/icmp/delete/serial', methods=['DELETE'])
def delete_icmp_record_by_serial():
    """Delete a record from the ICMP table based on its 'serial_no'."""
    try:
        data = request.get_json()  # Parse JSON from the request body
        serial_no = data.get('serial_no')

        # Check if the serial_no is provided in the request
        if not serial_no:
            return jsonify({"error": "Missing 'serial_no' in request body"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Fetch the record to get the IP address using the serial_no
                cursor.execute("SELECT ip FROM autointelli_task WHERE serial_no = %s;", (serial_no,))
                record = cursor.fetchone()

                if not record:
                    return jsonify({"error": f"No record found with serial_no {serial_no}"}), 404

                ip = record['ip']
                config_file_path = os.path.join(TARGET_DIR, f"{ip}.conf")

                # Delete the record from the database
                cursor.execute("DELETE FROM autointelli_task WHERE serial_no = %s;", (serial_no,))
                conn.commit()

                # Remove the associated configuration file if it exists
                if os.path.exists(config_file_path):
                    os.remove(config_file_path)

        except Exception as e:
            conn.rollback()
            return jsonify({"error": "Failed to delete record from the database"}), 500
        finally:
            conn.close()

        return jsonify({"message": f"Record with serial_no {serial_no} deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "Failed to handle the DELETE request for serial_no"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
