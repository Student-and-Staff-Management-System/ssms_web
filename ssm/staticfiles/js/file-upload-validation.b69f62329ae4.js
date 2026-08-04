/**
 * File Upload Size Validation
 * Validates file size before upload (10MB limit for compressible files, 100KB for others)
 */

(function () {
    'use strict';

    const MAX_FILE_SIZE = 100 * 1024; // 100KB in bytes for other files
    const COMPRESSIBLE_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes for compressible files
    const MAX_FILE_SIZE_KB = 100;

    /**
     * Validate file size
     */
    function validateFileSize(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const isCompressible = ['jpg', 'jpeg', 'png', 'webp', 'pdf'].includes(ext);
        const limit = isCompressible ? COMPRESSIBLE_MAX_FILE_SIZE : MAX_FILE_SIZE;
        const limitText = isCompressible ? '10MB' : `${MAX_FILE_SIZE_KB}KB`;

        if (file.size > limit) {
            return {
                valid: false,
                message: `File size must not exceed ${limitText}. Current file size: ${(file.size / 1024).toFixed(1)}KB`
            };
        }
        return { valid: true };
    }

    /**
     * Handle file input change
     */
    function handleFileInput(event) {
        const input = event.target;
        const file = input.files[0];

        if (!file) return;

        const validation = validateFileSize(file);

        if (!validation.valid) {
            // Show error message
            alert(validation.message);

            // Clear the input
            input.value = '';

            // Prevent form submission
            event.preventDefault();
            return false;
        }
    }

    /**
     * Initialize validation on all file inputs
     */
    function initFileValidation() {
        const fileInputs = document.querySelectorAll('input[type="file"]');

        fileInputs.forEach(input => {
            // Add change event listener
            input.addEventListener('change', handleFileInput);

            // Add help text if not already present
            if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('file-size-hint')) {
                const hint = document.createElement('small');
                hint.className = 'file-size-hint';
                hint.style.display = 'block';
                hint.style.color = '#666';
                hint.style.marginTop = '4px';
                hint.textContent = `PDF/Images up to 10MB will be auto-compressed under 100KB.`;

                // Insert after the input
                input.parentNode.insertBefore(hint, input.nextSibling);
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFileValidation);
    } else {
        initFileValidation();
    }
})();
