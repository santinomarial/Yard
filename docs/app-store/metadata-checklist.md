# App Store metadata checklist

## Draft listing

- Name: `Yard`
- Subtitle: `A trusted campus marketplace`
- Promotional text: `List useful items quickly, find what you need nearby, and coordinate safer public pickups with verified community members.`
- Keywords: `marketplace,reuse,campus,student,furniture,electronics,local,secondhand`
- Primary category: Shopping; secondary category: Lifestyle
- Description: Explain native photo-assisted listing, natural search, favorites and wanted posts, server-authoritative reservations, messaging, public-area pickup coordination, and safety reporting. State clearly that Yard does not process payments and is independent from Harvard University.
- Support URL: replace with an operator-controlled HTTPS page
- Marketing URL: optional; replace before submission
- Privacy Policy URL: publish `docs/privacy-policy.md` at a stable HTTPS URL

## Required assets and declarations

- [x] Opaque 1024×1024 App Store icon in the asset catalog
- [ ] Capture current iPhone screenshots at required App Store Connect sizes from a seeded demo build
- [ ] Optional app preview video contains no real student information
- [x] Version/build settings are project-driven
- [x] Camera, photo-library, and when-in-use location usage descriptions
- [x] Privacy manifest with required-reason API declaration
- [x] Account deletion inside the app
- [x] Terms, Privacy, Community Guidelines, prohibited-items, report/block, support, and independence disclaimer surfaces
- [ ] Replace `yard.market`, `api.yard.market`, and `support@yard.market` placeholders with verified operator-controlled endpoints
- [ ] Validate production signing, APNs, Associated Domains, Sign in with Apple, and TestFlight receipt

## App Privacy answers

Declare identifiers, email address, photos/videos, and other user content as linked to the user for app functionality; identifiers and safety content may also support fraud prevention/security. Do not declare tracking. Location is used on-device for directions/ETA and is not collected by Yard's backend. Confirm these answers against the deployed providers and current binary before every submission.

## Review notes

Use `docs/app-store-review.md`. Provide a current single-use review code and clear steps; never provide a production master bypass. Mention that payments occur outside the app, exact addresses are neither requested nor displayed, and all sample identities/listings are fictional.
