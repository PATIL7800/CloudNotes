
const fileForm = document.getElementById("file-form");
const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-button");
const fileMessage = document.getElementById("file-message");
const fileLoading = document.getElementById("file-loading");
const filesList = document.getElementById("files-list");

function showFileMessage(text, isError = false) {
    fileMessage.textContent = text;
    fileMessage.style.color = isError ? "#dc2626" : "#15803d";
}

async function fileRequest(url, options = {}) {
    const response = await fetch(url, options);

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
}

async function loadFiles() {
    fileLoading.textContent = "Loading your files...";
    filesList.replaceChildren();

    try {
        const files = await fileRequest("/api/files");

        fileLoading.textContent =
            files.length === 0 ? "No files uploaded yet." : "";

        files.forEach(file => {
            const card = document.createElement("div");
            card.className = "file-card";

            const name = document.createElement("span");
            name.className = "file-name";
            name.textContent = file.filename;

            const actions = document.createElement("div");
            actions.className = "file-actions";

            const download = document.createElement("a");
            download.href =
                `/api/files/${encodeURIComponent(file.id)}/download`;
            download.textContent = "Download";
            download.className = "file-download";

            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "Delete";
            remove.className = "delete-button";

            remove.addEventListener("click", async () => {
                if (!confirm(`Delete "${file.filename}"?`)) return;

                try {
                    await fileRequest(
                        `/api/files/${encodeURIComponent(file.id)}`,
                        { method: "DELETE" }
                    );

                    showFileMessage("File deleted successfully.");
                    await loadFiles();
                } catch (error) {
                    showFileMessage(error.message, true);
                }
            });

            actions.append(download, remove);
            card.append(name, actions);
            filesList.appendChild(card);
        });
    } catch (error) {
        fileLoading.textContent = error.message;
    }
}

fileForm.addEventListener("submit", async event => {
    event.preventDefault();

    const file = fileInput.files[0];

    if (!file) {
        showFileMessage("Please select a file.", true);
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showFileMessage("File size must be 10 MB or less.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    uploadButton.disabled = true;

    try {
        await fileRequest("/api/files", {
            method: "POST",
            body: formData
        });

        fileForm.reset();
        showFileMessage("File uploaded successfully.");
        await loadFiles();
    } catch (error) {
        showFileMessage(error.message, true);
    } finally {
        uploadButton.disabled = false;
    }
});

loadFiles();
