document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('registration-form');

    // Helper: Check if element is visible (handles collapsed accordions logic if needed, 
    // though for validation we usually care if it's in the document flow and not hidden by styling)
    function isEffectivelyVisible(el) {
        if (!el) return false;
        if (el.disabled) return false;
        // Fields in 'display: none' sections (conditional logic) will have offsetParent === null
        if (el.offsetParent === null) return false;
        return true;
    }

    // Helper: UI helpers for errors
    const clearFieldErrors = () => {
        form.querySelectorAll('.field-error').forEach(el => {
            el.classList.remove('field-error');
        });
    };

    const markFieldError = (el) => {
        if (el) el.classList.add('field-error');
    };

    // Helper: Regex Validator
    const validateRegex = (id, regex, msg, errors) => {
        const el = document.getElementById(id);
        if (!el || !isEffectivelyVisible(el)) return;
        const value = (el.value || '').trim();
        if (value && !regex.test(value)) {
            errors.push(msg);
            markFieldError(el);
        }
    };

    // Helper: Numeric Range Validator
    const checkRange = (name, min, max, label, errors) => {
        const el = form.querySelector(`input[name="${name}"]`);
        if (!el || !isEffectivelyVisible(el)) return;
        if (el.value) {
            const val = parseFloat(el.value);
            if (isNaN(val) || val < min || val > max) {
                errors.push(`${label} must be between ${min} and ${max}.`);
                markFieldError(el);
            }
        }
    };

    // Helper: File Validator
    const validateFileInputs = (errors) => {
        const maxSizeMB = 5;
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        const fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            if (!isEffectivelyVisible(input) || !input.files || !input.files[0]) return;
            const file = input.files[0];
            if (file.size > maxSizeBytes) {
                errors.push(`${input.name || 'File'} must be smaller than ${maxSizeMB} MB.`);
                markFieldError(input);
            }
        });
    };

    // Helper: Age Validator
    const validateAge = (errors) => {
        const dobEl = document.getElementById('date_of_birth');
        if (!dobEl || !dobEl.value || !isEffectivelyVisible(dobEl)) return;
        const dob = new Date(dobEl.value);
        if (isNaN(dob.getTime())) return;
        const age = (Date.now() - dob.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
        if (age < 15) {
            errors.push("Student must be at least 15 years old.");
            markFieldError(dobEl);
        }
    };

    if (form) {
        form.addEventListener('submit', async function (event) {
            event.preventDefault();
            clearFieldErrors();
            let errors = [];

            // ---------------------------------------------------------
            // 1. Required Field Validation
            // ---------------------------------------------------------
            const requiredElements = form.querySelectorAll('[required]');
            requiredElements.forEach(el => {
                if (!isEffectivelyVisible(el)) return;
                if (!el.value || !el.value.trim()) {
                    let label = "Field";
                    const id = el.id;
                    if (id) {
                        const labelEl = form.querySelector(`label[for="${id}"]`);
                        if (labelEl) label = labelEl.textContent.trim();
                    } else {
                        label = el.name || "Field";
                    }
                    errors.push(`${label} is required.`);
                    markFieldError(el);
                }
            });

            // ---------------------------------------------------------
            // 2. Password Validation
            // ---------------------------------------------------------
            const pw = document.getElementById('password');
            const cpw = document.getElementById('confirm-password');

            if (pw && isEffectivelyVisible(pw)) {
                if (pw.value.length < 6) {
                    errors.push("Password must be at least 6 characters.");
                    markFieldError(pw);
                }
            }
            if (pw && cpw && isEffectivelyVisible(cpw)) {
                if (pw.value !== cpw.value) {
                    errors.push("Passwords do not match.");
                    markFieldError(cpw);
                }
            }

            // ---------------------------------------------------------
            // 3. Pattern Validation (Regex)
            // ---------------------------------------------------------
            validateRegex('student_mobile', /^\d{10}$/, "Student Mobile must be 10 digits.", errors);
            validateRegex('father_mobile', /^\d{10}$/, "Father Mobile must be 10 digits.", errors);
            validateRegex('mother_mobile', /^\d{10}$/, "Mother Mobile must be 10 digits.", errors);
            validateRegex('aadhaar_number', /^\d{12}$/, "Aadhaar Number must be 12 digits.", errors);
            validateRegex('ifsc_code', /^[A-Z]{4}0[A-Z0-9]{6}$/, "Invalid IFSC Code.", errors);
            validateRegex('student_email', /^[^\s@]+@[^\s@]+\.[^\s@]+$/, "Invalid Email Format.", errors);

            // ---------------------------------------------------------
            // 4. Numeric Range Validation
            // ---------------------------------------------------------
            checkRange('sslc_percentage', 0, 100, "SSLC Percentage", errors);
            checkRange('hsc_percentage', 0, 100, "HSC Percentage", errors);
            checkRange('diploma_percentage', 0, 100, "Diploma Percentage", errors);
            checkRange('ug_ogpa', 0, 10, "UG OGPA", errors);
            checkRange('pg_ogpa', 0, 10, "PG OGPA", errors);

            // ---------------------------------------------------------
            // 5. Age Validation
            // ---------------------------------------------------------
            validateAge(errors);

            // ---------------------------------------------------------
            // 6. File Upload Validation
            // ---------------------------------------------------------
            validateFileInputs(errors);

            if (errors.length > 0) {
                const uniqueErrors = [...new Set(errors)];
                Swal.fire({
                    icon: 'warning',
                    title: 'Validation Error',
                    html: uniqueErrors.join("<br>"),
                    confirmButtonColor: '#5a7d7c',
                    confirmButtonText: 'OK'
                });
                return;
            }

            // Submission
            const formData = new FormData(form);
            const registerUrl = form.getAttribute('data-register-url');
            const successUrl = form.getAttribute('data-success-url');
            // Get CSRF token from the input field usually generated by {% csrf_token %}
            const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfToken = csrfTokenInput ? csrfTokenInput.value : '';

            try {
                const response = await fetch(registerUrl, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-CSRFToken': csrfToken }
                });
                const result = await response.json();
                if (response.ok) {
                    Swal.fire({
                        title: 'Success!',
                        text: 'Registration successful!',
                        icon: 'success',
                        confirmButtonColor: '#5a7d7c',
                        timer: 2000,
                        showConfirmButton: false
                    }).then(() => {
                    }).then(() => {
                        // Redirect to student dashboard as per backend instruction implies completion
                        if (successUrl) {
                            window.location.href = successUrl;
                        } else {
                            window.location.href = "/dashboard/";
                        }
                    });
                } else {
                    if (result.error) {
                        Swal.fire({
                            icon: 'error',
                            title: 'Server Error',
                            text: result.error,
                            confirmButtonColor: '#5a7d7c'
                        });
                    } else {
                        Swal.fire({
                            icon: 'error',
                            title: 'Registration Failed',
                            text: 'Please check your data.',
                            confirmButtonColor: '#5a7d7c'
                        });
                    }
                }
            } catch (error) {
                console.error('Submission Error:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Network Error',
                    text: 'An unexpected network error occurred.',
                    confirmButtonColor: '#5a7d7c'
                });
            }
        });
    }
});
