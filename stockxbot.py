from app import create_app, db
from app.models import Company, Announcement, TelegramSubscriber, Subscribe

app = create_app()

# Generate GOOGLE_APPLICATION_CREDENTIALS from environment variables
import os
import json
keys = {
    "type": os.environ.get("TYPE"),
    "project_id": os.environ.get("PROJECT_ID"),
    "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
    "private_key": os.environ.get("PRIVATE_KEY").encode('latin1').decode('unicode_escape'),
    "client_email": os.environ.get("CLIENT_EMAIL"),
    "client_id": os.environ.get("CLIENT_ID"),
    "auth_uri": os.environ.get("AUTH_URI"),
    "token_uri": os.environ.get("TOKEN_URI"),
    "auth_provider_x509_cert_url": os.environ.get("AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.environ.get("CLIENT_X509_CERT_URL")
}

with open(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"), "w") as write_file:
    json.dump(keys, write_file, indent=2)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Company': Company, 'Announcement': Announcement, 'TelegramSubscriber': TelegramSubscriber, 'Subscribe': Subscribe}
