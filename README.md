# 🌌 LDAP Manager Dashboard

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-black.svg?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![LDAP](https://img.shields.io/badge/LDAP-3-orange.svg?style=for-the-badge&logo=active-directory&logoColor=white)](https://ldap3.readthedocs.io/)

A premium, modern LDAP management dashboard built with **Python Flask** and **Glassmorphism UI**. Effortlessly manage your users, groups, and permissions with a sleek, responsive interface.

---

## ✨ Features

- **🚀 Modern UI/UX**: Stunning Glassmorphism design with dynamic animations and responsive layouts.
- **👤 User Management**: Full CRUD operations for LDAP users (posixAccount).
- **👥 Group Management**: Manage both `posixGroup` and `groupOfNames`.
- **🔐 Secure Authentication**: Integrated LDAP authentication with session-based access control.
- **🏢 Department Support**: Categorize users into departments dynamically via environment configuration.
- **🛠️ Member Management**: Easily add or remove members from groups with a clean interface.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, ldap3
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism), JavaScript (ES6+)
- **Environment**: Dotenv for secure configuration

---

## 🚀 Getting Started

### 1️⃣ Prerequisites

- Python 3.8+
- Access to an OpenLDAP server

### 2️⃣ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/ldap-manager.git
cd ldap-manager
pip install -r requirements.txt
```

### 3️⃣ Configuration

Create a `.env` file in the root directory and configure your LDAP settings:

```ini
LDAP_SERVER=ldap://your-ldap-server-ip

U_BASE_DN=ou=people,dc=example,dc=com
G_BASE_DN=ou=groups,dc=example,dc=com

ADMIN_DN=cn=admin,dc=example,dc=com
ADMIN_PASSWORD=your-secure-password
ADMINS_DN=cn=ldap-manager-admins,ou=groups,dc=example,dc=com

DEPARTMENTS=HR,IT,Finance,Sales

SRV_ADDRESS=0.0.0.0
SRV_PORT=8080
SSL=False

DEBUG=False
```
*ADMINS_DN is the group that contains users who have access to Admin Dashboard*

### 4️⃣ Run the Application

```bash
python ldap-manager.py
```
Access the dashboard at `http://localhost:8080`.

---

## 🔌 API Documentation

All API requests should include the session cookie after authentication.

### 🔑 Authentication

#### `POST /api/auth`
Authenticates a user and starts a session.

- **Body**:
  ```json
  {
    "username": "admin",
    "password": "password123"
  }
  ```
- **Success Response**: `200 OK`
  ```json
  { "code": 200, "message": "Logged in", "token": "..." }
  ```

---

### 👤 User Endpoints

#### `GET /api/user/list`
Fetches all LDAP users.
- **Success Response**: `200 OK`
  ```json
  { "code": 200, "message": "OK", "entries": [...] }
  ```

#### `POST /api/user/add`
Adds a new LDAP user.
- **Body**:
  ```json
  {
    "username": "jdoe",
    "kind": 0,
    "first_name": "John",
    "last_name": "Doe",
    "title": "Engineer",
    "department": "IT",
    "phone": "123456789",
    "mail": "jdoe@example.com"
  }
  ```

#### `POST /api/user/edit`
Updates an existing user.
- **Body**: Same as add, with optional `password` and `cn`.

#### `POST /api/user/delete`
Removes a user from LDAP.
- **Body**: `{ "username": "jdoe" }`

---

### 👥 Group Endpoints

#### `GET /api/group/list`
Fetches all groups (Posix and GroupOfNames).
- **Success Response**: `200 OK`
  ```json
  {
    "code": 200,
    "entries": { "posix_groups": [], "gon_groups": [] }
  }
  ```

#### `POST /api/group/create`
Creates a new group.
- **Body**:
  ```json
  {
    "name": "Developers",
    "kind": 0, 
    "description": "Technical team"
  }
  ```
  *(Kind: 0 for Posix, 1 for GroupOfNames)*

#### `POST /api/group/members/add`
Adds users to a group.
- **Body**:
  ```json
  {
    "name": "Developers",
    "members": ["jdoe", "asmith"]
  }
  ```

#### `POST /api/group/members/delete`
Removes users from a group.
- **Body**: Same as add member.

---

## 🎨 UI Preview

The dashboard features a **Glassmorphism** design:
- **Frosted glass** backgrounds for cards and modals.
- **Vibrant gradients** for buttons and highlights.
- **Smooth transitions** between tabs and operations.
- **Responsive layout** that works on desktop and tablets.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---
Built with ❤️ by dijey099.
