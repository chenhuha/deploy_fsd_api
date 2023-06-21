# docs.py

import os
import markdown
from flask import render_template
from markdown.extensions.extra import ExtraExtension


def get_markdown_files(root_folder):
    markdown_files = []
    for folder in ['deploy', 'upgrade', 'extension']:
        folder_path = os.path.join(root_folder, folder)
        files = [file for file in os.listdir(folder_path) if file.endswith('.md')]
        markdown_files.extend([(folder, file) for file in files])
    return sorted(markdown_files)

def register_docs_routes(app):
    @app.route('/docs')
    def index():
        markdown_files = get_markdown_files('docs')
        return render_template('index.html', files=markdown_files)

    @app.route('/docs/<folder>/<filename>')
    def file(folder, filename):
        file_path = os.path.join('docs', folder, filename)
        with open(file_path, 'r') as f:
            content = f.read()
        extensions = [ExtraExtension()]
        html = markdown.markdown(content, extensions=extensions)
        return render_template('file.html', filename=filename, html=html)
