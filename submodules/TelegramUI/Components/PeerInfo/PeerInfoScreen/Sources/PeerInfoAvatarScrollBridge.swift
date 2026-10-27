import UIKit

/// The header is a sibling of the scroll view. On either Duo display its
/// expanded photo can fill the viewport, leaving no scroll-view surface to drag.
/// Keep native scroll physics, but let that recognizer also see header touches.
final class PeerInfoAvatarScrollBridge: NSObject, UIGestureRecognizerDelegate {
    private weak var avatarPan: UIPanGestureRecognizer?
    private weak var previousAvatarDelegate: UIGestureRecognizerDelegate?

    func update(container: UIView, scrollView: UIScrollView, avatarView: UIView, enabled: Bool) {
        let target = enabled ? container : scrollView
        if scrollView.panGestureRecognizer.view !== target {
            target.addGestureRecognizer(scrollView.panGestureRecognizer)
        }
        if enabled {
            if let pan = avatarView.gestureRecognizers?.compactMap({ $0 as? UIPanGestureRecognizer }).first,
               pan !== self.avatarPan {
                self.restoreAvatarDelegate()
                self.avatarPan = pan
                self.previousAvatarDelegate = pan.delegate
                pan.delegate = self
            }
        } else {
            self.restoreAvatarDelegate()
        }
    }

    private func restoreAvatarDelegate() {
        if let pan = self.avatarPan, pan.delegate === self {
            pan.delegate = self.previousAvatarDelegate
        }
        self.avatarPan = nil
        self.previousAvatarDelegate = nil
    }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        guard let pan = gestureRecognizer as? UIPanGestureRecognizer else { return true }
        let velocity = pan.velocity(in: pan.view)
        return abs(velocity.x) > abs(velocity.y)
    }
}
