/**
 * POS System - Main JavaScript
 * Dark/Light theme toggle and global utilities
 */

(function() {
    'use strict';

    const THEME_KEY = 'pos-theme';
    const LIGHT = 'light';
    const DARK = 'dark';

    function getStoredTheme() {
        return localStorage.getItem(THEME_KEY) || LIGHT;
    }

    function setStoredTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        const icon = document.querySelector('#themeToggle i');
        if (icon) {
            icon.className = theme === DARK ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
        }
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-bs-theme') || LIGHT;
        const next = current === LIGHT ? DARK : LIGHT;
        applyTheme(next);
        setStoredTheme(next);
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        const stored = getStoredTheme();
        applyTheme(stored);

        const toggle = document.getElementById('themeToggle');
        if (toggle) {
            toggle.addEventListener('click', toggleTheme);
        }
    });
})();
