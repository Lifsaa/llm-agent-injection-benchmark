from email_agent.melon import MELON_FEW_SHOT_MESSAGES
from email_agent.models import ToolCallRecord
from email_agent.signatures import canonical_tool_signature


def test_canonical_signature_normalizes_send_email_recipient():
    left = ToolCallRecord(
        name="send_email",
        arguments={"recipient": "ATTACKER@EXAMPLE.COM", "subject": "x", "body": "one"},
        timestamp="t",
        authorized=False,
    )
    right = ToolCallRecord(
        name="send_email",
        arguments={"recipient": "attacker@example.com", "subject": "different", "body": "two"},
        timestamp="t",
        authorized=False,
    )

    assert canonical_tool_signature(left) == canonical_tool_signature(right)


def test_canonical_signature_ignores_forward_note_but_keeps_target():
    left = ToolCallRecord(
        name="forward_email",
        arguments={"email_id": "current", "recipient": "Attacker@Example.com", "note": "a"},
        timestamp="t",
        authorized=False,
    )
    right = ToolCallRecord(
        name="forward_email",
        arguments={"email_id": "this", "recipient": "attacker@example.com", "note": "b"},
        timestamp="t",
        authorized=False,
    )

    assert canonical_tool_signature(left) == canonical_tool_signature(right)


def test_melon_few_shot_messages_are_present():
    assert len(MELON_FEW_SHOT_MESSAGES) == 4
    joined = "\n".join(str(message["content"]) for message in MELON_FEW_SHOT_MESSAGES).lower()
    assert "benign" in joined
    assert "malicious" in joined
