import SwiftUI

struct TransferReceipt: Identifiable {
    let id = UUID()
    let recipient: String
    let amount: String

    var reference: String {
        String(id.uuidString.prefix(8))
    }
}

/// The same transfer with two endings: a persistent confirmation screen
/// (correct) and a toast-only ending (anti-pattern) — run both and compare
/// what you're left with two seconds later.
struct TransferView: View {
    @Environment(ToastCenter.self) private var center
    @State private var recipient = "Jordan Reyes"
    @State private var amount = "250.00"
    @State private var receipt: TransferReceipt?

    private let recipients = ["Jordan Reyes", "Sam Okafor", "Priya Nair"]

    var body: some View {
        Form {
            Section("Transfer") {
                Picker("To", selection: $recipient) {
                    ForEach(recipients, id: \.self, content: Text.init)
                }
                LabeledContent("Amount") {
                    TextField("0.00", text: $amount)
                        .keyboardType(.decimalPad)
                        .multilineTextAlignment(.trailing)
                }
            }

            Section {
                Button("Send — proper confirmation") {
                    receipt = TransferReceipt(recipient: recipient, amount: amount)
                }
                .font(.body.weight(.semibold))
            } footer: {
                Text("Full-screen result with a reference number and an explicit Done. The user keeps evidence; VoiceOver users get a screen, not a 2-second window.")
            }

            Section {
                Button("Send — toast only (anti-pattern)", role: .destructive) {
                    center.show(.hud("Transfer sent", symbol: "paperplane.circle.fill"))
                }
            } footer: {
                Text("Feels slick, but: no reference number, no persistent record, gone before VoiceOver users perceive it, and it fails WCAG 2.2.1 (Enough Time). Never end a money movement this way.")
            }
        }
        .navigationTitle("Send money")
        .fullScreenCover(item: $receipt) { receipt in
            ConfirmationView(receipt: receipt)
        }
    }
}

private struct ConfirmationView: View {
    @Environment(\.dismiss) private var dismiss
    let receipt: TransferReceipt

    var body: some View {
        VStack(spacing: 24) {
            Spacer()

            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 72))
                .foregroundStyle(.green)

            VStack(spacing: 8) {
                Text("£\(receipt.amount) sent")
                    .font(.title.bold())
                Text("to \(receipt.recipient)")
                    .foregroundStyle(.secondary)
            }

            LabeledContent("Reference") {
                Text(receipt.reference)
                    .font(.body.monospaced())
            }
            .padding()
            .background(.quaternary.opacity(0.5), in: .rect(cornerRadius: 12, style: .continuous))
            .padding(.horizontal, 32)

            Spacer()

            Button {
                dismiss()
            } label: {
                Text("Done")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .padding(.horizontal, 24)
            .padding(.bottom, 12)
        }
        .sensoryFeedback(.success, trigger: receipt.id)
    }
}
