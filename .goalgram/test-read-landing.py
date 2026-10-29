#!/usr/bin/env python3
"""Exercise the production animation-landing callback without building TelegramUI."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'submodules/TelegramUI/Sources/CoreListChatHistoryBackend.swift').read_text()
start = source.index('Queue.mainQueue().after(transition.duration * UIView.animationDurationFactor(), { [weak self] in')
end = source.index('\n                })', start) + len('\n                })')
callback = source[start:end]

# The callback is production Swift. The small host models the two distinct publications:
# range changes do not publish read indices; the offset observer samples presented messages.
harness = r'''
import Foundation
struct Transition { var duration: Double = 0.3; static let immediate = Transition(duration: 0) }
enum Geometry { case presented, settled }
enum UIView { static func animationDurationFactor() -> Double { 1 } }
final class Queue {
    static let shared = Queue()
    var pending: (() -> Void)?
    static func mainQueue() -> Queue { shared }
    func after(_ delay: Double, _ callback: @escaping () -> Void) { pending = callback }
    func land() { let callback = pending; pending = nil; callback?() }
}
final class Backend {
    var presentedMessage = 0
    var readMessage = 0
    var canRead = true
    var rangeUpdates = 0
    var offsetUpdates = 0
    func updateVisibleItemRange(force: Bool) { rangeUpdates += 1 }
    func updateVisibleContentOffset(transition: Transition, geometry: Geometry) {
        precondition(geometry == .presented, "never mark the animation destination as seen")
        offsetUpdates += 1
        if canRead { readMessage = max(readMessage, presentedMessage) }
    }
    func animate() {
        let transition = Transition()
        CALLBACK
    }
}
func check(_ condition: Bool, _ label: String) {
    if !condition { print("FAIL: \(label)"); exit(1) }
}
let backend = Backend()
backend.animate()
check(backend.readMessage == 0, "offscreen destination is not read before landing")
backend.presentedMessage = 42
Queue.shared.land()
check(backend.rangeUpdates == 1, "landed range is published")
check(backend.readMessage == 42, "landed visible message reaches read observer without user scroll")
backend.canRead = false
backend.animate()
backend.presentedMessage = 43
Queue.shared.land()
check(backend.readMessage == 42, "existing read gate remains authoritative")
backend.canRead = true
backend.animate()
backend.presentedMessage = 44
Queue.shared.land()
check(backend.readMessage == 44, "later arrivals advance the read watermark")
var released: Backend? = Backend()
released?.animate()
weak var witness = released
released = nil
check(witness == nil, "scheduled callback does not retain the history")
Queue.shared.land()
print("PASS: production landing callback republishes presented visibility; read gates and weak lifetime preserved")
'''.replace('CALLBACK', callback)
with tempfile.TemporaryDirectory(prefix='goalgram-read-landing-') as temp:
    path = Path(temp)
    (path / 'main.swift').write_text(harness)
    subprocess.run(['xcrun', 'swiftc', str(path / 'main.swift'), '-o', str(path / 'tests')], check=True)
    subprocess.run([str(path / 'tests')], check=True)
