import SwiftUI

struct ContentView: View {
    var body: some View {
        TabView {
            PatternsView()
                .tabItem { Label("Patterns", systemImage: "rectangle.stack") }
            BankingView()
                .tabItem { Label("Banking", systemImage: "creditcard") }
            LabView()
                .tabItem { Label("Lab", systemImage: "slider.horizontal.3") }
        }
    }
}
