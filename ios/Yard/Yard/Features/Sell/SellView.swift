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
            Button("Done") { model.reset(); pickerItems = [] }
        } message: {
            Text("Your item passed its checks and is now visible in Yard.")
        }
        .onChange(of: model.state) { _, state in
            if case .published = state { showPublishedConfirmation = true }
        }
    }

    private var photoSection: some View {
        Section {
            HStack {
                PhotosPicker(
                    selection: $pickerItems,
                    maxSelectionCount: 8,
                    matching: .images
                ) {
                    Label(
                        model.photos.isEmpty ? "Choose photos" : "Change photos",
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
                } label: {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(draft.title.isEmpty ? "Untitled draft" : draft.title)
                            .foregroundStyle(.primary)
                        Text(draft.updatedAt, format: .relative(presentation: .named))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .onDelete { offsets in
                for index in offsets { modelContext.delete(savedDrafts[index]) }
                try? modelContext.save()
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
                modelContext.insert(model.makeLocalDraft())
                try? modelContext.save()
            }
            .accessibilityIdentifier("saveListingDraftButton")
            Button("Publish listing") {
                guard let token = environment.session.accessToken else { return }
                Task { await model.publish(using: environment.selling, accessToken: token) }
            }
            .buttonStyle(YardPrimaryButtonStyle())
            .disabled(!model.canPublish)
            .accessibilityIdentifier("publishListingButton")
        }
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
