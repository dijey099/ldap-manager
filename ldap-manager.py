import os
import json
import logging
import secrets
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE
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

SRV_ADDRESS = os.getenv('SRV_ADDRESS', "localhost")
SRV_PORT = os.getenv('SRV_PORT', 8080)
SRV_SSL = os.getenv('SSL', 'False')

LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://server.com')

U_BASE_DN = os.getenv('U_BASE_DN', 'ou=people,dc=server,dc=com')
G_BASE_DN = os.getenv('G_BASE_DN', 'ou=groups,dc=server,dc=com')

DEPARTMENTS = os.getenv('DEPARTMENTS', 'HR,HSE,IS')

ADMIN_DN = os.getenv('ADMIN_DN', 'cn=admin,dc=server,dc=come')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'v3rY5Ecre7')

ADMINS_DN = os.getenv('ADMINS_DN', 'dc=server,dc=com')

DEBUG_STATUS = os.getenv('DEBUG', 'False')
DEBUG = False
if DEBUG_STATUS == "True":
    DEBUG = True

DB_PATH = "logs.db"


def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user TEXT NOT NULL,
                ip TEXT NOT NULL,
                action TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")


def log_action(action_text):
    try:
        user = session.get('user', 'system')
        ip = request.remote_addr
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO logs (timestamp, user, ip, action) VALUES (?, ?, ?, ?)",
                  (timestamp, user, ip, action_text))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Failed to log action: {e}")



def get_user_dn(username):
    try:
        if username == "admin":
            return ADMIN_DN

        server = Server(LDAP_SERVER)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(U_BASE_DN, f"(uid={username})", attributes=['*'])
        
        if conn.entries:
            # print(conn.entries)
            return conn.entries[0].entry_dn
        else:
            return None
    except Exception as e:
        logging.error(e)
        return None


def authenticate(username, password):
    try:
        user_dn = get_user_dn(username)
        if not user_dn:
            logging.error(f"User {username} not found")
            return False

        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, user_dn, password, auto_bind=True)
        if username == "admin":
            logging.info(f"Authentication successful for {username}")
            conn.unbind()
            return True
        else:
            g_dn = ADMINS_DN.split(',')
            g_name = g_dn[0].replace("cn=", "")
            g_search_base = ",".join(g_dn[1:])
            search_filter = f'(&(objectClass=posixGroup)(cn={g_name}))'
            conn.search(search_base=g_search_base,
                        search_filter=search_filter,
                        attributes=['memberUid'])
            if conn.entries:
                group_entry = conn.entries[0]
                members = group_entry.memberUid.values
                if username in members:
                    logging.info(f"Authentication successful for {username}")
                    conn.unbind()
                    return True
                else:
                    logging.warning(f"Authentication failed for {username} - Not member of {g_name}")
                    conn.unbind()
                    return False
            else:
                logging.error(f"Group {g_name} not found.")
                conn.unbind()
                return False

    except Exception as e:
        logging.warning(f"Authentication failed for {username} - {e}")
        conn.unbind()
        return False


def get_users():
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=U_BASE_DN,
            search_filter='(objectClass=posixAccount)',
            attributes=[
                'uid',
                'cn',
                'givenName',
                'sn',
                'title',
                'departmentNumber',
                'gidNumber',
                'uidNumber',
                'mail',
                'mobile',
                'objectClass'
            ]
        )
        users = conn.response_to_json()
        conn.unbind()
        return json.loads(users)

    except Exception as e:
        logging.error(f"Failed to get users - {e}")
        conn.unbind()
        return None
        

def add_user(uid, kind, givenName, sn, title, departmentNumber, mobile, mail):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=U_BASE_DN,
            search_filter="(objectClass=posixAccount)",
            attributes=["uidNumber"]
        )

        uid_numbers = []

        for entry in conn.entries:
            if "uidNumber" in entry:
                try:
                    uid_numbers.append(int(entry.uidNumber.value))
                except (ValueError, TypeError):
                    pass

        if uid_numbers:
            next_uid = max(uid_numbers) + 1
        else:
            next_uid = 1000

        add_u_ok = conn.add(
            f"uid={uid},{U_BASE_DN}",
            attributes={
                "cn": uid.strip(), 
                "givenName": givenName.strip(), 
                "sn": sn.strip(), 
                "title": title.strip(), 
                "departmentNumber": departmentNumber.strip(), 
                "gidNumber": 27, 
                "uidNumber": next_uid, 
                "mail": mail.strip(), 
                "mobile": mobile.strip(), 
                "objectClass": [
                    "inetOrgPerson",
                    "posixAccount",
                    "shadowAccount"
                ],
                "userPassword": "{SSHA}T6nQZ5iN2SZqObXuDGp7n1Gzhdkx5tay",
                "loginShell": "/bin/bash" if kind == 0 else "/usr/local/bin/bastion",
                "homeDirectory": f"/home/{uid.strip()}"
            }
        )

        add_g_ok = conn.add(
            f"cn={uid},{G_BASE_DN}",
            attributes={
                "cn": uid, 
                "objectClass": ["posixGroup"],
                "gidNumber": next_uid
            }
        )

        if add_u_ok and add_g_ok:
            logging.info(f"User {uid} added successfully")
            conn.unbind()
            return True
        else:
            logging.error(f"Failed to add new user {uid} - {conn.result}")
            conn.unbind()
            return False

    except Exception as e:
        logging.error(f"Failed to add user {uid} - {e}")
        conn.unbind()
        return False


def delete_user(uid):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        u_ok = conn.delete(f"uid={uid.strip()},{U_BASE_DN}")
        g_ok = conn.delete(f"cn={uid.strip()},{G_BASE_DN}")

        if u_ok and g_ok:
            logging.info(f"User {uid} deleted successfully")
            conn.unbind()
            return True
        else:
            logging.error(f"Failed to delete user {uid} - {conn.result}")
            conn.unbind()
            return False

    except Exception as e:
        logging.error(f"Failed to delete user {uid} - {e}")
        return False


def edit_user(uid, cn=None, kind=None, givenName=None, sn=None, title=None, departmentNumber=None, mobile=None, mail=None, password=None):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        changes = {}

        if cn:
            changes["cn"] = [(MODIFY_REPLACE, [cn.strip()])]
        if kind:
            if kind == 0:
                changes["loginShell"] = [(MODIFY_REPLACE, ["/bin/bash"])]
            elif kind == 1:
                changes["loginShell"] = "/usr/local/bin/bastion"
        if givenName:
            changes["givenName"] = [(MODIFY_REPLACE, [givenName.strip()])]
        if sn:
            changes["sn"] = [(MODIFY_REPLACE, [sn.strip()])]
        if title:
            changes["title"] = [(MODIFY_REPLACE, [title.strip()])]
        if departmentNumber:
            changes["departmentNumber"] = [(MODIFY_REPLACE, [departmentNumber.strip()])]
        if mobile:
            changes["mobile"] = [(MODIFY_REPLACE, [mobile.strip()])]
        if mail:
            changes["mail"] = [(MODIFY_REPLACE, [mail.strip()])]
        if password:
            changes["userPassword"] = [(MODIFY_REPLACE, [password.strip()])]

        if changes:
            ok = conn.modify(
                f"uid={uid},{U_BASE_DN}",
                changes
            )

            if ok:
                logging.info(f"User {uid} edited successfully")
                conn.unbind()
                return True
            else:
                logging.error(f"Failed to edit user {uid} - {conn.result}")
                conn.unbind()
                return False
        else:
            logging.info(f"No change made for user {uid}")
            conn.unbind()
            return False

    except Exception as e:
        logging.error(f"Failed to edit user {uid} - {e}")
        conn.unbind()
        return False


def get_groups():
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=G_BASE_DN,
            search_filter='(objectClass=posixGroup)',
            attributes=[
                'cn',
                'gidNumber',
                'description',
                'memberUid'
            ]
        )
        posix_groups = conn.response_to_json()

        conn.search(
            search_base=G_BASE_DN,
            search_filter='(objectClass=groupOfNames)',
            attributes=[
                'cn',
                'description',
                'member'
            ]
        )
        gon_groups = conn.response_to_json()

        conn.unbind()
        return json.loads(posix_groups), json.loads(gon_groups)

    except Exception as e:
        logging.error(f"Failed to get groups - {e}")
        conn.unbind()
        return None


def create_group(name, kind, description):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=G_BASE_DN,
            search_filter="(objectClass=posixGroup)",
            attributes=["gidNumber"]
        )

        gid_numbers = []
        for entry in conn.entries:
            if "gidNumber" in entry:
                try:
                    gid_numbers.append(int(entry.gidNumber.value))
                except (ValueError, TypeError):
                    pass

        if gid_numbers:
            next_gid = max(gid_numbers) + 1
        else:
            next_gid = 10000

        att = {}
        if kind == 0 or kind == "0":
            att = {
                "cn": name.strip(), 
                "objectClass": ["posixGroup"],
                "description": description.strip(),
                "gidNumber": next_gid
            }
        elif kind == 1 or kind == "1":
            att = {
                "cn": name.strip(), 
                "objectClass": ["groupOfNames"],
                "description": description.strip(),
                "member": ADMIN_DN
            }

        ok = conn.add(
            f"cn={name.strip()},{G_BASE_DN}",
            attributes=att
        )

        if ok:
            logging.info(f"Group {name} added successfully")
            return True
        else:
            logging.error(f"Failed to create group {name} - {conn.result}")
            return False

    except Exception as e:
        logging.error(f"Failed to create group {name} - {e}")
        return False

    finally:
        conn.unbind()


def delete_group(name):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        status = conn.delete(f"cn={name.strip()},{G_BASE_DN}")

        if status:
            logging.info(f"Group {name} deleted successfully")
            return True
        else:
            logging.error(f"Failed to delete group {name} - {status['description']}")
            return False

    except Exception as e:
        logging.error(f"Failed to delete group {name} - {e}")
        return False

    finally:
        conn.unbind()


def edit_group(name, new_name=None, new_description=None):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        changes = {}
        
        if new_name:
            changes["cn"] = [(MODIFY_REPLACE, [new_name.strip()])]
        if new_description:
            changes["description"] = [(MODIFY_REPLACE, [new_description.strip()])]

        if changes:
            ok = conn.modify(
                f"cn={name.strip()},{G_BASE_DN}",
                changes
            )

            if ok:
                logging.info(f"Group {name} edited successfully")
                conn.unbind()
                return True
            else:
                logging.error(f"Failed to edit group {name} - {conn.result}")
                conn.unbind()
                return False
        else:
            logging.info(f"No change made for group {name}")
            return True

    except Exception as e:
        logging.error(f"Failed to edit group {name} - {e}")
        return False


def add_members(group_name, members):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=G_BASE_DN,
            search_filter=f"(cn={group_name})",
            attributes=["objectClass"]
        )

        kind = ""
        for entry in conn.entries:
            kind = entry.objectClass.value
        
        changes = {}
        if kind == "posixGroup":
            changes = {
                "memberUid": [(MODIFY_ADD, members)]
            }
        elif kind == "groupOfNames":
            changes = {
                "member": [(MODIFY_ADD, [f"uid={uid},{U_BASE_DN}" for uid in members])]
            }

        ok = conn.modify(
            f"cn={group_name.strip()},{G_BASE_DN}",
            changes
        )

        if ok:
            logging.info(f"New members added to {group_name} successfully")
            conn.unbind()
            return True
        else:
            logging.error(f"Failed to add new members to {group_name} - {conn.result}")
            conn.unbind()
            return False

    except Exception as e:
        logging.error(f"Failed to add new members to {group_name} - {e}")
        return False


def delete_members(group_name, members):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, ADMIN_DN, ADMIN_PASSWORD, auto_bind=True)

        conn.search(
            search_base=G_BASE_DN,
            search_filter=f"(cn={group_name})",
            attributes=["objectClass"]
        )

        kind = ""
        for entry in conn.entries:
            kind = entry.objectClass.value
        
        changes = {}
        if kind == "posixGroup":
            changes = {
                "memberUid": [(MODIFY_DELETE, members)]
            }
        elif kind == "groupOfNames":
            changes = {
                "member": [(MODIFY_DELETE, [f"uid={uid},{U_BASE_DN}" for uid in members])]
            }

        ok = conn.modify(
            f"cn={group_name.strip()},{G_BASE_DN}",
            changes
        )

        if ok:
            logging.info(f"New members added to {group_name} successfully")
            conn.unbind()
            return True
        else:
            logging.error(f"Failed to add new members to {group_name} - {conn.result}")
            conn.unbind()
            return False

    except Exception as e:
        logging.error(f"Failed to add new members to {group_name} - {e}")
        return False


@app.route('/', methods=['GET'])
def root():
    return redirect(url_for("admin"))


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')


@app.route('/admin', methods=['GET'])
def admin():
    if 'user' not in session:
        return redirect(url_for("login"))

    departments = DEPARTMENTS.split(',')
    return render_template("admin.html", departments=departments, username=session['user'])


@app.route('/api/auth', methods=['POST'])
def auth():
    rdata = request.get_json()
    username = rdata.get('username')
    password = rdata.get('password')

    if username and password:
        if authenticate(username, password):
            session['user'] = username
            log_action(f"User logged in successfully")
            return make_response(
                {
                    "code": 200,
                    "message": "Logged in",
                    "token": "LOL"
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


@app.route('/api/user/list', methods=['GET'])
def get_u():
    if 'user' not in session:
        return redirect(url_for("login"))

    users = get_users()
    return make_response(
        {
            "code": 200,
            "message": "OK",
            "entries": users["entries"]
        },
        200
    )


@app.route('/api/user/add', methods=['POST'])
def add_u():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    uid = rdata.get('username')
    kind = rdata.get('kind')    # Admin bastion(0) or server(1)
    givenName = rdata.get('first_name')
    sn = rdata.get('last_name')
    title = rdata.get('title')
    departmentNumber = rdata.get('department')
    mobile = rdata.get('phone')
    mail = rdata.get('mail')

    if all([uid, kind, givenName, sn, title, departmentNumber, mobile, mail]):
        success = add_user(uid, kind, givenName, sn, title, departmentNumber, mobile, mail)

        if success:
            log_action(f"Added new user: {uid}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/user/delete', methods=['POST'])
def delete_u():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    uid = rdata.get('username')

    if uid:
        success = delete_user(uid)

        if success:
            log_action(f"Deleted user: {uid}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/user/edit', methods=['POST'])
def edit_u():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    uid = rdata.get('username')
    cn = rdata.get('cn')
    kind = rdata.get('kind')    # Admin bastion(0) or server(1)
    givenName = rdata.get('first_name')
    sn = rdata.get('last_name')
    title = rdata.get('title')
    departmentNumber = rdata.get('department')
    mobile = rdata.get('phone')
    mail = rdata.get('mail')
    password = rdata.get('password')

    if uid:
        success = edit_user(uid, cn, kind, givenName, sn, title, departmentNumber, mobile, mail, password)

        if success:
            log_action(f"Edited user: {uid}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/group/list', methods=['GET'])
def get_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    posix_groups, gon_groups = get_groups()
    return make_response(
        {
            "code": 200,
            "message": "OK",
            "entries": {
                "posix_groups": posix_groups["entries"],
                "gon_groups": gon_groups["entries"]
            }
        },
        200
    )


@app.route('/api/group/create', methods=['POST'])
def create_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    name = rdata.get('name')
    kind = rdata.get('kind')    # Admin default(0) or windows(1)
    description = rdata.get('description')

    if name and str(kind) and description:
        success = create_group(name, kind, description)

        if success:
            log_action(f"Created new group: {name}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/group/delete', methods=['POST'])
def delete_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    name = rdata.get('name')

    if name:
        success = delete_group(name)

        if success:
            log_action(f"Deleted group: {name}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/group/edit', methods=['POST'])
def edit_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    name = rdata.get('name')
    new_name = rdata.get('new_name')
    new_description = rdata.get('new_description')

    if name:
        success = edit_group(name, new_name, new_description)

        if success:
            log_action(f"Edited group: {name}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/group/members/add', methods=['POST'])
def add_member_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    group_name = rdata.get('name')
    new_members = rdata.get('members')

    if group_name and new_members:
        success = add_members(group_name, new_members)

        if success:
            log_action(f"Added members {', '.join(new_members)} to group: {group_name}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/group/members/delete', methods=['POST'])
def delete_member_g():
    if 'user' not in session:
        return redirect(url_for("login"))

    rdata = request.get_json()

    name = rdata.get('name')
    members = rdata.get('members')

    if name:
        success = delete_members(name, members)

        if success:
            log_action(f"Removed members {', '.join(members)} from group: {name}")
            return make_response(
                {
                    "code": 200,
                    "message": "OK"
                },
                200
            )

    return make_response(
        {
            "code": 400,
            "message": "Bad request"
        },
        400
    )


@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return redirect(url_for("login"))


@app.route('/api/logs/list', methods=['GET'])
def get_logs():
    if 'user' not in session:
        return redirect(url_for("login"))

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
        rows = c.fetchall()
        logs = [dict(row) for row in rows]
        conn.close()
        
        return make_response(
            {
                "code": 200,
                "message": "OK",
                "entries": logs
            },
            200
        )
    except Exception as e:
        logging.error(f"Failed to fetch logs: {e}")
        return make_response(
            {
                "code": 500,
                "message": "Internal server error"
            },
            500
        )


if __name__ == '__main__':
    init_db()
    if SRV_SSL == "True":
        public_key = "ssl/public.crt"
        private_key = "ssl/private.key"
        if os.path.exists(public_key) and os.path.exists(private_key):
            context = (public_key, private_key)
            app.run(debug=DEBUG, host=SRV_ADDRESS, port=SRV_PORT, ssl_context=context)
        else:
            logging.error("Missing public.crt or private.key in ./ssl directory. Run \"cd ssl && ./certgen --host <YOUR_SERVER_FQDN_OR_IP>\"")
    else:
        app.run(debug=DEBUG, host=SRV_ADDRESS, port=SRV_PORT)