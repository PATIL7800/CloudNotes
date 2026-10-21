
import { initializeApp, getApps, getApp } from
    "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";

import {
    getAuth,
    onAuthStateChanged
} from "https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js";

import { firebaseConfig } from "./firebase-config.js";

const app = getApps().length
    ? getApp()
    : initializeApp(firebaseConfig);

const auth = getAuth(app);

const toggle = document.getElementById("profile-toggle");
const menu = document.getElementById("profile-menu");
const emailElement = document.getElementById("profile-email");
const avatar = document.getElementById("profile-toggle");
const largeAvatar = document.getElementById("profile-large-avatar");

if (toggle && menu) {
    toggle.addEventListener("click", () => {
        const isOpening = menu.hidden;
        menu.hidden = !isOpening;
        toggle.setAttribute("aria-expanded", String(isOpening));
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".profile-area")) {
            menu.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            menu.hidden = true;
            toggle.setAttribute("aria-expanded", "false");
        }
    });
}

onAuthStateChanged(auth, (user) => {
    if (user && user.email) {
        const email = user.email;
        const initial = email.charAt(0).toUpperCase();

        if (emailElement) {
            emailElement.textContent = email;
        }

        if (avatar) {
            avatar.textContent = initial;
        }

        if (largeAvatar) {
            largeAvatar.textContent = initial;
        }
    } else {
        if (emailElement) {
            emailElement.textContent = "Account email unavailable";
        }

        if (avatar) {
            avatar.textContent = "U";
        }

        if (largeAvatar) {
            largeAvatar.textContent = "U";
        }
    }
});
