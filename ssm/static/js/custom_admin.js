/**
 * custom_admin.js - Enhanced JS functionality for Django Admin (Jazzmin)
 * Adds ordering / reordering support (Move Up, Move Down, Sort A-Z) to filter_horizontal multi-select widgets.
 */

document.addEventListener('DOMContentLoaded', function () {
    function initSelectorReorder() {
        const chosenContainers = document.querySelectorAll('.selector .selector-chosen');

        chosenContainers.forEach(function (chosenContainer) {
            if (chosenContainer.querySelector('.selector-reorder-bar')) {
                return; // Already initialized
            }

            const select = chosenContainer.querySelector('select');
            if (!select) return;

            // Create Reorder Control Bar
            const reorderBar = document.createElement('div');
            reorderBar.className = 'selector-reorder-bar';
            reorderBar.innerHTML = `
                <button type="button" class="selector-move-up" title="Move selected item up (Alt + Up)">
                    <i class="fas fa-arrow-up"></i> Move Up
                </button>
                <button type="button" class="selector-move-down" title="Move selected item down (Alt + Down)">
                    <i class="fas fa-arrow-down"></i> Move Down
                </button>
                <button type="button" class="selector-sort-az" title="Sort chosen items alphabetically">
                    <i class="fas fa-sort-alpha-down"></i> Sort A-Z
                </button>
            `;

            // Insert reorderBar before clearall link or append to container
            const clearAllLink = chosenContainer.querySelector('.selector-clearall');
            if (clearAllLink) {
                chosenContainer.insertBefore(reorderBar, clearAllLink);
            } else {
                chosenContainer.appendChild(reorderBar);
            }

            // Move Up Handler
            const moveUpBtn = reorderBar.querySelector('.selector-move-up');
            moveUpBtn.addEventListener('click', function (e) {
                e.preventDefault();
                moveSelectedOptions(select, -1);
            });

            // Move Down Handler
            const moveDownBtn = reorderBar.querySelector('.selector-move-down');
            moveDownBtn.addEventListener('click', function (e) {
                e.preventDefault();
                moveSelectedOptions(select, 1);
            });

            // Sort A-Z Handler
            const sortBtn = reorderBar.querySelector('.selector-sort-az');
            sortBtn.addEventListener('click', function (e) {
                e.preventDefault();
                sortOptionsAlphabetically(select);
            });

            // Keyboard navigation (Alt + Up / Alt + Down)
            select.addEventListener('keydown', function (e) {
                if (e.altKey && e.key === 'ArrowUp') {
                    e.preventDefault();
                    moveSelectedOptions(select, -1);
                } else if (e.altKey && e.key === 'ArrowDown') {
                    e.preventDefault();
                    moveSelectedOptions(select, 1);
                }
            });
        });
    }

    function moveSelectedOptions(select, direction) {
        const options = Array.from(select.options);
        const selected = options.filter(opt => opt.selected);
        if (selected.length === 0) return;

        if (direction === -1) {
            // Move Up
            for (let i = 0; i < options.length; i++) {
                const opt = options[i];
                if (opt.selected && i > 0) {
                    const prev = options[i - 1];
                    if (!prev.selected) {
                        select.insertBefore(opt, prev);
                        // Swap in array representation
                        options[i] = prev;
                        options[i - 1] = opt;
                    }
                }
            }
        } else if (direction === 1) {
            // Move Down
            for (let i = options.length - 1; i >= 0; i--) {
                const opt = options[i];
                if (opt.selected && i < options.length - 1) {
                    const next = options[i + 1];
                    if (!next.selected) {
                        select.insertBefore(next, opt);
                        // Swap in array representation
                        options[i] = next;
                        options[i + 1] = opt;
                    }
                }
            }
        }
    }

    function sortOptionsAlphabetically(select) {
        const options = Array.from(select.options);
        options.sort((a, b) => a.text.localeCompare(b.text, undefined, { sensitivity: 'base' }));
        options.forEach(opt => select.appendChild(opt));
    }

    // Run initialization
    initSelectorReorder();
    setTimeout(initSelectorReorder, 300);
    setTimeout(initSelectorReorder, 1000);
});
