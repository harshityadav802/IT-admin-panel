from flask import Flask, render_template

app = Flask(__name__)

@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/groups')
def groups():
    return render_template('groups.html')

@app.route('/audit-log')
def audit_log():
    return render_template('audit_log.html')

if __name__ == '__main__':
    app.run(debug=True)