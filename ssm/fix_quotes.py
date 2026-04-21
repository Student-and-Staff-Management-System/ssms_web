file_path = r'c:\Users\sachi\OneDrive\Desktop\nojinx\ssm\students\scholars_views.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the escaped quotes that were accidentally added
content = content.replace('\\"', '"')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed escaped quotes in scholars_views.py")
