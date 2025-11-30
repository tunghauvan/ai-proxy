<template>
  <div id="app-root">
    <header>
      <div class="logo">LangGraph Proxy</div>
      <nav>
        <router-link to="/">Models</router-link>
        <router-link to="/create">Create</router-link>
        <router-link to="/playground">Playground</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
:root {
  --primary-color: #212529;
  --primary-hover: #343a40;
  --secondary-bg: #e9ecef;
  --secondary-hover: #dee2e6;
  --danger-color: #dc3545;
  --danger-hover: #bd2130;
  --success-color: #198754;
  --warning-color: #ffc107;
  --text-color: #212529;
  --text-muted: #6c757d;
  --border-color: #ced4da;
  --border-radius: 6px;
  --focus-ring: 0 0 0 3px rgba(33, 37, 41, 0.1);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #f8f9fa;
  color: var(--text-color);
  line-height: 1.5;
}

#app-root {
  width: 100%;
  margin: 0;
  padding: 0 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  border-bottom: 1px solid #e9ecef;
  margin-bottom: 2rem;
}

.logo {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-color);
}

nav {
  display: flex;
  gap: 0.5rem;
}

nav a {
  padding: 0.5rem 1rem;
  text-decoration: none;
  color: #495057;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: var(--border-radius);
  transition: background 0.15s, color 0.15s;
}

nav a:hover {
  background: var(--secondary-bg);
  color: var(--text-color);
}

nav a.router-link-active {
  background: var(--primary-color);
  color: #fff;
}

main {
  background: #fff;
  border-radius: 8px;
  padding: 2rem;
  border: 1px solid #e9ecef;
  min-height: calc(100vh - 140px);
  width: 100%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* --- Global Design System --- */

/* Typography */
h1, h2, h3, h4, h5, h6 {
  margin: 0;
  color: var(--text-color);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0 0 0.25rem 0;
}

.subtitle {
  color: var(--text-muted);
  margin: 0;
  font-size: 0.875rem;
}

.section-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 0.75rem;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: var(--border-radius);
  border: none;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  text-decoration: none;
  line-height: 1.5;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--secondary-bg);
  color: #495057;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--secondary-hover);
}

.btn-danger {
  background: var(--danger-color);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: var(--danger-hover);
}

/* Icon Buttons */
.icon-button {
  width: 36px;
  height: 36px;
  border-radius: var(--border-radius);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-muted);
}

.icon-button:hover:not(:disabled) {
  background: var(--secondary-bg);
  color: var(--text-color);
}

.icon-button svg {
  width: 18px;
  height: 18px;
}

.icon-button-success { color: var(--success-color); background: #e6f5ec; }
.icon-button-success:hover:not(:disabled) { background: #d1e7dd; }

.icon-button-warning { color: #c2410c; background: #fff4e6; }
.icon-button-warning:hover:not(:disabled) { background: #ffe8cc; }

.icon-button-danger { color: var(--danger-color); background: #fee2e2; }
.icon-button-danger:hover:not(:disabled) { background: #f8d7da; }

/* Forms */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-bottom: 1rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #495057;
}

.form-input,
.form-select,
.form-textarea {
  display: block;
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  font-weight: 400;
  line-height: 1.5;
  color: var(--text-color);
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  border-color: var(--primary-color);
  outline: 0;
  box-shadow: var(--focus-ring);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: #adb5bd;
}

.form-textarea {
  resize: vertical;
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color);
  cursor: pointer;
  user-select: none;
}

.checkbox-label input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
  accent-color: var(--primary-color);
}

.form-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}

/* Badges */
.status-badge {
  padding: 0.25rem 0.6rem;
  border-radius: 50rem;
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.status-active { background: #dcfce7; color: #15803d; }
.status-enabled { background: #dbeafe; color: #1d4ed8; }
.status-disabled { background: #e9ecef; color: #495057; }

/* Utilities */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(0,0,0,0.1);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-message {
  color: #842029;
  background-color: #f8d7da;
  border: 1px solid #f5c2c7;
  padding: 0.75rem 1rem;
  border-radius: var(--border-radius);
  font-size: 0.875rem;
  margin-bottom: 1rem;
}
</style>
