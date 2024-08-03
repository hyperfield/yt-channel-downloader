from py2exe.runtime import Runtime

# Define options within a dictionary or directly as parameters
options = {
    'script': 'main.py',
    'dest_base': 'ytchandl',
    'icon_resources': [(1, "icon.ico")],
    'other_resources': [(24, 1, open("icon.png", "rb").read())],
    'bundle_files': 1,
    'compressed': True
}

# Initialize Runtime with options
app = Runtime(options)

# Check for command to freeze
if len(sys.argv) >= 2 and sys.argv[1] == 'freeze':
    app.freeze()
