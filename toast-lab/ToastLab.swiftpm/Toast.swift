import SwiftUI
import Observation
import Accessibility

/// A single transient message. Three placements, mirroring the three shapes
/// Apple actually ships:
/// - `.topBanner`    — system-style capsule ("Pasted from…", AirPods connected)
/// - `.centerHUD`    — Apple Music-style confirmation ("Added to Library")
/// - `.bottomSnackbar` — Mail-style timed bar, the only one allowed an action (Undo)
struct Toast: Identifiable, Equatable {
    enum Placement: String, CaseIterable, Identifiable {
        case topBanner = "Top banner"
        case centerHUD = "Center HUD"
        case bottomSnackbar = "Bottom snackbar"

        var id: String { rawValue }
    }

    let id = UUID()
    var message: String
    var symbol: String? = nil
    var placement: Placement = .bottomSnackbar
    var duration: Duration = .seconds(2)
    var haptic: SensoryFeedback? = .success
    var actionLabel: String? = nil
    var action: (() -> Void)? = nil

    static func == (lhs: Toast, rhs: Toast) -> Bool { lhs.id == rhs.id }
}

@Observable
final class ToastCenter {
    private(set) var current: Toast?

    /// Replaces any visible toast — one at a time, never stacked or queued,
    /// matching system behavior.
    func show(_ toast: Toast) {
        current = toast
        // VoiceOver never "sees" a transient view unless we announce it.
        AccessibilityNotification.Announcement(toast.message).post()
    }

    /// Dismisses only if `toast` is still the visible one, so a stale
    /// auto-dismiss timer can't kill a newer toast.
    func dismiss(_ toast: Toast? = nil) {
        if let toast, toast.id != current?.id { return }
        current = nil
    }
}

// Convenience factories for the recurring banking cases.
extension Toast {
    static func copied(_ what: String) -> Toast {
        Toast(
            message: "\(what) copied",
            symbol: "doc.on.doc.fill",
            placement: .topBanner,
            duration: .seconds(2)
        )
    }

    static func hud(_ message: String, symbol: String = "checkmark.circle.fill") -> Toast {
        Toast(
            message: message,
            symbol: symbol,
            placement: .centerHUD,
            duration: .seconds(1.6)
        )
    }

    static func undoable(_ message: String, symbol: String? = nil, undo: @escaping () -> Void) -> Toast {
        Toast(
            message: message,
            symbol: symbol,
            placement: .bottomSnackbar,
            // Longer because it carries an action the user may want to reach.
            duration: .seconds(5),
            actionLabel: "Undo",
            action: undo
        )
    }
}
