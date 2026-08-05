// swift-tools-version: 5.9
import PackageDescription
import AppleProductTypes

let package = Package(
    name: "ToastLab",
    platforms: [
        .iOS("17.0")
    ],
    products: [
        .iOSApplication(
            name: "ToastLab",
            targets: ["AppModule"],
            bundleIdentifier: "com.toastlab.demo",
            displayVersion: "1.0",
            bundleVersion: "1",
            supportedDeviceFamilies: [
                .pad,
                .phone
            ],
            supportedInterfaceOrientations: [
                .portrait
            ]
        )
    ],
    targets: [
        .executableTarget(
            name: "AppModule",
            path: "."
        )
    ]
)
