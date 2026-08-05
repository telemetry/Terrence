import SwiftUI

// MARK: - Host

struct ToastHostModifier: ViewModifier {
    @Environment(ToastCenter.self) private var center
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    func body(content: Content) -> some View {
        content
            .overlay(alignment: .top) {
                if let toast = center.current, toast.placement == .topBanner {
                    BannerToastView(toast: toast)
                        .transition(transition(edge: .top))
                }
            }
            .overlay {
                if let toast = center.current, toast.placement == .centerHUD {
                    HUDToastView(toast: toast)
                        .transition(reduceMotion
                            ? .opacity
                            : .scale(scale: 0.85).combined(with: .opacity))
                }
            }
            .overlay(alignment: .bottom) {
                if let toast = center.current, toast.placement == .bottomSnackbar {
                    SnackbarToastView(toast: toast)
                        .transition(transition(edge: .bottom))
                        // Keep the bar clear of the tab bar, like Mail's Undo Send
                        // sits in the toolbar region rather than over content.
                        .padding(.bottom, 64)
                }
            }
            .sensoryFeedback(trigger: center.current) { _, newToast in
                newToast?.haptic
            }
            .animation(
                reduceMotion ? .easeInOut(duration: 0.2) : .snappy(duration: 0.35),
                value: center.current
            )
    }

    private func transition(edge: Edge) -> AnyTransition {
        reduceMotion ? .opacity : AnyTransition.move(edge: edge).combined(with: .opacity)
    }
}

extension View {
    func toastHost() -> some View {
        modifier(ToastHostModifier())
    }
}

// MARK: - Shared behavior

private struct ToastBehavior: ViewModifier {
    @Environment(ToastCenter.self) private var center
    let toast: Toast

    func body(content: Content) -> some View {
        content
            .task(id: toast.id) {
                try? await Task.sleep(for: toast.duration)
                guard !Task.isCancelled else { return }
                center.dismiss(toast)
            }
            .gesture(
                DragGesture(minimumDistance: 12).onEnded { value in
                    let towardEdge = switch toast.placement {
                    case .topBanner: value.translation.height < 0
                    default: value.translation.height > 0
                    }
                    if towardEdge { center.dismiss(toast) }
                }
            )
            .accessibilityElement(children: .combine)
    }
}

// MARK: - Top banner ("Pasted from…" style)

struct BannerToastView: View {
    let toast: Toast

    var body: some View {
        HStack(spacing: 8) {
            if let symbol = toast.symbol {
                Image(systemName: symbol)
                    .font(.footnote)
                    .foregroundStyle(.tint)
            }
            Text(toast.message)
                .font(.footnote.weight(.semibold))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.regularMaterial, in: .capsule)
        .overlay(Capsule().strokeBorder(.quaternary))
        .shadow(color: .black.opacity(0.12), radius: 10, y: 3)
        .padding(.top, 4)
        .modifier(ToastBehavior(toast: toast))
    }
}

// MARK: - Center HUD (Apple Music "Added to Library" style)

struct HUDToastView: View {
    let toast: Toast

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: toast.symbol ?? "checkmark.circle.fill")
                .font(.system(size: 44, weight: .medium))
                .foregroundStyle(.tint)
            Text(toast.message)
                .font(.headline)
                .multilineTextAlignment(.center)
        }
        .padding(28)
        .frame(minWidth: 190)
        .background(.regularMaterial, in: .rect(cornerRadius: 24, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .strokeBorder(.quaternary)
        )
        .shadow(color: .black.opacity(0.1), radius: 16, y: 6)
        .modifier(ToastBehavior(toast: toast))
    }
}

// MARK: - Bottom snackbar (Mail "Undo Send" style)

struct SnackbarToastView: View {
    @Environment(ToastCenter.self) private var center
    let toast: Toast

    var body: some View {
        HStack(spacing: 12) {
            if let symbol = toast.symbol {
                Image(systemName: symbol)
                    .foregroundStyle(.secondary)
            }
            Text(toast.message)
                .font(.subheadline.weight(.medium))
                .lineLimit(2)
            if let label = toast.actionLabel {
                Spacer(minLength: 8)
                Button(label) {
                    toast.action?()
                    center.dismiss(toast)
                }
                .font(.subheadline.weight(.semibold))
                .buttonStyle(.borderless)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 13)
        .frame(maxWidth: 480)
        .background(.regularMaterial, in: .rect(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .strokeBorder(.quaternary)
        )
        .shadow(color: .black.opacity(0.12), radius: 12, y: 4)
        .padding(.horizontal, 16)
        .modifier(ToastBehavior(toast: toast))
    }
}
