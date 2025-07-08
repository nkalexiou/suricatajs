from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('./db/surikatajs.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/alerts', methods=['GET'])
def get_alerts():
    conn = get_db_connection()
    cursor = conn.cursor()

    alert_type = request.args.get('type')
    javascript = request.args.get('javascript')
    date = request.args.get('date')

    query = "SELECT * FROM alerts"
    conditions = []
    params = []

    if alert_type:
        conditions.append("alert_type=?")
        params.append(alert_type)
    if javascript:
        conditions.append("javascript=?")
        params.append(javascript)
    if date:
        conditions.append("date=?")
        params.append(date)

    # Only add WHERE if there are conditions
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    alerts = [dict(row) for row in rows]

    conn.close()
    return jsonify(alerts)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8085)
