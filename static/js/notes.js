
const noteForm = document.getElementById("note-form");
const titleInput = document.getElementById("note-title");
const contentInput = document.getElementById("note-content");
const notesList = document.getElementById("notes-list");
const message = document.getElementById("note-message");
const loadingMessage = document.getElementById("loading-message");
const saveButton = document.getElementById("save-button");
const cancelButton = document.getElementById("cancel-edit");
const formHeading = document.getElementById("form-heading");

const searchInput = document.getElementById("note-search");
const filterSelect = document.getElementById("note-filter");

let editingNoteId = null;
let allNotes = [];

function showMessage(text, isError = false) {
    message.textContent = text;
    message.style.color = isError ? "#dc2626" : "#15803d";
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}

function resetForm() {
    editingNoteId = null;
    noteForm.reset();
    formHeading.textContent = "Create a Note";
    saveButton.textContent = "Save Note";
    cancelButton.hidden = true;
}

function renderNotes() {
    notesList.replaceChildren();

    const query = searchInput.value.trim().toLowerCase();
    const filter = filterSelect.value;

    const filteredNotes = allNotes.filter(note => {
        const matchesSearch =
            (note.title || "").toLowerCase().includes(query) ||
            (note.content || "").toLowerCase().includes(query);

        const matchesFilter =
            filter === "all" ||
            (filter === "pinned" && note.pinned === true) ||
            (filter === "favorites" && note.favorite === true);

        return matchesSearch && matchesFilter;
    });

    // Pinned notes appear first.
    filteredNotes.sort((a, b) =>
        Number(b.pinned === true) - Number(a.pinned === true)
    );

    if (allNotes.length === 0) {
        loadingMessage.textContent = "You have no saved notes yet.";
        return;
    }

    loadingMessage.textContent = filteredNotes.length === 0
        ? "No notes match your search or filter."
        : "";

    filteredNotes.forEach(note => {
        const card = document.createElement("article");
        card.className = "auth-card note-card";

        const title = document.createElement("h3");
        title.textContent =
            `${note.pinned ? "📌 " : ""}${note.title}`;

        const content = document.createElement("p");
        content.className = "note-content";
        content.textContent = note.content;

        const actions = document.createElement("div");
        actions.className = "note-actions";

        const pinButton = document.createElement("button");
        pinButton.type = "button";
        pinButton.textContent = note.pinned
            ? "Unpin"
            : "📌 Pin";

        pinButton.addEventListener("click", () =>
            updatePreference(note, "pinned", !note.pinned)
        );

        const favoriteButton = document.createElement("button");
        favoriteButton.type = "button";
        favoriteButton.textContent = note.favorite
            ? "★ Favorited"
            : "☆ Favorite";

        favoriteButton.addEventListener("click", () =>
            updatePreference(note, "favorite", !note.favorite)
        );

        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.textContent = "Edit";

        editButton.addEventListener("click", () => {
            editingNoteId = note.id;
            titleInput.value = note.title;
            contentInput.value = note.content;
            formHeading.textContent = "Edit Note";
            saveButton.textContent = "Update Note";
            cancelButton.hidden = false;
            noteForm.scrollIntoView({ behavior: "smooth" });
        });

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.textContent = "Delete";
        deleteButton.className = "delete-button";

        deleteButton.addEventListener("click", async () => {
            if (!confirm(`Delete "${note.title}"?`)) return;

            try {
                await apiRequest(
                    `/api/notes/${encodeURIComponent(note.id)}`,
                    { method: "DELETE" }
                );

                if (editingNoteId === note.id) resetForm();

                showMessage("Note deleted successfully.");
                await loadNotes();
            } catch (error) {
                showMessage(error.message, true);
            }
        });

        actions.append(
            pinButton,
            favoriteButton,
            editButton,
            deleteButton
        );

        card.append(title, content, actions);
        notesList.appendChild(card);
    });
}

async function updatePreference(note, field, value) {
    try {
        await apiRequest(
            `/api/notes/${encodeURIComponent(note.id)}/preferences`,
            {
                method: "PATCH",
                body: JSON.stringify({ [field]: value })
            }
        );

        showMessage(
            field === "pinned"
                ? (value ? "Note pinned." : "Note unpinned.")
                : (value ? "Note added to favorites." : "Removed from favorites.")
        );

        await loadNotes();
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function loadNotes() {
    loadingMessage.textContent = "Loading your notes...";

    try {
        const notes = await apiRequest("/api/notes");

        // Older notes may not have these fields yet.
        allNotes = notes.map(note => ({
            ...note,
            pinned: note.pinned === true,
            favorite: note.favorite === true
        }));

        renderNotes();
    } catch (error) {
        allNotes = [];
        notesList.replaceChildren();
        loadingMessage.textContent = error.message;
    }
}

noteForm.addEventListener("submit", async event => {
    event.preventDefault();

    const title = titleInput.value.trim();
    const content = contentInput.value.trim();

    if (!title || !content) {
        showMessage("Please enter both a title and content.", true);
        return;
    }

    saveButton.disabled = true;

    try {
        if (editingNoteId) {
            await apiRequest(
                `/api/notes/${encodeURIComponent(editingNoteId)}`,
                {
                    method: "PUT",
                    body: JSON.stringify({ title, content })
                }
            );

            showMessage("Note updated successfully.");
        } else {
            await apiRequest("/api/notes", {
                method: "POST",
                body: JSON.stringify({ title, content })
            });

            showMessage("Note saved successfully.");
        }

        resetForm();
        await loadNotes();
    } catch (error) {
        showMessage(error.message, true);
    } finally {
        saveButton.disabled = false;
    }
});

cancelButton.addEventListener("click", resetForm);

searchInput.addEventListener("input", renderNotes);
filterSelect.addEventListener("change", renderNotes);

loadNotes();
