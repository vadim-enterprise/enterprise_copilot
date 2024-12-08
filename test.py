from pathlib import Path
doc_path = "/home/ubuntu/django_project/text.docx"
if not Path(doc_path).exists():
    raise FileNotFoundError(f"Document not found at {doc_path}")
else:
    print('test')