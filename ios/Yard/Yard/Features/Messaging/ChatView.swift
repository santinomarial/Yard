import SwiftUI

struct ChatView: View {
    let conversation: Conversation
    let listingTitle: String
    @Environment(AppEnvironment.self) private var environment
    @State private var model = ChatViewModel()

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
                                    isMine: message.senderID == environment.session.currentUser?.id
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
        .task { await load() }
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
}

private struct MessageBubble: View {
    let message: YardMessage
    let isMine: Bool

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
    }
}
