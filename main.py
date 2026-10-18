
from gmail_service import get_gmail_service
from gmail_reader import search_emails, get_message
from attachment_downloader import get_cv_attachments, save_attachment
from cv_text_extractor import extract_cv_text
from job_match import check_cv_match
import hashlib


def process_cvs(job_description, number_of_cvs=None):
    get_gmail_service()

    processed_cvs = set()
    results = []
    errors = []

    emails = search_emails(
        "has:attachment {filename:pdf filename:docx}",
        max_results=100
    )

    print(f"Found {len(emails)} emails")

    for email in emails:
        message_id = email["id"]

        try:
            message = get_message(message_id)
            attachments = get_cv_attachments(message)

            for attachment in attachments:
                if number_of_cvs is not None and len(results) >= number_of_cvs:
                    return {"results": results, "errors": errors}

                try:
                    file_path = save_attachment(message_id, attachment)
                    file_hash = hashlib.sha256(
                        file_path.read_bytes()
                    ).hexdigest()

                    if file_hash in processed_cvs:
                        continue

                    cv_text = extract_cv_text(str(file_path))

                    if not cv_text.strip():
                        processed_cvs.add(file_hash)
                        errors.append({
                            "filename": attachment["filename"],
                            "error": "No text could be extracted"
                        })
                        continue

                    result = check_cv_match(job_description, cv_text)

                    if result is None:
                        errors.append({
                            "filename": attachment["filename"],
                            "error": "CV matching failed"
                        })
                        continue

                    processed_cvs.add(file_hash)

                    results.append({
                        "filename": attachment["filename"],
                        "result": result
                    })

                except Exception as error:
                    errors.append({
                        "filename": attachment.get("filename", "Unknown"),
                        "error": str(error)
                    })

        except Exception as error:
            errors.append({
                "email_id": message_id,
                "error": str(error)
            })

    return {"results": results, "errors": errors}


def main():
    job_description = open(
        "job_description.txt", encoding="utf-8"
    ).read()

    output = process_cvs(job_description)

    for candidate in output["results"]:
        print(f"\nCV: {candidate['filename']}")
        print(candidate["result"])

    for error in output["errors"]:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
