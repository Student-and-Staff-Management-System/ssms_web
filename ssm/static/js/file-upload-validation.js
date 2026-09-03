/**
 * Client-Side File Upload Validation & Image Compression
 * Automatically compresses images in-browser to under 100KB before form submission.
 */

(function () {
    'use strict';

    const TARGET_MAX_SIZE = 100 * 1024; // 100KB in bytes
    const COMPRESSIBLE_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB limit for compressible files
    const TARGET_MAX_SIZE_KB = 100;

    /**
     * Client-side HTML5 Canvas Image Compression
     */
    function compressImageFile(file, inputElement) {
        if (!file || !file.type.startsWith('image/')) return;
        if (file.size <= TARGET_MAX_SIZE) return;

        const reader = new FileReader();
        reader.onload = function (e) {
            const img = new Image();
            img.onload = function () {
                let width = img.width;
                let height = img.height;
                const maxDim = 1200;

                if (width > maxDim || height > maxDim) {
                    if (width > height) {
                        height = Math.round((height * maxDim) / width);
                        width = maxDim;
                    } else {
                        width = Math.round((width * maxDim) / height);
                        height = maxDim;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');

                // Fill white background for transparent images
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, width, height);
                ctx.drawImage(img, 0, 0, width, height);

                let quality = 0.85;

                function attemptBlobCompress() {
                    canvas.toBlob(function (blob) {
                        if (blob && blob.size > TARGET_MAX_SIZE && quality > 0.2) {
                            quality -= 0.15;
                            attemptBlobCompress();
                        } else if (blob) {
                            try {
                                const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
                                const newFileName = baseName + '.jpg';
                                const compressedFile = new File([blob], newFileName, {
                                    type: 'image/jpeg',
                                    lastModified: Date.now()
                                });

                                if (window.DataTransfer) {
                                    const dt = new DataTransfer();
                                    dt.items.add(compressedFile);
                                    inputElement.files = dt.files;
                                }

                                console.log(`[JS Compression] ${file.name} compressed: ${(file.size / 1024).toFixed(1)}KB -> ${(compressedFile.size / 1024).toFixed(1)}KB`);
                            } catch (err) {
                                console.warn('[JS Compression] Failed to assign compressed file to input:', err);
                            }
                        }
                    }, 'image/jpeg', quality);
                }

                attemptBlobCompress();
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }

    /**
     * Validate file size
     */
    function validateFileSize(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const isCompressible = ['jpg', 'jpeg', 'png', 'webp', 'pdf'].includes(ext);
        const limit = isCompressible ? COMPRESSIBLE_MAX_FILE_SIZE : TARGET_MAX_SIZE;
        const limitText = isCompressible ? '10MB' : `${TARGET_MAX_SIZE_KB}KB`;

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
            alert(validation.message);
            input.value = '';
            event.preventDefault();
            return false;
        }

        // Trigger in-browser image compression automatically
        compressImageFile(file, input);
    }

    /**
     * Initialize validation and compression on all file inputs
     */
    function initFileValidation() {
        const fileInputs = document.querySelectorAll('input[type="file"]');

        fileInputs.forEach(input => {
            input.removeEventListener('change', handleFileInput);
            input.addEventListener('change', handleFileInput);

            // Add help hint if not present
            if (!input.nextElementSibling || !input.nextElementSibling.classList.contains('file-size-hint')) {
                const hint = document.createElement('small');
                hint.className = 'file-size-hint';
                hint.style.display = 'block';
                hint.style.color = '#64748b';
                hint.style.fontSize = '0.75rem';
                hint.style.marginTop = '4px';
                hint.textContent = `PDFs & Images up to 10MB will be auto-compressed under 100KB.`;

                input.parentNode.insertBefore(hint, input.nextSibling);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFileValidation);
    } else {
        initFileValidation();
    }
})();
