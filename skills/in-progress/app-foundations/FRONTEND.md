# Frontend and UI architecture

Rules for the client side of an app, mobile or web. Examples use Android and Compose terms where a concrete name helps; the ideas carry to SwiftUI, React and the rest.

## Rules

1. **State flows one way.** Data layer exposes observable state, a view model turns it into screen state, the screen renders it and sends events back. Screens never call the network or the database directly.
2. **Model screen state as a closed set.** Loading, content, error (and empty, if it differs) as a sealed type or tagged union. A screen that can be "loading and errored at once" has a bug waiting.
3. **Separate network, storage and UI models.** The wire format, the local table and what the screen shows are three types with mappers between them, so a server field rename does not ripple into every screen.
4. **Drafts autosave.** Any form a user would be upset to lose saves on every field change to local storage and survives app kill.
5. **High-rate input is batched before it touches state.** Scanners, sensors, sockets: collect on a background thread, batch by time or count (tens of milliseconds), hand one batch to the data layer, persist it in one transaction. Conflate the *view* if it cannot keep up; never drop the *data*.
6. **One writer per local database.** Funnel writes through a single-threaded dispatcher or actor. Concurrent writers on SQLite buy lock errors, not speed.
7. **Hardware sits behind an interface with a fake.** Barcode, RFID, NFC, camera, printer: an interface the app codes against, one adapter per vendor, and a fake that replays a script. The fake is what makes emulator runs, screenshot tests and load tests possible.
8. **Design tokens, not ad hoc colours.** Colour, type, spacing and radius come from one token set. Add semantic tokens the base kit lacks (success, warning, pending, conflict) and check their contrast.

## Accessibility and field use

- Touch targets at least 48dp (or 44pt on iOS) even when the row looks denser. People wear gloves.
- Never encode state by colour alone; pair it with an icon and text. Sync and scan states are the usual offenders.
- Check contrast of every text and background pair you actually use, including muted text on muted backgrounds, which often fails AA while muted-on-white passes.
- Test on the real target device, at the real brightness, with the real input method.

## Performance

- Long lists: stable item keys, a content type per row kind, one flat row composable, no deep nesting per row.
- Keep list instances stable instead of reaching for blanket immutability annotations; read fast-changing values in layout or draw, not in composition.
- No heavy work at app start; generate and ship startup or baseline profiles where the platform supports them. Note that side-loaded or MDM-pushed builds may not get those profiles applied at install time.
- A simple device tier flag lets low-end devices skip animations and blur.

## Traps

- Spinners that wait for the network on screens that already have local data. Show local data, refresh in the background.
- Error states that say "something went wrong" and offer nothing. Say what failed, whether the data is safe, and what the user can do.
- Hardware SDK callbacks doing work on their own thread and touching UI state directly.
- Building against the vendor SDK first and adding the fake later. The fake comes first; it defines the interface.

## Checklist

- [ ] Screens read observable state from the data layer only.
- [ ] Screen state is a closed set of cases, each rendered.
- [ ] Forms autosave drafts locally.
- [ ] High-rate inputs are batched; the view conflates, the data does not drop.
- [ ] Every hardware dependency has an interface and a fake.
- [ ] Touch targets, colour-independent state, and measured contrast are checked.
- [ ] Sync and error state is visible where the user needs it.
