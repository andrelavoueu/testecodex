from __future__ import annotations

import imaplib
import os
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from email.policy import default


@dataclass
class SourceMessage:
    source_id: str
    body: str


def _extract_plain_text(msg: Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get("Content-Disposition", "")
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""

    payload = msg.get_payload(decode=True)
    if payload is None:
        text_payload = msg.get_payload()
        return text_payload if isinstance(text_payload, str) else ""

    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


class ImapEmailSource:
    def __init__(
        self,
        account_email: str,
        imap_server: str,
        password_env: str,
        folder: str = "INBOX",
        search_criteria: str = "UNSEEN",
    ) -> None:
        self.account_email = account_email
        self.imap_server = imap_server
        self.password_env = password_env
        self.folder = folder
        self.search_criteria = search_criteria

    def fetch_messages(self) -> list[SourceMessage]:
        password = os.getenv(self.password_env)
        if not password:
            raise RuntimeError(
                f"Variável de ambiente não definida para senha: {self.password_env}"
            )

        with imaplib.IMAP4_SSL(self.imap_server) as mail:
            mail.login(self.account_email, password)
            status, _ = mail.select(self.folder)
            if status != "OK":
                raise RuntimeError(f"Falha ao abrir pasta IMAP '{self.folder}'")

            status, data = mail.search(None, self.search_criteria)
            if status != "OK":
                raise RuntimeError("Falha na busca de e-mails")

            message_ids = data[0].split()
            messages: list[SourceMessage] = []

            for raw_msg_id in message_ids:
                msg_id = raw_msg_id.decode("utf-8", errors="ignore")
                fetch_status, raw_data = mail.fetch(raw_msg_id, "(RFC822)")
                if fetch_status != "OK":
                    continue

                raw_email = raw_data[0][1]
                parsed = message_from_bytes(raw_email, policy=default)
                body = _extract_plain_text(parsed)

                source_id = f"{self.account_email}:{msg_id}"
                messages.append(SourceMessage(source_id=source_id, body=body))

            return messages
