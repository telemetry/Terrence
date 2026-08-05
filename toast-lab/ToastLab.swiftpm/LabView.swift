import SwiftUI

/// Knobs for feeling out placement, duration, and action affordance.
struct LabView: View {
    @Environment(ToastCenter.self) private var center
    @State private var message = "Account nickname updated"
    @State private var placement: Toast.Placement = .bottomSnackbar
    @State private var seconds = 2.0
    @State private var showSymbol = true
    @State private var withUndo = false
    @State private var undoTaps = 0

    var body: some View {
        NavigationStack {
            Form {
                Section("Content") {
                    TextField("Message", text: $message)
                    Toggle("Symbol", isOn: $showSymbol)
                    Toggle("Undo action", isOn: $withUndo)
                        .disabled(placement != .bottomSnackbar)
                }

                Section("Timing & placement") {
                    Picker("Placement", selection: $placement) {
                        ForEach(Toast.Placement.allCases) { placement in
                            Text(placement.rawValue).tag(placement)
                        }
                    }
                    LabeledContent("Duration", value: seconds.formatted(.number.precision(.fractionLength(1))) + " s")
                    Slider(value: $seconds, in: 1...8, step: 0.5)
                }

                Section {
                    Button("Show toast") {
                        center.show(
                            Toast(
                                message: message,
                                symbol: showSymbol ? "checkmark.circle.fill" : nil,
                                placement: placement,
                                duration: .seconds(seconds),
                                actionLabel: canUndo ? "Undo" : nil,
                                action: canUndo ? { undoTaps += 1 } : nil
                            )
                        )
                    }
                    .font(.body.weight(.semibold))
                } footer: {
                    Text(footerText)
                }
            }
            .navigationTitle("Lab")
        }
    }

    private var canUndo: Bool {
        withUndo && placement == .bottomSnackbar
    }

    private var footerText: String {
        var lines = [
            "Swipe the toast toward its edge to dismiss. Enable VoiceOver or Reduce Motion in Settings to hear the announcement / see the crossfade fallback."
        ]
        if undoTaps > 0 {
            lines.append("Undo tapped \(undoTaps)×.")
        }
        return lines.joined(separator: "\n")
    }
}
