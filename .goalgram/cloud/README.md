# Goalgram Xcode Cloud bridge (setup in progress)

This stable Xcode project contains the real application and all six extension signing targets. It does not generate a placeholder executable. `ci_pre_xcodebuild.sh` builds the application through the existing Bazel adapter; native targets stage those real products and let Xcode handle automatic signing and extension embedding.

## Status

Project/scheme enumeration, configuration inspection, Python syntax and fail-closed staging checks have passed. No complete archive, Xcode Cloud run, extension-signing validation or TestFlight publication has passed yet. Treat this bridge as unverified until those checks complete.

## First onboarding

Open `GoalgramCloud.xcodeproj`, select the shared `Goalgram` scheme, then Product > Xcode Cloud > Create Workflow. Reuse the existing GitHub provider authorization for `mylyne/Goalgram`. Configure Xcode 27.1 and an Archive action for iOS with internal TestFlight distribution, but do not release before inspecting the first signed archive.

The workflow needs secret `GOALGRAM_BUILD_CONFIG_BASE64`: base64 of the existing private Goalgram appstore configuration. Never commit it, echo it to build logs, or place it in the project. This is an intentional private configuration transfer to Apple's cloud, not part of project generation. Initial onboarding also requires committing/pushing this project and the fix after approval.

Build numbers use 10013 + CI_BUILD_NUMBER; verify against App Store Connect before enabling publication. The default checked-in 10014 is for project inspection only. Native target build numbers are loaded from BuildNumber.xcconfig, rewritten before xcodebuild starts.

## Required cloud verification

- Main application and all six extensions have matching versions and Goalgram identifiers.
- All final signatures/profiles are Apple-issued, no bootstrap profile or ad-hoc signatures survive.
- Production APNs, App Groups and communication notification permissions remain valid.
- Framework dSYMs match their binaries; no upload warnings return.
- Real application startup and auto-read regression, including animation completion and safety gates.
- Real-account testing of the originally reported intermittent unread state (the callback test alone is not sufficient).

`project.json` is the reproducible XcodeGen input; the generated stable `.xcodeproj` and shared scheme must be committed. Do not regenerate it inside Cloud. The build hook intentionally fails if private config or real Bazel products are missing.
