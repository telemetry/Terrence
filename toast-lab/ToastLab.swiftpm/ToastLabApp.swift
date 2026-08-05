import SwiftUI

@main
struct ToastLabApp: App {
    @State private var toastCenter = ToastCenter()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(toastCenter)
                // Host lives at the root so toasts survive navigation pushes,
                // sheet presentation, and tab switches.
                .toastHost()
        }
    }
}
