import SwiftUI
import UIKit

/// Banking flows where a toast is the right tool — and where it isn't.
struct BankingView: View {
    @Environment(ToastCenter.self) private var center
    @State private var frozen = false

    private let iban = "GB29 NWBK 6016 1331 9268 19"

    var body: some View {
        NavigationStack {
            List {
                Section {
                    CardView(frozen: frozen)
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                }

                Section {
                    Button {
                        UIPasteboard.general.string = iban
                        center.show(.copied("IBAN"))
                    } label: {
                        Label("Copy IBAN", systemImage: "doc.on.doc")
                    }

                    Button {
                        frozen.toggle()
                        let nowFrozen = frozen
                        center.show(
                            .undoable(
                                nowFrozen ? "Card frozen" : "Card unfrozen",
                                symbol: "snowflake"
                            ) {
                                frozen = !nowFrozen
                            }
                        )
                    } label: {
                        Label(
                            frozen ? "Unfreeze card" : "Freeze card",
                            systemImage: "snowflake"
                        )
                    }
                } header: {
                    Text("Toast-appropriate")
                } footer: {
                    Text("Low stakes, reversible, and the card above visibly changes state — the toast is redundant confirmation, not the record.")
                }

                Section {
                    NavigationLink {
                        TransferView()
                    } label: {
                        Label("Send money", systemImage: "arrow.up.right.circle")
                    }
                } header: {
                    Text("Not toast-appropriate")
                } footer: {
                    Text("Money movement needs a persistent confirmation with a reference number. Try both endings inside.")
                }
            }
            .navigationTitle("Banking")
        }
    }
}

private struct CardView: View {
    var frozen: Bool

    var body: some View {
        RoundedRectangle(cornerRadius: 20, style: .continuous)
            .fill(
                LinearGradient(
                    colors: frozen
                        ? [Color(.systemGray2), Color(.systemGray)]
                        : [.indigo, .purple],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .frame(height: 190)
            .overlay(alignment: .topLeading) {
                Image(systemName: "wave.3.right")
                    .foregroundStyle(.white.opacity(0.8))
                    .padding(20)
            }
            .overlay(alignment: .bottomLeading) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("•••• •••• •••• 4821")
                        .font(.title3.monospaced())
                    Text("T. BYTE")
                        .font(.caption.weight(.semibold))
                        .opacity(0.8)
                }
                .foregroundStyle(.white)
                .padding(20)
            }
            .overlay {
                if frozen {
                    Label("Frozen", systemImage: "snowflake")
                        .font(.headline)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 10)
                        .background(.regularMaterial, in: .capsule)
                }
            }
            .animation(.default, value: frozen)
            .accessibilityElement(children: .ignore)
            .accessibilityLabel(frozen ? "Debit card, frozen" : "Debit card, active")
    }
}
