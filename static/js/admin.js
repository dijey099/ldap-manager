document.addEventListener("DOMContentLoaded", function () {
    // --- State Management ---
    let users = [];
    let groups = { posix_groups: [], gon_groups: [] };
    let currentView = 'dashboard';
    let editingUser = null;
    let editingGroup = null;
    let originalUserData = null;

    // --- Utilities ---
    function getVal(attr) {
        if (Array.isArray(attr)) return attr.length > 0 ? attr[0] : '';
        return attr || '';
    }

    function showToast(message, type = "success") {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.style.background = type === "error" ? "#e03131" : "#A01863";
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // --- Selectors ---
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    const pageTitle = document.getElementById('page-title');
    const logoutBtn = document.getElementById('logout-btn');
    
    // User Modals & Forms
    const userModal = document.getElementById('user-modal');
    const userForm = document.getElementById('user-form');
    const addUserBtn = document.getElementById('add-user-btn');
    const userModalTitle = document.getElementById('user-modal-title');
    
    // Group Modals & Forms
    const groupModal = document.getElementById('group-modal');
    const groupForm = document.getElementById('group-form');
    const addGroupBtn = document.getElementById('add-group-btn');
    const groupModalTitle = document.getElementById('group-modal-title');

    // Close buttons
    const closeBtns = document.querySelectorAll('.close, .close-modal');

    // --- Initialization ---
    init();

    async function init() {
        setupEventListeners();
        await fetchData();
        renderDashboard();
    }

    // --- API Calls ---
    async function fetchData() {
        try {
            const [uRes, gRes] = await Promise.all([
                fetch('/api/user/list'),
                fetch('/api/group/list')
            ]);

            if (uRes.ok) {
                const uData = await uRes.json();
                users = uData.entries || [];
            }

            if (gRes.ok) {
                const gData = await gRes.json();
                groups = gData.entries || { posix_groups: [], gon_groups: [] };
            }
        } catch (error) {
            console.error("Error fetching data:", error);
            showToast("Failed to fetch data from server", "error");
        }
    }

    // --- Navigation ---
    function switchView(viewName) {
        currentView = viewName;
        
        // Update Sidebar
        navItems.forEach(item => {
            if (item.getAttribute('data-view') === viewName) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Show/Hide Views
        views.forEach(view => {
            if (view.id === `${viewName}-view`) {
                view.style.display = 'block';
            } else {
                view.style.display = 'none';
            }
        });

        // Update Title & Render
        const titles = {
            'dashboard': 'Dashboard',
            'users': 'User Management',
            'groups': 'Group Management'
        };
        pageTitle.textContent = titles[viewName];

        if (viewName === 'dashboard') renderDashboard();
        if (viewName === 'users') renderUsers();
        if (viewName === 'groups') renderGroups();
    }

    // --- Rendering Logic ---
    function renderDashboard() {
        document.getElementById('total-users').textContent = users.length;
        document.getElementById('total-groups').textContent = groups.posix_groups.length + groups.gon_groups.length;
        document.getElementById('posix-groups-count').textContent = groups.posix_groups.length;
        document.getElementById('gon-groups-count').textContent = groups.gon_groups.length;

        // Last 5 Users
        const recentUsers = users.slice(-5).reverse();
        const userList = document.getElementById('recent-users-list');
        userList.innerHTML = recentUsers.map(u => `
            <tr>
                <td>${getVal(u.attributes.uid)}</td>
                <td>${getVal(u.attributes.givenName)} ${getVal(u.attributes.sn)}</td>
                <td>${getVal(u.attributes.mail)}</td>
            </tr>
        `).join('');

        // Last 5 Groups
        const taggedPosix = groups.posix_groups.map(g => ({...g, type: 'POSIX'}));
        const taggedGon = groups.gon_groups.map(g => ({...g, type: 'Generic'}));
        const allGroups = [...taggedPosix, ...taggedGon].slice(-5).reverse();
        
        const groupList = document.getElementById('recent-groups-list');
        groupList.innerHTML = allGroups.map(g => {
            if (!g.attributes) return '';
            const cn = getVal(g.attributes.cn);
            const desc = getVal(g.attributes.description);
            const isPosix = g.type === 'POSIX';
            return `
                <tr>
                    <td>${cn}</td>
                    <td><span class="badge ${isPosix ? 'posix' : 'gon'}">${g.type}</span></td>
                    <td>${desc}</td>
                </tr>
            `;
        }).join('');
    }

    function renderUsers(filter = '') {
        const tableBody = document.getElementById('users-table-body');
        const filteredUsers = users.filter(u => {
            if (!u.attributes) return false;
            const uid = getVal(u.attributes.uid).toLowerCase();
            const cn = getVal(u.attributes.cn).toLowerCase();
            const mail = getVal(u.attributes.mail).toLowerCase();
            const f = filter.toLowerCase();
            return uid.includes(f) || cn.includes(f) || mail.includes(f);
        });

        tableBody.innerHTML = filteredUsers.map(u => {
            if (!u.attributes) return '';
            const uid = getVal(u.attributes.uid);
            const gn = getVal(u.attributes.givenName);
            const sn = getVal(u.attributes.sn);
            const mail = getVal(u.attributes.mail);
            const phone = getVal(u.attributes.mobile);
            const dept = getVal(u.attributes.departmentNumber);

            return `
                <tr class="clickable" onclick="editUser('${uid}')">
                    <td><strong>${uid}</strong></td>
                    <td>${gn} ${sn}</td>
                    <td>${mail}</td>
                    <td>${phone}</td>
                    <td>${dept}</td>
                    <td class="actions-cell">
                        <button class="btn btn-icon btn-danger" onclick="event.stopPropagation(); deleteUser('${uid}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function renderGroups(filter = '') {
        const tableBody = document.getElementById('groups-table-body');
        const allGroups = [
            ...groups.posix_groups.map(g => ({...g, type: 'POSIX'})),
            ...groups.gon_groups.map(g => ({...g, type: 'Generic'}))
        ];

        const filteredGroups = allGroups.filter(g => {
            if (!g.attributes) return false;
            const cn = getVal(g.attributes.cn).toLowerCase();
            const desc = getVal(g.attributes.description).toLowerCase();
            const f = filter.toLowerCase();
            return cn.includes(f) || desc.includes(f);
        });

        tableBody.innerHTML = filteredGroups.map(g => {
            if (!g.attributes) return '';
            const cn = getVal(g.attributes.cn);
            const desc = getVal(g.attributes.description);
            const gid = getVal(g.attributes.gidNumber);
            
            // Extract members
            let members = [];
            if (g.type === 'POSIX') {
                members = g.attributes.memberUid || [];
            } else {
                const dns = g.attributes.member || [];
                members = dns.map(dn => {
                    const match = dn.match(/uid=([^,]+)/);
                    return match ? match[1] : dn;
                });
            }
            if (!Array.isArray(members)) members = [members];
            
            const displayMembers = members.length > 5 
                ? members.slice(0, 5).join(', ') + '...' 
                : (members.join(', ') || '-');

            return `
                <tr class="clickable" onclick="editGroup('${cn}', '${g.type}')">
                    <td><strong>${cn}</strong></td>
                    <td><span class="badge ${g.type === 'POSIX' ? 'posix' : 'gon'}">${g.type}</span></td>
                    <td>${gid || '-'}</td>
                    <td>${desc}</td>
                    <td><small>${displayMembers}</small></td>
                    <td class="actions-cell">
                        <button class="btn btn-icon btn-danger" onclick="event.stopPropagation(); deleteGroup('${cn}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // --- Event Listeners ---
    function setupEventListeners() {
        // Navigation
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                switchView(item.getAttribute('data-view'));
            });
        });

        // Logout
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/logout', { method: 'POST' });
                window.location.href = '/login';
            } catch (error) {
                window.location.href = '/login';
            }
        });

        // Modals
        addUserBtn.addEventListener('click', () => {
            editingUser = null;
            userModalTitle.textContent = "Add New User";
            userForm.reset();
            document.getElementById('m-username').disabled = false;
            document.getElementById('kind-container').style.display = 'block';
            document.getElementById('password-container').style.display = 'none';
            document.getElementById('m-password').required = false;
            userModal.style.display = 'block';
        });

        addGroupBtn.addEventListener('click', () => {
            editingGroup = null;
            groupModalTitle.textContent = "Create New Group";
            groupForm.reset();
            document.getElementById('g-name').disabled = false;
            document.getElementById('g-edit-name-container').style.display = 'none';
            document.getElementById('g-kind-container').style.display = 'block';
            document.getElementById('g-members-section').style.display = 'none';
            groupModal.style.display = 'block';
        });

        document.getElementById('g-add-member-btn').addEventListener('click', async () => {
            const select = document.getElementById('g-add-member-select');
            const username = select.value;
            if (!username || !editingGroup) return;

            try {
                const response = await fetch('/api/group/members/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: editingGroup.name, members: [username] })
                });

                if (response.ok) {
                    showToast("Member added", "success");
                    await fetchData();
                    editGroup(editingGroup.name, editingGroup.type); // Refresh modal
                    renderGroups();
                } else {
                    showToast("Failed to add member", "error");
                }
            } catch (error) {
                showToast("Server error", "error");
            }
        });

        closeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                userModal.style.display = 'none';
                groupModal.style.display = 'none';
            });
        });

        window.onclick = (event) => {
            if (event.target == userModal) userModal.style.display = 'none';
            if (event.target == groupModal) groupModal.style.display = 'none';
        };

        // Forms
        userForm.addEventListener('submit', handleUserSubmit);
        groupForm.addEventListener('submit', handleGroupSubmit);

        // Search
        document.getElementById('user-search').addEventListener('input', (e) => renderUsers(e.target.value));
        document.getElementById('group-search').addEventListener('input', (e) => renderGroups(e.target.value));
    }

    // --- Handlers ---
    async function handleUserSubmit(e) {
        e.preventDefault();
        const formData = new FormData(userForm);
        const rawData = Object.fromEntries(formData.entries());
        
        let payload = {};
        const endpoint = editingUser ? '/api/user/edit' : '/api/user/add';
        
        if (editingUser) {
            // Edit: only send changed fields + username
            payload.username = editingUser;
            
            const fieldMap = {
                'first_name': 'givenName',
                'last_name': 'sn',
                'mail': 'mail',
                'phone': 'mobile',
                'title': 'title',
                'department': 'departmentNumber'
            };

            for (const [formKey, ldapKey] of Object.entries(fieldMap)) {
                const newVal = rawData[formKey];
                const oldVal = getVal(originalUserData.attributes[ldapKey]);
                if (newVal !== oldVal) {
                    payload[formKey] = newVal;
                }
            }
            
            // Password special case
            if (rawData.password) {
                payload.password = rawData.password;
            }
        } else {
            // Add: send all fields
            payload = rawData;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                showToast(editingUser ? "User updated successfully" : "User added successfully", "success");
                userModal.style.display = 'none';
                await fetchData();
                renderUsers();
                if (currentView === 'dashboard') renderDashboard();
            } else {
                const res = await response.json();
                showToast(res.message || "Operation failed", "error");
            }
        } catch (error) {
            showToast("Server error", "error");
        }
    }

    async function handleGroupSubmit(e) {
        e.preventDefault();
        const formData = new FormData(groupForm);
        const data = Object.fromEntries(formData.entries());
        
        let endpoint = '/api/group/create';
        let payload = data;

        if (editingGroup) {
            endpoint = '/api/group/edit';
            payload = {
                name: editingGroup.name,
                new_name: data.new_name !== editingGroup.name ? data.new_name : null,
                new_description: data.description !== editingGroup.description ? data.description : null
            };
        }
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                showToast(editingGroup ? "Group updated successfully" : "Group created successfully", "success");
                groupModal.style.display = 'none';
                await fetchData();
                renderGroups();
                if (currentView === 'dashboard') renderDashboard();
            } else {
                const res = await response.json();
                showToast(res.message || "Operation failed", "error");
            }
        } catch (error) {
            showToast("Server error", "error");
        }
    }

    // --- Global functions (attached to window for HTML onclick) ---
    window.editUser = function(uid) {
        const user = users.find(u => getVal(u.attributes.uid) === uid);
        if (!user) return;

        editingUser = uid;
        originalUserData = JSON.parse(JSON.stringify(user)); // Deep copy
        userModalTitle.textContent = "Edit User Attributes";
        
        // Fill form
        document.getElementById('m-username').value = getVal(user.attributes.uid);
        document.getElementById('m-username').disabled = true;
        document.getElementById('m-first_name').value = getVal(user.attributes.givenName);
        document.getElementById('m-last_name').value = getVal(user.attributes.sn);
        document.getElementById('m-mail').value = getVal(user.attributes.mail);
        document.getElementById('m-phone').value = getVal(user.attributes.mobile);
        document.getElementById('m-title').value = getVal(user.attributes.title);
        document.getElementById('m-department').value = getVal(user.attributes.departmentNumber);
        
        // Hide kind for edit as API doesn't seem to support changing it directly via edit_user easily or it's not needed
        document.getElementById('kind-container').style.display = 'none';
        document.getElementById('password-container').style.display = 'block';
        document.getElementById('password-container').querySelector('label').textContent = "New Password (optional)";
        document.getElementById('m-password').required = false;
        document.getElementById('m-password').value = '';

        userModal.style.display = 'block';
    };

    window.deleteUser = async function(uid) {
        if (!confirm(`Are you sure you want to delete user ${uid}?`)) return;

        try {
            const response = await fetch('/api/user/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: uid })
            });

            if (response.ok) {
                showToast("User deleted successfully", "success");
                await fetchData();
                renderUsers();
            } else {
                showToast("Failed to delete user", "error");
            }
        } catch (error) {
            showToast("Server error", "error");
        }
    };

    window.editGroup = function(name, type) {
        const groupList = type === 'POSIX' ? groups.posix_groups : groups.gon_groups;
        const group = groupList.find(g => getVal(g.attributes.cn) === name);
        if (!group) return;

        editingGroup = { name, type, description: getVal(group.attributes.description) };
        groupModalTitle.textContent = `Edit Group: ${name}`;
        
        // Fill form
        document.getElementById('g-name').value = name;
        document.getElementById('g-name').disabled = true;
        document.getElementById('g-new-name').value = name;
        document.getElementById('g-edit-name-container').style.display = 'block';
        document.getElementById('g-kind-container').style.display = 'none';
        document.getElementById('g-description').value = getVal(group.attributes.description);
        
        // Show members section
        document.getElementById('g-members-section').style.display = 'block';
        
        // Extract current members
        let members = [];
        if (type === 'POSIX') {
            members = group.attributes.memberUid || [];
        } else {
            const dns = group.attributes.member || [];
            members = dns.map(dn => {
                const match = dn.match(/uid=([^,]+)/);
                return match ? match[1] : dn;
            });
        }
        if (!Array.isArray(members)) members = [members];

        // Populate user select for adding members (FILTERED)
        const select = document.getElementById('g-add-member-select');
        const availableUsers = users.filter(u => !members.includes(getVal(u.attributes.uid)));
        
        select.innerHTML = '<option value="">Select User to Add</option>' + 
            availableUsers.map(u => `<option value="${getVal(u.attributes.uid)}">${getVal(u.attributes.uid)} (${getVal(u.attributes.cn)})</option>`).join('');

        // Render current members
        const mList = document.getElementById('g-members-list');
        mList.innerHTML = members.map(m => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span>${m}</span>
                <button type="button" class="btn btn-icon btn-sm btn-danger" onclick="removeMemberFromGroup('${name}', '${m}')" style="width: 25px; height: 25px;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('') || '<p style="color: #888; font-size: 12px; text-align: center;">No members yet</p>';

        groupModal.style.display = 'block';
    };

    window.removeMemberFromGroup = async function(groupName, username) {
        if (!confirm(`Remove ${username} from ${groupName}?`)) return;

        try {
            const response = await fetch('/api/group/members/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: groupName, members: [username] })
            });

            if (response.ok) {
                showToast("Member removed", "success");
                await fetchData();
                editGroup(groupName, editingGroup.type); // Refresh modal
                renderGroups();
            } else {
                showToast("Failed to remove member", "error");
            }
        } catch (error) {
            showToast("Server error", "error");
        }
    };

    window.deleteGroup = async function(name) {
        if (!confirm(`Are you sure you want to delete group ${name}?`)) return;

        try {
            const response = await fetch('/api/group/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            });

            if (response.ok) {
                showToast("Group deleted successfully", "success");
                await fetchData();
                renderGroups();
            } else {
                showToast("Failed to delete group", "error");
            }
        } catch (error) {
            showToast("Server error", "error");
        }
    };
});
