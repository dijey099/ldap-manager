import os
import logging
import secrets
from threading import Thread
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, NTLM
from flask import Flask, request, make_response, session, render_template, redirect, url_for


load_dotenv(dotenv_path=".env")

logging.basicConfig(
    filename='ldap-manager.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__, template_folder='web', static_folder='static')
app.debug = True
app.secret_key = secrets.token_hex(16)

PORT= os.getenv('PORT', 4444)

LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://server.com')

BASE_DN = os.getenv('BASE_DN', 'ou=people,dc=server,dc=com')

ADMIN_DN = os.getenv('ADMIN_DN', 'cn=admin,dc=server,dc=come')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'v3rY5Ecre7')



def authenticate(username, password):
    try:
        user_dn = get_user_dn(username)
        if not user_dn:
            logging.error(f"User {username} not found")
            return False

        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user_dn, password, auto_bind=True)
        logging.info(f"Authentication successful for {username}")
        conn.unbind()

        return True

    except Exception as e:
        logging.warning(f"Authentication failed for {username} - {e}")
        return False


def get_user_dn(username):
    try:
        if username == "admin":
            return ADMIN_DN

        server = Server(LDAP_SERVER)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(BASE_DN, f"(uid={username})", attributes=['*'])
        
        if conn.entries:
            print(conn.entries)
            return conn.entries[0].entry_dn
        else:
            return None
    except Exception as e:
        logging.error(e)
        return None


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/auth', methods=['POST'])
def auth():
    rdata = request.get_json()
    if rdata and rdata.get('username') and rdata.get('password'):
        username = rdata.get('username')
        password = rdata.get('password')

        if username != "admin":
            return make_response(
                {
                    "code": 401,
                    "message": "Invalid credentials"
                },
                401
            )

    if authenticate(username, password):
        session['user'] = username
        return make_response(
            {
                "code": 200,
                "message": "Logged in",
                "token": "lol"
            },
            200
        )
    else:
        return make_response(
            {
                "code": 401,
                "message": "Invalid credentials"
            },
            401
        )


@app.route('/admin', methods=['GET'])
def admin():
    if 'user' not in session:
        return redirect(url_for("login"))

    return render_template("admin.html")


@app.route('/add/user', methods=['POST'])
def add_user():
    if 'user' not in session:
        return redirect(url_for("login"))
    return make_response(
        {
            "code": 200,
            "message": "New user added",
        },
        200
    )


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for("login"))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=PORT)