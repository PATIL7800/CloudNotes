
import { initializeApp } from "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";

import {
    getAuth,
    createUserWithEmailAndPassword,
    signInWithEmailAndPassword
} from "https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js";

import { firebaseConfig } from "./firebase-config.js";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

async function establishFlaskSession(user) {
    const idToken = await user.getIdToken();

    const response = await fetch("/auth/session", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        credentials: "same-origin",
        body: JSON.stringify({ idToken })
    });

    if (!response.ok) {
        throw new Error("Could not establish your session.");
    }
}

function showError(message) {
    const errorBox = document.getElementById("auth-error");
    if (errorBox) {
        errorBox.textContent = message;
    }
}

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        showError("");

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        try {
            const result = await signInWithEmailAndPassword(
                auth, email, password
            );

            await establishFlaskSession(result.user);
            window.location.href = "/dashboard";
        } catch (error) {
            showError(error.message);
        }
    });
}

if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        showError("");

        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        try {
            const result = await createUserWithEmailAndPassword(
                auth, email, password
            );

            await establishFlaskSession(result.user);
            window.location.href = "/dashboard";
        } catch (error) {
            showError(error.message);
        }
    });
}
