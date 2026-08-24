import XCTest

final class YardJourneyUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-ui-testing"]
        app.launch()
        XCTAssertTrue(app.otherElements["rootTabView"].waitForExistence(timeout: 5))
    }

    func testBrowseElectronicsOpenMonitorAndSave() {
        let electronics = app.buttons["category_electronics"]
        XCTAssertTrue(electronics.waitForExistence(timeout: 3))
        electronics.tap()

        XCTAssertTrue(app.otherElements["searchView"].waitForExistence(timeout: 3))
        openMonitor()

        let save = app.buttons["saveListingButton"]
        XCTAssertTrue(save.waitForExistence(timeout: 3))
        save.tap()
        XCTAssertTrue(app.buttons["Unsave"].waitForExistence(timeout: 3))
    }

    func testEnterListingDetailsAndSaveLocalDraft() {
        app.tabBars.buttons["Sell"].tap()

        let title = app.textFields["listingTitleField"]
        XCTAssertTrue(title.waitForExistence(timeout: 3))
        title.tap()
        title.typeText("Desk lamp draft")
        app.buttons["saveListingDraftButton"].tap()

        XCTAssertTrue(app.staticTexts["Desk lamp draft"].waitForExistence(timeout: 3))
    }

    func testReserveUsesServerAuthoritativeMockAndShowsConfirmation() {
        openMonitor()

        let reserve = app.buttons["reserveListingButton"]
        XCTAssertTrue(reserve.waitForExistence(timeout: 3))
        reserve.tap()

        XCTAssertTrue(app.staticTexts["Reserved for you"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["reservationDoneButton"].exists)
    }

    private func openMonitor() {
        let monitor = app.otherElements[
            "listingCard_11408445-3907-55C2-848E-8AD314EB1C7B"
        ]
        XCTAssertTrue(monitor.waitForExistence(timeout: 3))
        monitor.tap()
        XCTAssertTrue(app.buttons["reserveListingButton"].waitForExistence(timeout: 3))
    }
}
