import base64
from pathlib import Path

from gmail_service import get_gmail_service


SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def walk_parts(payload):
    """Recursively go through all MIME parts in a Gmail message."""
    yield payload

    for part in payload.get("parts", []) or []:
        yield from walk_parts(part)


def is_supported_cv(filename, mime_type):
    """Check whether an attachment is a PDF or DOCX file."""
    extension = Path(filename).suffix.lower()

    return (
        mime_type in SUPPORTED_MIME_TYPES
        or extension in SUPPORTED_EXTENSIONS
    )


def get_cv_attachments(message):
    """Return metadata for supported PDF and DOCX attachments."""
    payload = message.get("payload", {})
    attachments = []

    for part in walk_parts(payload):
        filename = part.get("filename", "")
        mime_type = part.get("mimeType", "")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")

        if not filename or not attachment_id:
            continue

        if not is_supported_cv(filename, mime_type):
            continue

        attachments.append({
            "filename": filename,
            "mime_type": mime_type,
            "attachment_id": attachment_id,
        })

    return attachments


def download_attachment(message_id, attachment_id):
    """Download and decode an attachment from Gmail."""
    service = get_gmail_service()

    response = (
        service.users()
        .messages()
        .attachments()
        .get(
            userId="me",
            messageId=message_id,
            id=attachment_id,
        )
        .execute()
    )

    encoded_data = response.get("data")

    if not encoded_data:
        raise ValueError("Gmail returned no attachment data.")

    encoded_data += "=" * (-len(encoded_data) % 4)

    return base64.urlsafe_b64decode(encoded_data)


def save_attachment(message_id, attachment, output_dir="matched_cvs_temp"):
    """Download an attachment and save it temporarily."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    filename = Path(attachment["filename"]).name
    save_path = output_path / filename

    if save_path.exists():
        print(f"File already exists, skipping: {save_path}")
        return save_path

    file_bytes = download_attachment(
        message_id,
        attachment["attachment_id"],
    )

    save_path.write_bytes(file_bytes)
    print(f"Downloaded to: {save_path}")

    return save_path