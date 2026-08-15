from __future__ import annotations

from expandr.models import Folder, Library, Settings, Snippet, TriggerMode, new_id


def _long_email() -> str:
    paragraph = (
        "This block is intentionally long. Text Blaze Free stops a single snippet "
        "at 2,500 characters and stops you at 20 snippets. Expandr does not. "
        "Use this for contracts, onboarding emails, runbooks, or anything you "
        "actually need to keep in one place.\n\n"
    )
    return (
        "Hi {formtext: name=name; default=there},\n\n"
        + (paragraph * 18)
        + "Thanks,\n{formtext: name=sender; default=Me}\n"
    )


def default_library() -> Library:
    personal = Folder(id=new_id(), name="Personal", trigger=TriggerMode.WORD_START)
    personal.snippets = [
        Snippet(
            id=new_id(),
            label="Thank you",
            shortcut="/ty",
            content="Thank you for your email — I will follow up shortly.",
        ),
        Snippet(
            id=new_id(),
            label="Signature",
            shortcut="/sig",
            content="Best regards,\n{formtext: name=name; default=Your Name}",
        ),
        Snippet(
            id=new_id(),
            label="Today's date",
            shortcut="/date",
            content="{time: YYYY-MM-DD}",
        ),
        Snippet(
            id=new_id(),
            label="Clipboard paste",
            shortcut="/clip",
            content="{clipboard}",
        ),
        Snippet(
            id=new_id(),
            label="Meeting notes",
            shortcut="/meet",
            content=(
                "Meeting: {formtext: name=title; default=Weekly sync}\n"
                "Date: {formdate: YYYY-MM-DD; name=when}\n"
                "Attendees: {formparagraph: name=people}\n\n"
                "Notes:\n- \n\n"
                "Next steps:\n- "
            ),
        ),
        Snippet(
            id=new_id(),
            label="Long email (over 2,500 characters)",
            shortcut="/long",
            content=_long_email(),
        ),
    ]
    return Library(folders=[personal], settings=Settings())
