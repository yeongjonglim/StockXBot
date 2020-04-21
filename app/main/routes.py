from flask import render_template, redirect, url_for
from app.main import bp

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html', title='Home')

@bp.route('/<ann_id>', methods=['GET'])
def link_shortner(ann_id):
    target_url = 'https://disclosure.bursamalaysia.com/FileAccess/viewHtml?e='+ann_id
    return redirect(target_url)
