from flask import send_from_directory, current_app as app

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.png', mimetype='image/x-icon') 