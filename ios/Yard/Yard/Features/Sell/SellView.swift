import PhotosUI
import SwiftData
import SwiftUI

struct SellView: View {
    @Environment(AppEnvironment.self) private var environment
    @Environment(\.modelContext) private var modelContext
    @Query(sort: \ListingDraftRecord.updatedAt, order: .reverse) private var savedDrafts: [ListingDraftRecord]
    @State private var model = SellViewModel()
    @State private var pickerItems: [PhotosPickerItem] = []
    @State private var showPublishedConfirmation = false
    @State private var showCamera = false
    @State private var editingDraftID: UUID?
    @State private var isBatchPublishing = false
    @State private var publicationMessage = "Your item passed its checks and is now visible in Yard."

    private let analyzer = VisionItemAnalysisService()

    var body: some View {
        Form {
            photoSection
            detailsSection
            pricingSection
            pickupSection
            if !savedDrafts.isEmpty { draftsSection }
            submissionSection
        }
        .navigationTitle("Sell")
        .task { await model.loadCategories(using: environment.marketplace) }
        .onChange(of: pickerItems) { _, items in
            Task { await model.loadPhotos(from: items) }
        }
        .fullScreenCover(isPresented: $showCamera) {
            CameraCaptureView { data in
                Task { await model.appendCameraPhoto(data) }
            }
            .ignoresSafeArea()
        }
        .alert("Listing published", isPresented: $showPublishedConfirmation) {
            Button("Done") { resetEditor() }
        } message: {
            Text(publicationMessage)
        }
        .onChange(of: model.state) { _, state in
            if case .published = state, !isBatchPublishing {
                removeEditingDraft()
                publicationMessage = "Your item passed its checks and is now visible in Yard."
                showPublishedConfirmation = true
            }
        }
    }

    private var photoSection: some View {
        let photoButtonTitle = model.photos.isEmpty ? "Choose photos" : "Change photos"
        return Section {
            HStack {
                PhotosPicker(
                    selection: $pickerItems,
                    maxSelectionCount: 8,
                    matching: .images
                ) {
                    Label(
                        photoButtonTitle,
                        systemImage: "photo.on.rectangle.angled"
                    )
                }
                .accessibilityIdentifier("listingPhotoPicker")

                Spacer()

                if UIImagePickerController.isSourceTypeAvailable(.camera) {
                    Button {
                        showCamera = true
                    } label: {
                        Label("Camera", systemImage: "camera")
                    }
                    .disabled(model.photos.count >= 8)
                    .accessibilityIdentifier("listingCameraButton")
                }
            }

            if !model.photos.isEmpty {
                ScrollView(.horizontal) {
                    HStack(spacing: YardTheme.Spacing.small) {
                        ForEach(model.photos) { photo in
                            PhotoThumbnail(data: photo.data)
                        }
                    }
                }
                .scrollIndicators(.hidden)
                Button {
                    Task { await model.analyze(using: analyzer) }
                } label: {
                    Label("Suggest details from photos", systemImage: "text.viewfinder")
                }
                .disabled(model.state != .editing)
                .accessibilityIdentifier("analyzeListingPhotosButton")
            }
        } header: {
            Text("Photos")
        } footer: {
            Text("Yard reads visible labels and packaging text on-device. Review every suggestion before publishing.")
        }
    }

    private var detailsSection: some View {
        Section("Item details") {
            TextField("Title", text: $model.title)
                .accessibilityIdentifier("listingTitleField")
            TextField("Description", text: $model.itemDescription, axis: .vertical)
                .lineLimit(3...8)
                .accessibilityIdentifier("listingDescriptionField")
            Picker("Category", selection: $model.categoryID) {
                Text("Choose a category").tag(Optional<UUID>.none)
                ForEach(model.categories) { category in
                    Text(category.name).tag(Optional(category.id))
                }
            }
            Picker("Condition", selection: $model.condition) {
                ForEach(ListingCondition.allCases, id: \.self) { condition in
                    Text(condition.displayName).tag(condition)
                }
            }
        }
    }

    private var pricingSection: some View {
        Section("Price") {
            Toggle("Free", isOn: $model.isFree)
            if !model.isFree {
                TextField("0.00", text: $model.priceText)
                    .keyboardType(.decimalPad)
                    .accessibilityLabel("Price in dollars")
                    .accessibilityIdentifier("listingPriceField")
            }
        }
    }

    private var pickupSection: some View {
        Section {
            Picker("Public area", selection: $model.pickupZone) {
                ForEach(model.pickupZones, id: \.self) { Text($0).tag($0) }
            }
        } header: {
            Text("Pickup area")
        } footer: {
            Text("Use a coarse public area. Never put a dorm room or exact address in a listing.")
        }
    }

    private var draftsSection: some View {
        Section("Saved on this device") {
            ForEach(savedDrafts.prefix(5)) { draft in
                Button {
                    model.restore(draft)
                    editingDraftID = draft.id
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(draft.title.isEmpty ? "Untitled draft" : draft.title)
                                .foregroundStyle(.primary)
                            Text(draft.updatedAt, format: .relative(presentation: .named))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if draft.isReadyForBatch {
                            Label("Reviewed", systemImage: "checkmark.seal.fill")
                                .font(.caption)
                                .foregroundStyle(.green)
                        }
                    }
                }
            }
            .onDelete { offsets in
                for index in offsets { modelContext.delete(savedDrafts[index]) }
                try? modelContext.save()
            }

            Button("Use this pickup area for all drafts") {
                for draft in savedDrafts {
                    draft.pickupZone = model.pickupZone
                    draft.updatedAt = .now
                }
                try? modelContext.save()
            }

            let reviewedCount = savedDrafts.filter(\.isReadyForBatch).count
            if reviewedCount > 0 {
                Button("Publish \(reviewedCount) reviewed drafts") {
                    Task { await publishReviewedDrafts() }
                }
                .disabled(isBatchPublishing || environment.session.accessToken == nil)
            }
        }
    }

    private var submissionSection: some View {
        Section {
            if let error = model.errorMessage {
                Text(error).foregroundStyle(.red).accessibilityIdentifier("sellError")
            }
            if model.state == .publishing {
                ProgressView(value: model.progress) { Text("Uploading and checking photos") }
            }
            Button("Save draft on this device") {
                saveCurrentDraft(readyForBatch: false)
            }
            .accessibilityIdentifier("saveListingDraftButton")
            Button("Save and mark reviewed for batch") {
                saveCurrentDraft(readyForBatch: true)
            }
            .disabled(!model.canPublish)
            Button("Create another draft with these common details") {
                let draft = model.makeNextItemDraft()
                modelContext.insert(draft)
                try? modelContext.save()
                model.restore(draft)
                editingDraftID = draft.id
                pickerItems = []
            }
            Button("Publish listing") {
                guard let token = environment.session.accessToken else { return }
                Task { await model.publish(using: environment.selling, accessToken: token) }
            }
            .buttonStyle(YardPrimaryButtonStyle())
            .disabled(!model.canPublish)
            .accessibilityIdentifier("publishListingButton")
        }
    }

    private func saveCurrentDraft(readyForBatch: Bool) {
        if let draft = editingDraft {
            for photo in draft.photos { modelContext.delete(photo) }
            model.update(draft, readyForBatch: readyForBatch)
        } else {
            let draft = model.makeLocalDraft()
            draft.isReadyForBatch = readyForBatch
            modelContext.insert(draft)
            editingDraftID = draft.id
        }
        try? modelContext.save()
    }

    private func publishReviewedDrafts() async {
        guard let token = environment.session.accessToken else { return }
        isBatchPublishing = true
        var publishedCount = 0
        let reviewed = savedDrafts.filter(\.isReadyForBatch)
        for draft in reviewed {
            model.restore(draft)
            guard model.canPublish else {
                draft.isReadyForBatch = false
                continue
            }
            await model.publish(using: environment.selling, accessToken: token)
            if case .published = model.state {
                modelContext.delete(draft)
                publishedCount += 1
            } else {
                break
            }
        }
        try? modelContext.save()
        isBatchPublishing = false
        editingDraftID = nil
        if publishedCount > 0 {
            publicationMessage = "Published \(publishedCount) individually reviewed \(publishedCount == 1 ? "listing" : "listings")."
            showPublishedConfirmation = true
        }
    }

    private var editingDraft: ListingDraftRecord? {
        savedDrafts.first { $0.id == editingDraftID }
    }

    private func removeEditingDraft() {
        guard let editingDraft else { return }
        modelContext.delete(editingDraft)
        try? modelContext.save()
        editingDraftID = nil
    }

    private func resetEditor() {
        model.reset()
        pickerItems = []
        editingDraftID = nil
    }
}

private struct PhotoThumbnail: View {
    let data: Data

    var body: some View {
        Group {
            if let image = UIImage(data: data) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
            } else {
                Image(systemName: "photo")
                    .foregroundStyle(.secondary)
            }
        }
        .frame(width: 112, height: 112)
        .background(YardTheme.Colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: YardTheme.Radius.card))
        .clipped()
        .accessibilityLabel("Selected item photo")
    }
}

#Preview {
    NavigationStack { SellView() }
        .environment(AppEnvironment(marketplace: PreviewMarketplaceRepository()))
        .modelContainer(for: [ListingDraftRecord.self, DraftPhotoRecord.self], inMemory: true)
}
