const API_URL = 'http://127.0.0.1:5000/api';
let currentUser = null;
let authToken = null;
let allNotes = [];
let allTags = [];

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('loginForm')?.addEventListener('submit', handleLogin);
    document.getElementById('registerForm')?.addEventListener('submit', handleRegister);
    
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    document.getElementById('newNoteBtn')?.addEventListener('click', () => openNoteModal());
    document.getElementById('saveNoteBtn')?.addEventListener('click', saveNote);
    document.getElementById('closeModalBtn')?.addEventListener('click', closeNoteModal);
    
    document.getElementById('statusFilter')?.addEventListener('change', filterNotes);
    document.getElementById('tagFilter')?.addEventListener('change', filterNotes);
    document.getElementById('searchInput')?.addEventListener('input', filterNotes);
}

function checkAuth() {
    authToken = localStorage.getItem('authToken');
    if (authToken) {
        fetchCurrentUser();
    } else {
        showAuthPage();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            localStorage.setItem('authToken', authToken);
            currentUser = data.user;
            showDashboard();
        } else {
            showError('loginError', data.error);
        }
    } catch (error) {
        showError('loginError', 'Login failed. Please try again.');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            localStorage.setItem('authToken', authToken);
            currentUser = data.user;
            showDashboard();
        } else {
            showError('registerError', data.error);
        }
    } catch (error) {
        showError('registerError', 'Registration failed. Please try again.');
    }
}

function handleLogout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showAuthPage();
}

async function fetchCurrentUser() {
    try {
        const response = await fetch(`${API_URL}/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            showDashboard();
        } else {
            handleLogout();
        }
    } catch (error) {
        handleLogout();
    }
}

function showAuthPage() {
    document.getElementById('authPage').classList.remove('hidden');
    document.getElementById('dashboardPage').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('authPage').classList.add('hidden');
    document.getElementById('dashboardPage').classList.remove('hidden');
    document.getElementById('userName').textContent = currentUser.name;
    loadDashboardData();
}

function showLogin() {
    document.getElementById('loginContainer').classList.remove('hidden');
    document.getElementById('registerContainer').classList.add('hidden');
}

function showRegister() {
    document.getElementById('loginContainer').classList.add('hidden');
    document.getElementById('registerContainer').classList.remove('hidden');
}

async function loadDashboardData() {
    await Promise.all([
        fetchNotes(),
        fetchTags(),
        fetchStats()
    ]);
}

async function fetchNotes() {
    try {
        const response = await fetch(`${API_URL}/notes`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            allNotes = data.notes;
            displayNotes(allNotes);
        }
    } catch (error) {
        console.error('Failed to fetch notes:', error);
    }
}

async function fetchTags() {
    try {
        const response = await fetch(`${API_URL}/tags`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            allTags = data.tags;
            populateTagFilter();
        }
    } catch (error) {
        console.error('Failed to fetch tags:', error);
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_URL}/users/${currentUser.user_id}/stats`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayStats(data.stats);
        }
    } catch (error) {
        console.error('Failed to fetch stats:', error);
    }
}

function displayNotes(notes) {
    const grid = document.getElementById('notesGrid');
    
    if (notes.length === 0) {
        grid.innerHTML = '<div class="empty-state"><h3>No notes yet</h3><p>Click "New Note" to create your first note</p></div>';
        return;
    }
    
    grid.innerHTML = notes.map(note => `
        <div class="note-card ${note.status.toLowerCase()}" onclick="openNoteModal(${note.note_id})">
            <div class="note-header">
                <div class="note-title">${escapeHtml(note.title)}</div>
                <span class="note-status">${note.status}</span>
            </div>
            <div class="note-content">${escapeHtml(note.content || '')}</div>
            <div class="note-tags">
                ${note.tags.map(tag => `<span class="tag" style="background-color: ${tag.color}">${escapeHtml(tag.tag_name)}</span>`).join('')}
            </div>
            <div class="note-meta">Modified: ${new Date(note.last_modified).toLocaleDateString()}</div>
            <div class="note-actions" onclick="event.stopPropagation()">
                <button class="btn btn-secondary" onclick="updateNoteStatus(${note.note_id}, '${note.status === 'Pinned' ? 'Active' : 'Pinned'}')">
                    ${note.status === 'Pinned' ? 'Unpin' : 'Pin'}
                </button>
                <button class="btn btn-secondary" onclick="updateNoteStatus(${note.note_id}, '${note.status === 'Archived' ? 'Active' : 'Archived'}')">
                    ${note.status === 'Archived' ? 'Unarchive' : 'Archive'}
                </button>
                <button class="btn btn-secondary" onclick="deleteNote(${note.note_id})">Delete</button>
            </div>
        </div>
    `).join('');
}

function displayStats(stats) {
    document.getElementById('totalNotes').textContent = stats.total_notes;
    document.getElementById('activeNotes').textContent = stats.active_notes;
    document.getElementById('pinnedNotes').textContent = stats.pinned_notes;
    document.getElementById('archivedNotes').textContent = stats.archived_notes;
    document.getElementById('totalTags').textContent = stats.total_active_tags;
}

function populateTagFilter() {
    const select = document.getElementById('tagFilter');
    select.innerHTML = '<option value="">All Tags</option>' + 
        allTags.map(tag => `<option value="${tag.tag_id}">${escapeHtml(tag.tag_name)}</option>`).join('');
}

function filterNotes() {
    const status = document.getElementById('statusFilter').value;
    const tagId = document.getElementById('tagFilter').value;
    const search = document.getElementById('searchInput').value.toLowerCase();
    
    let filtered = allNotes;
    
    if (status) {
        filtered = filtered.filter(note => note.status === status);
    }
    
    if (tagId) {
        filtered = filtered.filter(note => note.tags.some(tag => tag.tag_id == tagId));
    }
    
    if (search) {
        filtered = filtered.filter(note => 
            note.title.toLowerCase().includes(search) || 
            note.content.toLowerCase().includes(search)
        );
    }
    
    displayNotes(filtered);
}

function openNoteModal(noteId = null) {
    const modal = document.getElementById('noteModal');
    const title = document.getElementById('modalTitle');
    const noteTitle = document.getElementById('noteTitle');
    const noteContent = document.getElementById('noteContent');
    const tagSelector = document.getElementById('tagSelector');
    
    if (noteId) {
        const note = allNotes.find(n => n.note_id === noteId);
        title.textContent = 'Edit Note';
        noteTitle.value = note.title;
        noteContent.value = note.content;
        document.getElementById('noteModal').dataset.noteId = noteId;
        
        tagSelector.innerHTML = allTags.map(tag => `
            <div class="tag-option ${note.tags.some(t => t.tag_id === tag.tag_id) ? 'selected' : ''}" 
                 style="background-color: ${tag.color}" 
                 data-tag-id="${tag.tag_id}"
                 onclick="toggleTag(this)">
                ${escapeHtml(tag.tag_name)}
            </div>
        `).join('');
    } else {
        title.textContent = 'New Note';
        noteTitle.value = '';
        noteContent.value = '';
        delete document.getElementById('noteModal').dataset.noteId;
        
        tagSelector.innerHTML = allTags.map(tag => `
            <div class="tag-option" 
                 style="background-color: ${tag.color}" 
                 data-tag-id="${tag.tag_id}"
                 onclick="toggleTag(this)">
                ${escapeHtml(tag.tag_name)}
            </div>
        `).join('');
    }
    
    modal.classList.add('active');
}

function closeNoteModal() {
    document.getElementById('noteModal').classList.remove('active');
}

function toggleTag(element) {
    element.classList.toggle('selected');
}

async function saveNote() {
    const noteId = document.getElementById('noteModal').dataset.noteId;
    const title = document.getElementById('noteTitle').value;
    const content = document.getElementById('noteContent').value;
    const selectedTags = Array.from(document.querySelectorAll('.tag-option.selected'))
        .map(el => parseInt(el.dataset.tagId));
    
    if (!title.trim()) {
        alert('Title is required');
        return;
    }
    
    const noteData = {
        title,
        content,
        tag_ids: selectedTags
    };
    
    try {
        const url = noteId ? `${API_URL}/notes/${noteId}` : `${API_URL}/notes`;
        const method = noteId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(noteData)
        });
        
        if (response.ok) {
            closeNoteModal();
            await loadDashboardData();
        } else {
            const data = await response.json();
            alert(data.error || 'Failed to save note');
        }
    } catch (error) {
        alert('Failed to save note. Please try again.');
    }
}

async function updateNoteStatus(noteId, status) {
    try {
        const response = await fetch(`${API_URL}/notes/${noteId}/status`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ status })
        });
        
        if (response.ok) {
            await loadDashboardData();
        }
    } catch (error) {
        console.error('Failed to update note status:', error);
    }
}

async function deleteNote(noteId) {
    if (!confirm('Are you sure you want to delete this note?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/notes/${noteId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            await loadDashboardData();
        }
    } catch (error) {
        console.error('Failed to delete note:', error);
    }
}

function showError(elementId, message) {
    const errorEl = document.getElementById(elementId);
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
