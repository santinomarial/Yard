import SwiftData
import SwiftUI

struct ProfileView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.modelContext) private var modelContext
    @State private var model = ProfileViewModel()
    @State private var showsEditName = false
    @State private var showsDeleteConfirmation = false

    var body: some View {
        List {
            if let user = environment.session.currentUser {
                profileHeader(user)
            }

            Section("Your listings") {
                if model.isLoading && model.listings.isEmpty {
                    ProgressView()
                } else if model.listings.isEmpty {
                    Text("Your published and draft listings will appear here.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(model.listings) { listing in
                        NavigationLink(value: listing) {
                            HStack {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(listing.title).font(.headline)
                                    Text(listing.status.displayName)
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(statusColor(listing.status))
                                }
                                Spacer()
                                Text(listing.formattedPrice).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }

            Section("Messages") {
                if model.conversations.isEmpty {
                    Text("Conversations with buyers and sellers will appear here.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(model.conversations) { conversation in
                        NavigationLink {
                            ChatView(conversation: conversation, listingTitle: "Yard conversation")
                        } label: {
                            Label {
                                VStack(alignment: .leading) {
                                    Text("Listing conversation")
                                    Text(conversation.updatedAt, format: .relative(presentation: .named))
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            } icon: { Image(systemName: "bubble.left.and.bubble.right") }
                        }
                    }
                }
            }

            Section("Exchanges") {
                if model.reservations.isEmpty {
                    Text("Reserved purchases and sales will appear here.")
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(model.reservations) { reservation in
                        NavigationLink {
                            PickupCoordinatorView(reservation: reservation)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(reservation.buyerID == environment.session.currentUser?.id ? "Purchase" : "Sale")
                                    .font(.headline)
                                Text(reservation.status.displayName)
                                    .font(.caption.weight(.semibold))
                                    .foregroundStyle(reservation.status == .active ? .orange : .secondary)
                                if reservation.status == .active {
                                    Text("Reservation ends \(reservation.expiresAt.formatted(.relative(presentation: .named)))")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }
            }

            Section("Safety and support") {
                NavigationLink("Notifications") {
                    NotificationsView()
                }
                NavigationLink("Prohibited items policy") {
                    PolicyView.prohibitedItems
                }
                NavigationLink("Privacy") {
                    PolicyView.privacy
                }
                Link("Contact support", destination: URL(string: "mailto:support@yard.market")!)
            }

            Section {
                Button("Sign out") { environment.session.signOut() }
                Button("Delete account", role: .destructive) { showsDeleteConfirmation = true }
                    .accessibilityIdentifier("deleteAccountButton")
            }
        }
        .navigationTitle("Profile")
        .navigationDestination(for: Listing.self) { ListingDetailView(listing: $0) }
        .task {
            model.restoreCachedConversations(
                MarketplaceLocalStore.cachedConversations(context: modelContext)
            )
            await load()
        }
        .refreshable { await load() }
        .alert("Delete your Yard account?", isPresented: $showsDeleteConfirmation) {
            Button("Delete account", role: .destructive) {
                Task { _ = await environment.session.deleteAccount() }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Your sign-in identity and Harvard email will be removed. Unsold listings will be taken down. Marketplace safety records are pseudonymized and retained where required.")
        }
        .sheet(isPresented: $showsEditName) { EditDisplayNameView() }
        .overlay(alignment: .bottom) {
            if let error = model.errorMessage ?? environment.session.errorMessage {
                Text(error)
                    .font(.caption).foregroundStyle(.white).padding()
                    .background(.red, in: Capsule()).padding()
            }
        }
        .accessibilityIdentifier("profileView")
    }

    private func profileHeader(_ user: YardUser) -> some View {
        Section {
            HStack(spacing: YardTheme.Spacing.medium) {
                Image(systemName: "person.crop.circle.fill")
                    .font(.system(size: 54)).foregroundStyle(YardTheme.Colors.crimson)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 5) {
                    Text(user.displayName).font(.title3.bold())
                    Label("Harvard email verified", systemImage: "checkmark.seal.fill")
                        .font(.subheadline).foregroundStyle(.green)
                    Text("Member since \(user.memberSince.formatted(.dateTime.month(.wide).year()))")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            Button("Edit display name") { showsEditName = true }
        }
    }

    private func load() async {
        guard let token = environment.session.accessToken else { return }
        await model.load(
            selling: environment.selling,
            transactions: environment.transactions,
            accessToken: token
        )
        if model.errorMessage == nil {
            MarketplaceLocalStore.replaceConversations(
                model.conversations, context: modelContext
            )
        }
    }

    private func statusColor(_ status: ListingStatus) -> Color {
        switch status {
        case .active: .green
        case .reserved: .orange
        case .rejected, .removed: .red
        default: .secondary
        }
    }
}

private struct EditDisplayNameView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.dismiss) private var dismiss
    @State private var displayName = ""

    var body: some View {
        NavigationStack {
            Form { TextField("Display name", text: $displayName) }
                .navigationTitle("Display name")
                .navigationBarTitleDisplayMode(.inline)
                .onAppear { displayName = environment.session.currentUser?.displayName ?? "" }
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { dismiss() }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") {
                            Task {
                                if await environment.session.updateProfile(displayName: displayName) {
                                    dismiss()
                                }
                            }
                        }
                        .disabled(displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                }
        }
        .presentationDetents([.medium])
    }
}

struct PolicyView: View {
    let title: String
    let bodyText: String

    var body: some View {
        ScrollView {
            Text(bodyText).frame(maxWidth: .infinity, alignment: .leading).padding()
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }

    static let prohibitedItems = PolicyView(
        title: "Prohibited items",
        bodyText: "Yard does not allow weapons, ammunition, explosives, illegal or controlled drugs, prescription drugs, alcohol, nicotine products, stolen or counterfeit goods, explicit sexual content or services, hazardous materials, fraudulent items, or anything prohibited by law or platform policy. Report a listing when you believe it violates this policy."
    )

    static let privacy = PolicyView(
        title: "Privacy",
        bodyText: "Yard uses your Apple identity to secure your account and a Harvard email solely to confirm access to the Harvard community. Public listings show a coarse pickup area, never an exact address. Yard does not require continuous location access. You can delete your account from Profile; sign-in and Harvard email data are removed while pseudonymized safety and transaction records may be retained."
    )
}
