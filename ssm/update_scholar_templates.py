import os
import re

portfolio_path = "c:\\Users\\sachi\\OneDrive\\Desktop\\nojinx\\ssm\\templates\\scholars\\scholar_portfolio.html"
form_path = "c:\\Users\\sachi\\OneDrive\\Desktop\\nojinx\\ssm\\templates\\scholars\\scholar_portfolio_form.html"

# Edit portfolio
with open(portfolio_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Update back link
html = html.replace("{% url 'staffs:staff_profile' %}", "{% url 'scholar_dashboard' %}")
html = html.replace("<!-- ═══ QUALIFICATIONS TAB ═══ -->", "<div style=\"display:none;\">")
html = html.replace("<!-- ═══ AWARDS & MORE TAB ═══ -->", "</div>\n        <!-- ═══ AWARDS & MORE TAB ═══ -->")
html = html.replace("<!-- Students Guided -->", "<div style=\"display:none;\">")
html = html.replace("<!-- Seminars (Legacy) -->", "</div>\n            <!-- Seminars (Legacy) -->")

# Replace Add URLS
html = html.replace("{% url \"staffs:portfolio_add_conference\" %}", "{% url 'scholar_portfolio_add' 'conference' %}")
html = html.replace("{% url \"staffs:portfolio_add_journal\" %}", "{% url 'scholar_portfolio_add' 'journal' %}")
html = html.replace("{% url \"staffs:portfolio_add_book\" %}", "{% url 'scholar_portfolio_add' 'book' %}")
html = html.replace("{% url \"staffs:portfolio_add_award\" %}", "{% url 'scholar_portfolio_add' 'award' %}")
html = html.replace("{% url \"staffs:portfolio_add_seminar\" %}", "{% url 'scholar_portfolio_add' 'seminar' %}")

# Replace Edit URLS
html = html.replace("{% url \"staffs:portfolio_edit_conference\" c.pk %}", "{% url 'scholar_portfolio_edit' 'conference' c.pk %}")
html = html.replace("{% url \"staffs:portfolio_edit_journal\" j.pk %}", "{% url 'scholar_portfolio_edit' 'journal' j.pk %}")
html = html.replace("{% url \"staffs:portfolio_edit_book\" b.pk %}", "{% url 'scholar_portfolio_edit' 'book' b.pk %}")
html = html.replace("{% url \"staffs:portfolio_edit_award\" a.pk %}", "{% url 'scholar_portfolio_edit' 'award' a.pk %}")
html = html.replace("{% url \"staffs:portfolio_edit_seminar\" s.pk %}", "{% url 'scholar_portfolio_edit' 'seminar' s.pk %}")

# Replace Delete URLS
html = html.replace("{% url 'staffs:portfolio_delete_entry' 'conference' c.pk %}", "{% url 'scholar_portfolio_delete' 'conference' c.pk %}")
html = html.replace("{% url 'staffs:portfolio_delete_entry' 'journal' j.pk %}", "{% url 'scholar_portfolio_delete' 'journal' j.pk %}")
html = html.replace("{% url 'staffs:portfolio_delete_entry' 'book' b.pk %}", "{% url 'scholar_portfolio_delete' 'book' b.pk %}")
html = html.replace("{% url 'staffs:portfolio_delete_entry' 'award' a.pk %}", "{% url 'scholar_portfolio_delete' 'award' a.pk %}")
html = html.replace("{% url 'staffs:portfolio_delete_entry' 'seminar' s.pk %}", "{% url 'scholar_portfolio_delete' 'seminar' s.pk %}")

# Redirect on Success javascript update
html = html.replace("window.location.href = '/staffs/profile/portfolio/#' + activeTab;", "window.location.href = '/students/scholar/portfolio/#' + activeTab;")

with open(portfolio_path, 'w', encoding='utf-8') as f:
    f.write(html)
    
# Edit forms
with open(form_path, 'r', encoding='utf-8') as f:
    f_html = f.read()

# Add a Staff Dropdown field BEFORE the main fields container, right inside the form tags.
staff_dropdown = """
    <div class="form-group" style="background:#eef4f4; padding:15px; border-radius:10px; margin-bottom:20px; border:1px solid #c2dcdc;">
        <label for="staff_id" style="color:#0f3f3f; font-weight:700;">★ Tag Faculty Member (Author/Supervisor) <span style="color:red">*</span></label>
        <select name="staff_id" id="staff_id" required style="font-weight:600; background:#fff; border-color:#82a9a9;">
            <option value="">-- Select Faculty Co-Author --</option>
            {% for staff in staff_list %}
            <option value="{{ staff.staff_id }}" {% if item and item.staff.staff_id == staff.staff_id %}selected{% endif %}>{{ staff.name }} ({{ staff.staff_id }})</option>
            {% endfor %}
        </select>
        <div class="form-help" style="color:#4a6b69;">This accomplishment will automatically reflect in the selected faculty member's profile as well.</div>
    </div>
"""

f_html = f_html.replace("{% csrf_token %}", "{% csrf_token %}\n" + staff_dropdown)
f_html = f_html.replace("btn-cancel\" href=\"{% url 'staffs:staff_portfolio' %}\"", "btn-cancel\" href=\"{% url 'scholar_portfolio' %}\"")

with open(form_path, 'w', encoding='utf-8') as f:
    f.write(f_html)

print("Template updates completed successfully.")
