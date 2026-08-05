import SwiftUI

/// Recreations of the three transient-feedback shapes Apple ships in its own
/// apps, plus the non-toast alternative the HIG actually prefers.
struct PatternsView: View {
    @Environment(ToastCenter.self) private var center
    @State private var syncStatus = "Updated just now"
    @State private var sendUndone = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    patternRow(
                        title: "Center HUD",
                        source: "Apple Music — “Added to Library”",
                        detail: "Non-interactive, ~1.5 s, pure confirmation of a state you can verify elsewhere."
                    ) {
                        center.show(.hud("Added to Library", symbol: "checkmark.circle.fill"))
                    }

                    patternRow(
                        title: "Top banner",
                        source: "System — “Pasted from Safari”, AirPods connected",
                        detail: "Capsule in the status region. Passive, out of the content area."
                    ) {
                        center.show(
                            Toast(
                                message: "Pasted from Safari",
                                symbol: "doc.on.clipboard",
                                placement: .topBanner
                            )
                        )
                    }

                    patternRow(
                        title: "Bottom snackbar with Undo",
                        source: "Mail — “Undo Send” (iOS 16+)",
                        detail: "The only Apple toast with an action, and the action is only ever Undo. Runs longer (~5 s) so the button is reachable."
                    ) {
                        sendUndone = false
                        center.show(
                            .undoable("Message sent", symbol: "paperplane.fill") {
                                sendUndone = true
                                center.show(.hud("Send undone", symbol: "arrow.uturn.backward.circle.fill"))
                            }
                        )
                    }
                } header: {
                    Text("What Apple ships")
                } footer: {
                    Text("All three: haptic-paired, one at a time, never the only record of the event.")
                }

                Section {
                    Button {
                        refresh()
                    } label: {
                        Label("Check for updates", systemImage: "arrow.clockwise")
                    }
                } header: {
                    Text("The HIG-preferred alternative")
                } footer: {
                    Text("\(syncStatus)\n\nMail doesn’t toast “Inbox refreshed” — it puts status in the toolbar, in context, with no timer. Watch the line above after tapping.")
                }
            }
            .navigationTitle("Toast Lab")
        }
    }

    private func patternRow(
        title: String,
        source: String,
        detail: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.body.weight(.semibold))
                Text(source)
                    .font(.subheadline)
                    .foregroundStyle(.tint)
                Text(detail)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 2)
        }
        .buttonStyle(.plain)
    }

    private func refresh() {
        Task {
            syncStatus = "Checking for updates…"
            try? await Task.sleep(for: .seconds(1.5))
            syncStatus = "Updated just now"
        }
    }
}
