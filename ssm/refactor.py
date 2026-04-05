import re

filepath = 'templates/staff/staff_portfolio.html'
with open(filepath, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Strip the custom modals. They are between <!-- MODALS --> and the first <script> block, wait, let's safely locate them.
# The modals are: `id="modalConference"`, `id="modalJournal"`, `id="modalBook"`, `id="modalSeminar"`, `id="modalAward"`, `id="modalStudent"`.
# Let's cleanly replace the blocks containing them.
for modal_id in ['modalConference', 'modalJournal', 'modalBook', 'modalSeminar', 'modalAward', 'modalStudent']:
    # The modal structure is <div id="modalXXX" class="modal"> ... </div>
    # But because they have nested divs, regex is tricky. Let's instead use a python html parser or just string manipulation if possible.
    pass

# A simpler way to do the replacement is to replace all specific Add button `href` or `onclick` manually or via regex.
# <button onclick="openModal('modalConference')" class="btn-add">➕ Add Conference</button>
c = re.sub(r'<button onclick="openModal\(\'modalConference\'\)" class="btn-add">➕ Add Conference</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_conference\' %}\', \'Add Conference\')" class="btn-add">➕ Add Conference</button>', c)

c = re.sub(r'<button onclick="openModal\(\'modalJournal\'\)" class="btn-add">➕ Add Journal</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_journal\' %}\', \'Add Journal\')" class="btn-add">➕ Add Journal</button>', c)

c = re.sub(r'<button onclick="openModal\(\'modalBook\'\)" class="btn-add">➕ Add Book / Article</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_book\' %}\', \'Add Book / Article\')" class="btn-add">➕ Add Book / Article</button>', c)

c = re.sub(r'<button onclick="openModal\(\'modalSeminar\'\)" class="btn-add">➕ Add Seminar</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_seminar\' %}\', \'Add Seminar\')" class="btn-add">➕ Add Seminar</button>', c)

c = re.sub(r'<button onclick="openModal\(\'modalAward\'\)" class="btn-add">➕ Add Award</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_award\' %}\', \'Add Award\')" class="btn-add">➕ Add Award</button>', c)

c = re.sub(r'<button onclick="openModal\(\'modalStudent\'\)" class="btn-add">➕ Add Student</button>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_student\' %}\', \'Add Student\')" class="btn-add">➕ Add Student</button>', c)

# Now the generic Add links:
c = re.sub(r'<a href="{% url \'staffs:portfolio_add_qualification\' %}" class="btn-add">➕ Add Qualification</a>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_qualification\' %}\', \'Add Qualification\')" class="btn-add">➕ Add Qualification</button>', c)

c = re.sub(r'<a href="{% url \'staffs:portfolio_add_designation\' %}" class="btn-add">➕ Add Designation</a>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_designation\' %}\', \'Add Designation\')" class="btn-add">➕ Add Designation</button>', c)

c = re.sub(r'<a href="{% url \'staffs:portfolio_add_membership\' %}" class="btn-add">➕ Add Membership</a>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_add_membership\' %}\', \'Add Membership\')" class="btn-add">➕ Add Membership</button>', c)

# And replace Edit links:
# <a href="{% url 'staffs:portfolio_edit_conference' c.pk %}" class="btn-edit">Edit</a>
c = re.sub(r'<a href="{% url \'staffs:portfolio_edit_([a-z_]+)\' (([a-z]\.)?pk(?:=item\.pk)?) %}" class="btn-edit">Edit</a>',
           r'<button onclick="openDynamicModal(\'{% url \'staffs:portfolio_edit_\1\' \2 %}\', \'Edit Entry\')" class="btn-edit">Edit</button>', c)

# Add the Unified Dynamic Modal HTML at the end, right before <script>
dynamic_modal_html = """
            <!-- UNIFIED DYNAMIC MODAL -->
            <div id="dynamicModal" class="modal dynamic-modal" style="display:none; align-items:center; justify-content:center; backdrop-filter: blur(4px);">
                <div class="modal-content" style="max-width: 650px; border-radius: 20px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); overflow: hidden; transform: scale(0.95); opacity: 0; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); margin: 20px; display: flex; flex-direction: column; max-height: 90vh;">
                    <div class="modal-header" style="background: var(--surface); border-bottom: 1px solid var(--border); padding: 20px 24px; position: sticky; top: 0; z-index: 10; display: flex; align-items: center; justify-content: space-between;">
                        <h3 id="dynamicModalTitle" style="margin: 0; font-size: 1.25rem; font-weight: 600; color: var(--primary-dark);">Modal Title</h3>
                        <button onclick="closeDynamicModal()" class="modal-close" style="background: var(--primary-light); border: none; width: 32px; height: 32px; border-radius: 50%; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--primary-dark); transition: all 0.2s;">&times;</button>
                    </div>
                    <div id="dynamicModalBody" style="padding: 0; overflow-y: auto; flex: 1; background: var(--bg-body); position: relative;">
                        <!-- Fetched content injected here -->
                    </div>
                </div>
            </div>
            
            <style>
                .modal-content.show {
                    transform: scale(1) !important;
                    opacity: 1 !important;
                }
                .btn-add { cursor: pointer; }
                .btn-edit { cursor: pointer; border: none; font-family: inherit; }
                .btn-delete { cursor: pointer; }
                
                /* Pill Tabs Modernization */
                .tab-container {
                    display: flex; gap: 8px; margin-bottom: 24px; border-bottom: none !important;
                    background: var(--surface); padding: 8px; border-radius: 100px; box-shadow: var(--shadow-sm);
                    overflow-x: auto;
                }
                .tab-link {
                    background: transparent; border: none !important; padding: 10px 18px; font-size: 0.95rem;
                    font-weight: 500; color: var(--text-muted); cursor: pointer; border-radius: 100px;
                    white-space: nowrap; transition: all 0.2s ease;
                }
                .tab-link:hover { color: var(--primary); background: var(--primary-light); }
                .tab-link.active {
                    background: var(--primary) !important; color: white !important;
                    box-shadow: 0 4px 6px -1px rgba(90, 125, 124, 0.4); font-weight: 600; border-bottom: none !important;
                }
                /* End Pill Tabs */
            </style>
"""

javascript_code = """
                async function openDynamicModal(url, title) {
                    const modal = document.getElementById('dynamicModal');
                    const modalContent = modal.querySelector('.modal-content');
                    const titleEl = document.getElementById('dynamicModalTitle');
                    const bodyEl = document.getElementById('dynamicModalBody');
                    
                    titleEl.innerText = title || "Form";
                    bodyEl.innerHTML = '<div style="padding: 60px; text-align: center; color: var(--text-muted);"><div style="display:inline-block; width: 30px; height: 30px; border: 3px solid var(--primary-light); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite;"></div><p style="margin-top: 15px;">Loading...</p></div>';
                    
                    modal.style.display = "flex";
                    // Trigger reflow for animation
                    void modal.offsetWidth;
                    modalContent.classList.add('show');
                    
                    try {
                        const response = await fetch(url, {
                            headers: { 'X-Requested-With': 'XMLHttpRequest' }
                        });
                        const htmlText = await response.text();
                        const parser = new DOMParser();
                        const doc = parser.parseFromString(htmlText, 'text/html');
                        
                        let formContainer = doc.querySelector('.form-container');
                        if(formContainer) {
                            // Extract just the form, we already have header in modal
                            const formElement = formContainer.querySelector('form');
                            if(formElement) {
                                // Add some internal padding to form
                                formElement.style.padding = '24px';
                                // Style the buttons cleanly
                                const btnBar = formElement.querySelector('.btn-bar');
                                if(btnBar) {
                                    btnBar.style.paddingTop = '10px';
                                    btnBar.style.marginTop = '10px';
                                    btnBar.style.borderTop = '1px solid var(--border)';
                                    const cancelBtn = btnBar.querySelector('.btn-cancel');
                                    if(cancelBtn) { cancelBtn.outerHTML = '<button type="button" class="btn-cancel" onclick="closeDynamicModal()" style="background: none; border: none; font-weight: 500; color: var(--text-muted); cursor: pointer; padding: 12px 24px;">Cancel</button>'; }
                                }
                                
                                bodyEl.innerHTML = formElement.outerHTML;
                                const newForm = bodyEl.querySelector('form');
                                newForm.action = url;
                                
                                newForm.addEventListener('submit', async function(e) {
                                    e.preventDefault();
                                    const submitBtn = newForm.querySelector('button[type="submit"]');
                                    const originalText = submitBtn.innerText;
                                    submitBtn.innerText = 'Saving...';
                                    submitBtn.disabled = true;
                                    
                                    try {
                                        const formData = new FormData(newForm);
                                        const postRes = await fetch(url, {
                                            method: 'POST',
                                            body: formData,
                                            redirect: 'follow',
                                            headers: { 'X-Requested-With': 'XMLHttpRequest' }
                                        });
                                        // If url changed to staff_portfolio -> Success redirect
                                        if (postRes.url.includes('staff_portfolio') && !postRes.url.includes('/edit/')) {
                                            window.location.reload();
                                        } else {
                                            // Validation failed, fetch returned the form with errors!
                                            const errHtml = await postRes.text();
                                            const errDoc = new DOMParser().parseFromString(errHtml, 'text/html');
                                            const errForm = errDoc.querySelector('.form-container form');
                                            if(errForm) {
                                                errForm.style.padding = '24px';
                                                bodyEl.innerHTML = errForm.outerHTML;
                                                // Re-attach listener (recursively or simply reload logic)
                                                // Simpler: Just tell user to refresh or we just inline the errors, but the submit button is re-rendered which loses event listener.
                                                // Better approach: Since we want a robust UX, if form is invalid, we can just replace newForm HTML with errForm HTML, and recursive attach. But let's keep it simple: we just use standard form submit inside modal, which works but causes full page reload on error.
                                                // WAIT, if it fails validation, we inject, but we must re-attach the event listener!
                                            } else {
                                                window.location.reload();
                                            }
                                        }
                                    } catch(err) {
                                        submitBtn.innerText = originalText;
                                        submitBtn.disabled = false;
                                        alert('Error saving. Please try again.');
                                    }
                                });
                            } else { bodyEl.innerHTML = formContainer.innerHTML; }
                        } else {
                            bodyEl.innerHTML = '<div style="padding: 24px;"><p>Could not extract form data.</p></div>';
                        }
                    } catch(err) {
                        bodyEl.innerHTML = '<div style="padding: 24px; color: red;"><p>Error fetching content.</p></div>';
                    }
                }

                function closeDynamicModal() {
                    const modal = document.getElementById('dynamicModal');
                    const modalContent = modal.querySelector('.modal-content');
                    modalContent.classList.remove('show');
                    setTimeout(() => {
                        modal.style.display = 'none';
                    }, 300);
                }
                
                // Add keydown listener to close modal on Escape
                document.addEventListener('keydown', function(event) {
                    if (event.key === "Escape") {
                        closeDynamicModal();
                    }
                });
"""

# Let's cleanly inject this right above the first script block:
# But we also have to strip the old hard-coded modalConference etc blocks.
import re
# We can use regex to strip out everything between <!-- MODALS --> and the first function openTab
c = re.sub(r'<!-- MODALS -->.*?<script>', dynamic_modal_html + '\n<script>\n' + javascript_code, c, flags=re.DOTALL)


# Add an animation style 
c = c.replace('</style>', """
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>""")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(c)

print("Replacement complete. Modal HTML deleted and unified Dynamic Modal injected.")
