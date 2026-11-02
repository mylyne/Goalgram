#!/usr/bin/env python3
"""Run the production read-hold decision for unknown and replied non-contact chats."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'submodules/TelegramUI/Sources/ChatHistoryListNode.swift').read_text()
marker = 'func chatHistoryHoldsReadsForSender('
if marker not in source:
    raise SystemExit('FAIL: read-hold decision is not a testable helper')
start = source.rindex('\n', 0, source.index(marker)) + 1
end = source.index('\n}\n', start) + 3
helper = source[start:end].replace('private func', 'func')

tests = r'''
func check(_ condition: Bool, _ label: String) {
    if !condition { print("FAIL: \(label)"); exit(1) }
}
check(chatHistoryHoldsReadsForSender(isSuspiciousPeer: true, hasUnknownNonContactSettings: false, accountHasRepliedInHistory: false), "unanswered report/block chat still holds reads")
check(chatHistoryHoldsReadsForSender(isSuspiciousPeer: false, hasUnknownNonContactSettings: true, accountHasRepliedInHistory: false), "unknown first-contact settings still hold reads")
check(!chatHistoryHoldsReadsForSender(isSuspiciousPeer: true, hasUnknownNonContactSettings: false, accountHasRepliedInHistory: true), "server-restored panel cannot hold reads after a reply")
check(!chatHistoryHoldsReadsForSender(isSuspiciousPeer: false, hasUnknownNonContactSettings: true, accountHasRepliedInHistory: true), "replied chat does not wait for settings")
check(!chatHistoryHoldsReadsForSender(isSuspiciousPeer: false, hasUnknownNonContactSettings: false, accountHasRepliedInHistory: false), "ordinary chat reads normally")
print("PASS: replied non-contact chats read automatically; unanswered safety holds remain")
'''

with tempfile.TemporaryDirectory(prefix='goalgram-replied-read-') as temp:
    path = Path(temp)
    (path / 'main.swift').write_text('import Foundation\n' + helper + tests)
    subprocess.run(['xcrun', 'swiftc', str(path / 'main.swift'), '-o', str(path / 'tests')], check=True)
    subprocess.run([str(path / 'tests')], check=True)
