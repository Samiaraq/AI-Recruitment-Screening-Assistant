from googleapiclient.discovery import build
from gmail_auth import get_credentials


def get_gmail_service() :
    """Create and return the Gmail API service."""
    credentials = get_credentials()
    return build("gmail", "v1", credentials=credentials)
