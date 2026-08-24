import SwiftUI

struct ChatView: View {
    let conversation: Conversation
    let listingTitle: String
    @Environment(AppEnvironment.self) private var environment
    @State private var model = ChatViewModel()
    @State private var reportTarget: ReportTargetReference?
    @State private var showsBlockConfirmation = false
    @State private var safetyMessage: String?

    var body: some View {
        VStack(spacing: 0) {
            if model.isLoading && model.messages.isEmpty {
                ProgressView("Loading conversation…").frame(maxHeight: .infinity)
            } else if model.messages.isEmpty {
                ContentUnavailableView(
                    "Start the conversation",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Ask about condition, availability, or a public pickup area.")
                )
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: YardTheme.Spacing.small) {
                            ForEach(model.messages) { message in
                                MessageBubble(
                                    message: message,
                                    isMine: message.senderID == environment.session.currentUser?.id,
                                    onReport: {
                                        reportTarget = ReportTargetReference(
                                            type: .message,
                                            targetID: message.id,
                                            title: "Message: \(message.body.prefix(80))"
                                        )
                                    }
                                )
                                .id(message.id)
                            }
                        }
                        .padding()
                    }
                    .onChange(of: model.messages.count) {
                        if let last = model.messages.last { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }

            if let error = model.errorMessage {
                Text(error).font(.caption).foregroundStyle(.red).padding(.horizontal)
            }

            HStack(alignment: .bottom) {
                TextField("Message", text: $model.draft, axis: .vertical)
                    .lineLimit(1...5)
                    .textFieldStyle(.roundedBorder)
                    .accessibilityIdentifier("messageField")
                Button("Send", systemImage: "arrow.up.circle.fill") { Task { await send() } }
                    .labelStyle(.iconOnly)
                    .font(.title2)
                    .disabled(model.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || model.isSending)
                    .accessibilityIdentifier("sendMessageButton")
            }
            .padding()
            .background(.bar)
        }
        .navigationTitle(listingTitle)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu("Safety", systemImage: "ellipsis") {
                    Button("Report user", role: .destructive) {
                        guard let otherUserID else { return }
                        reportTarget = ReportTargetReference(
                            type: .user, targetID: otherUserID, title: "Conversation member"
                        )
                    }
                    Button("Block user", role: .destructive) {
                        showsBlockConfirmation = true
                    }
                }
            }
        }
        .sheet(item: $reportTarget) { ReportSheet(target: $0) }
        .confirmationDialog("Block this user?", isPresented: $showsBlockConfirmation) {
            Button("Block user", role: .destructive) { Task { await blockUser() } }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("They will no longer be able to continue direct interaction with you.")
        }
        .alert("Yard", isPresented: Binding(
            get: { safetyMessage != nil },
            set: { if !$0 { safetyMessage = nil } }
        )) { Button("OK", role: .cancel) {} } message: { Text(safetyMessage ?? "") }
        .task {
            await load()
            connect()
        }
        .onDisappear { model.disconnect() }
        .refreshable { await load() }
    }

    private func load() async {
        guard let token = environment.session.accessToken else { return }
        await model.load(
            conversationID: conversation.id,
            using: environment.transactions,
            accessToken: token
        )
    }

    private func send() async {
        guard let token = environment.session.accessToken else { return }
        await model.send(
            conversationID: conversation.id,
            using: environment.transactions,
            accessToken: token
        )
    }

    private func connect() {
        guard let token = environment.session.accessToken else { return }
        model.connect(
            conversationID: conversation.id,
            using: environment.transactions,
            accessToken: token
        )
    }

    private var otherUserID: UUID? {
        conversation.memberIDs.first { $0 != environment.session.currentUser?.id }
    }

    private func blockUser() async {
        guard let token = environment.session.accessToken, let otherUserID else { return }
        do {
            try await environment.safety.block(userID: otherUserID, accessToken: token)
            safetyMessage = "This user is blocked."
        } catch {
            safetyMessage = error.transactionMessage
        }
    }
}

private struct MessageBubble: View {
    let message: YardMessage
    let isMine: Bool
    let onReport: () -> Void

    var body: some View {
        HStack {
            if isMine { Spacer(minLength: 52) }
            VStack(alignment: .leading, spacing: 4) {
                Text(message.body)
                Text(message.createdAt, format: .dateTime.hour().minute())
                    .font(.caption2)
                    .foregroundStyle(isMine ? .white.opacity(0.8) : .secondary)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
            .background(isMine ? YardTheme.Colors.crimson : YardTheme.Colors.surface)
            .foregroundStyle(isMine ? .white : .primary)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            if !isMine { Spacer(minLength: 52) }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(isMine ? "You" : "Seller"): \(message.body)")
        .contextMenu {
            if !isMine, message.messageType == .text {
                Button("Report message", role: .destructive, action: onReport)
            }
        }
    }
}
