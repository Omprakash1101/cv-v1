# 🔐 Security Policy

## 📌 Supported Versions

This project is actively maintained for security updates on the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| 0.x.x   | :x:                |

> ⚠️ Only the latest stable version receives security patches. Older versions are not maintained.

---

## 🚨 Reporting a Vulnerability

We take security issues seriously and appreciate responsible disclosure.

If you discover a vulnerability, please report it using the following steps:

### 📩 How to Report

* Email: **[omprakaskgopi2k05@gmail.com](mailto:omprakashgopi2k05@gmail.com)**
* Subject: **[SECURITY] Vulnerability Report – CFG Analyzer**
* Include:

  * Description of the vulnerability
  * Steps to reproduce
  * Affected endpoints (e.g., `/diagram/`)
  * Possible impact
  * Suggested fix (if any)

---

## ⏱️ Response Timeline

| Stage            | Timeframe          |
| ---------------- | ------------------ |
| Initial response | Within 48 hours    |
| Investigation    | 3–5 business days  |
| Fix & patch      | 5–10 business days |

---

## 🔍 What to Expect

* ✅ Confirmation of receipt
* 🔍 Detailed investigation
* 🛠️ Fix or mitigation if valid
* 📢 Disclosure after patch (if applicable)

If the vulnerability is **accepted**, we will:

* Fix it in the next release
* Credit the reporter (optional)

If the vulnerability is **declined**, we will:

* Provide a clear explanation

---

## 🔐 Security Measures in This Project

This project follows secure coding practices including:

* ✅ No stack trace exposure to users (CWE-209 mitigation)
* ✅ Centralized error handling via middleware
* ✅ Secure logging (no sensitive data in responses)
* ✅ Input validation using serializers
* ✅ Sanitized API responses

---

## ⚠️ Scope

Please report only vulnerabilities related to:

* API endpoints (`/diagram/`, `/healthcheck/`)
* Error handling and data exposure
* File upload handling (ZIP processing)
* Authentication or authorization (if added later)

Out of scope:

* UI/UX issues
* Performance optimizations
* Non-security bugs

---

## 🙏 Acknowledgements

We thank all contributors and security researchers who help improve this project.


