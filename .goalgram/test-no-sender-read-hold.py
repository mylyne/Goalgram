#!/usr/bin/env python3
"""13.2 reads suspicious and unknown non-contact chats normally; keep that from regressing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
for forbidden in ['holdsReadsForSender', 'chatHistoryHoldsReadsForSender', 'canMarkReadValue']:
    if forbidden in source:
        raise SystemExit('FAIL: sender read hold returned: ' + forbidden)
if 'combineLatest(self.maxVisibleIncomingMessageIndex.get(), self.canReadHistory.get())' not in source:
    raise SystemExit('FAIL: read history no longer follows visibility and canReadHistory alone')
print('PASS: visible messages are read through canReadHistory alone, with no sender hold')
