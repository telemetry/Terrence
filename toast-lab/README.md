# Toast Lab

A small SwiftUI app for testing snackbar/toast patterns against what Apple
actually ships, built as research for in-app transient feedback in a banking
context. Apple has no toast component — not in the HIG, not in UIKit or
SwiftUI — but iOS itself uses three distinct transient-feedback shapes, and
this app recreates all of them so you can feel out timing, placement, and
where the pattern breaks down.

## Running it

`ToastLab.swiftpm` is an app playground package — no `.xcodeproj` needed:

- **Mac:** open `ToastLab.swiftpm` in Xcode 15 or later, pick an iOS 17+
  simulator, run.
- **iPad:** open it in Swift Playgrounds 4.4+ and run it directly on device
  (the only way to feel the haptics).

## What's inside

**Patterns tab** — recreations of Apple's own transient feedback:

| Pattern | Apple's version | Traits |
|---|---|---|
| Center HUD | Apple Music "Added to Library" | ~1.5 s, non-interactive, pure confirmation |
| Top banner | System "Pasted from…", AirPods connected | Capsule in the status region, passive |
| Bottom snackbar | Mail "Undo Send" (iOS 16+) | The only one with an action — and it's only ever Undo |

Plus the alternative the HIG actually prefers: in-context status text
(Mail's "Updated just now" toolbar line), with no timer at all.

**Banking tab** — where the line sits for a banking app:

- *Toast-appropriate:* copy IBAN, freeze/unfreeze card — low stakes,
  reversible, and the card UI visibly changes state so the toast is
  redundant confirmation, not the record.
- *Not toast-appropriate:* sending money. The transfer flow has two endings —
  a persistent confirmation screen with a reference number (correct), and a
  toast-only ending (anti-pattern) so you can feel what's missing two
  seconds later.

**Lab tab** — knobs for message, placement, duration (1–8 s), symbol, and
Undo, to tune what feels right.

## Design rules encoded in `Toast.swift` / `ToastViews.swift`

1. One toast at a time — new ones replace, never stack or queue.
2. Passive by default; the only permitted action is Undo, and toasts
   carrying it run longer (~5 s vs ~2 s).
3. Every toast pairs with a haptic (`.sensoryFeedback`) and a VoiceOver
   announcement (`AccessibilityNotification.Announcement`) — a transient
   view is invisible to assistive tech otherwise.
4. Reduce Motion swaps slide/scale transitions for crossfades.
5. Swipe toward the nearest edge dismisses; the host lives at the app root
   so toasts survive navigation.
6. A toast is never the only record of anything that matters — money
   movement gets a persistent confirmation screen.
