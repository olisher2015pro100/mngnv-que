Project preview & restore

Files created:
- index.html.bak — backup copy of `index.html` at time of update

Quick preview (Windows, in project folder):

1. Start a simple HTTP server (Python 3):

```powershell
python -m http.server 8000
```

2. Open in browser: http://localhost:8000/index.html

Restore original file (PowerShell):

```powershell
Copy-Item -Path index.html.bak -Destination index.html -Force
```

Notes:
- Make sure `tshirt1.jpg`, `tshirt2.jpg`, `tshirt3.jpg` are in the same folder as `index.html`.
- If you want, I can also create a git repo and commit these changes for safer versioning.
