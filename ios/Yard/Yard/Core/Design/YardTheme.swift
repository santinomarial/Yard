import SwiftUI

enum YardTheme {
    enum Colors {
        static let crimson = Color(red: 165 / 255, green: 28 / 255, blue: 48 / 255)
        static let ink = Color(red: 30 / 255, green: 30 / 255, blue: 30 / 255)
        static let parchment = Color(red: 243 / 255, green: 243 / 255, blue: 241 / 255)
        static let mortar = Color(red: 140 / 255, green: 129 / 255, blue: 121 / 255)
        static let slate = Color(red: 137 / 255, green: 150 / 255, blue: 160 / 255)

        static let background = Color(uiColor: .systemGroupedBackground)
        static let surface = Color(uiColor: .secondarySystemGroupedBackground)
        static let primaryText = Color.primary
        static let secondaryText = Color.secondary
    }

    enum Spacing {
        static let xSmall: CGFloat = 4
        static let small: CGFloat = 8
        static let medium: CGFloat = 16
        static let large: CGFloat = 24
        static let xLarge: CGFloat = 32
    }

    enum Radius {
        static let small: CGFloat = 10
        static let card: CGFloat = 18
        static let button: CGFloat = 14
    }
}

struct YardPrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(YardTheme.Colors.crimson.opacity(configuration.isPressed ? 0.78 : 1))
            .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.button, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.98 : 1)
            .animation(.snappy(duration: 0.15), value: configuration.isPressed)
    }
}
