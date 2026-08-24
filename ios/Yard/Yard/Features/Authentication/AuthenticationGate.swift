import AuthenticationServices
import SwiftUI

struct AuthenticationGate: View {
    @Environment(AppEnvironment.self) private var environment

    var body: some View {
        Group {
            switch environment.session.phase {
            case .restoring:
                ProgressView("Opening Yard…")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(YardTheme.Colors.background)
            case .signedOut:
                SignInView()
            case let .signedIn(user):
                if user.harvardEmailVerified {
                    RootTabView()
                } else {
                    HarvardVerificationView()
                }
            }
        }
        .task { await environment.session.restore() }
    }
}

private struct SignInView: View {
    @Environment(AppEnvironment.self) private var environment

    var body: some View {
        VStack(spacing: YardTheme.Spacing.large) {
            Spacer()
            Image(systemName: "leaf.fill")
                .font(.system(size: 44, weight: .semibold))
                .foregroundStyle(YardTheme.Colors.crimson)
                .accessibilityHidden(true)
            VStack(spacing: YardTheme.Spacing.small) {
                Text("Yard")
                    .font(.system(.largeTitle, design: .serif, weight: .bold))
                Text("Buy and sell useful things with verified Harvard community members nearby.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            if let error = environment.session.errorMessage {
                Text(error)
                    .font(.callout)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .accessibilityIdentifier("authenticationError")
            }
            SignInWithAppleButton(.continue) { request in
                request.requestedScopes = [.fullName]
            } onCompletion: { result in
                guard case let .success(authorization) = result,
                      let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                      let tokenData = credential.identityToken,
                      let token = String(data: tokenData, encoding: .utf8)
                else {
                    environment.session.clearError()
                    return
                }
                let displayName = credential.fullName.flatMap {
                    PersonNameComponentsFormatter().string(from: $0).nilIfEmpty
                }
                Task {
                    await environment.session.signInWithApple(
                        identityToken: token, displayName: displayName
                    )
                }
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 52)
            .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.button))
            .accessibilityIdentifier("signInWithAppleButton")

            #if DEBUG
            Button("Use local development account") {
                Task { await environment.session.signInForDevelopment() }
            }
            .buttonStyle(YardPrimaryButtonStyle())
            .accessibilityIdentifier("developmentSignInButton")
            #endif
            Spacer()
            Text("Yard is an independent community marketplace and is not affiliated with or endorsed by Harvard University.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(YardTheme.Spacing.xLarge)
        .background(YardTheme.Colors.background)
        .disabled(environment.session.isWorking)
    }
}

private struct HarvardVerificationView: View {
    @Environment(AppEnvironment.self) private var environment
    @State private var email = ""
    @State private var code = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("name@harvard.edu", text: $email)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.emailAddress)
                        .textContentType(.emailAddress)
                        .accessibilityIdentifier("harvardEmailField")
                    Button("Send verification code") {
                        Task { await environment.session.requestVerification(email: email) }
                    }
                    .disabled(email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                } header: {
                    Text("Harvard email")
                } footer: {
                    Text("This proves control of an eligible Harvard-managed email. It does not verify enrollment or identity beyond that signal.")
                }

                if environment.session.developmentCode != nil {
                    Section("Verification code") {
                        TextField("6-digit code", text: $code)
                            .keyboardType(.numberPad)
                            .textContentType(.oneTimeCode)
                            .accessibilityIdentifier("verificationCodeField")
                        Button("Verify and enter Yard") {
                            Task {
                                await environment.session.confirmVerification(
                                    email: email, code: code
                                )
                            }
                        }
                        .buttonStyle(YardPrimaryButtonStyle())
                        .disabled(code.count != 6)
                        #if DEBUG
                        Text("Local code: \(environment.session.developmentCode ?? "")")
                            .font(.caption.monospaced())
                            .foregroundStyle(.secondary)
                        #endif
                    }
                }

                if let error = environment.session.errorMessage {
                    Section { Text(error).foregroundStyle(.red) }
                }
                Section {
                    Button("Sign out", role: .destructive) { environment.session.signOut() }
                }
            }
            .navigationTitle("Verify your community")
            .disabled(environment.session.isWorking)
        }
    }
}

private extension String {
    var nilIfEmpty: String? { isEmpty ? nil : self }
}
