# Extending a shipped game's UI at runtime

Use this reference when a mod adds rows, tabs or pages to the game's own menus (pause menu, photo
mode, settings) through reflection, so the addition reads as part of the game. The target is
**native**: a player cannot tell the added rows from the game's own. Every rule below came from a
live pass where the first attempt looked or behaved wrong.

## Verify every call against the live signature

Before code calls a reflected function, `describe` it on a live instance and match the parameter
count and names exactly. Counts include out and return parameters (a `NavigateToCustomIndex` with
`Index, SubIndex, Success, ReturnValue` takes four, not two or three), and names differ between
builds and docs (`bShouldGrayout`, not `Grayout`). Do this for **every** function the feature calls,
in one probe script, before the first install; a wrong count throws, and a feature that catches the
throw and cleans up just looks like "nothing appeared". A widget's helper bar or text block may be
the game's own Blueprint wrapper with its own setter (`UpdateProgressBar(InPercent)`), not the UMG
class you expected.

## Look like the game: learn from its own instances

A widget created from the class default is not what the game shows. Designers set per-instance
properties, and pages set layout at runtime:

- **Diff** a live game row against your row: every plain property plus its slot. Copy what differs
  (navigable type, hover selection, colours) from a game instance at runtime rather than hardcoding
  today's values, so a game patch carries over.
- Call the page's **own** layout and scale functions after adding or reordering children (for
  example a page's `UpdateSelectionDistance` sets the negative slot padding that gives the game's
  row spacing; `RefreshUIScale` applies the player's text-size setting to a page's scale box).
- Match the host exactly. Add only elements the game's own screens have; a value column that holds
  about twenty characters means a row holds a short value, and longer prose stays in the mod's own
  menu. An extra description line or a read-only row that shows cut-off text reads as bolted on.

## The game rewrites what you filled

A row's construct runs a frame after you fill it, and game-wide resets (Reset All, the UI coming back
after a hidden state) rewrite rows to their defaults (`- -`, an empty bar). Read back what a row
shows and refill on mismatch: every row during its first second, then one representative per row
**kind** (the game resets option rows and slider rows separately). Reading back every row every
frame is the slow version of the same fix.

## Layout and navigation timing

- A panel the game has just created has zero desired size. Call `ForceLayoutPrepass` before
  `GetDesiredSize`; if it still reads zero, try again next tick instead of building on zero.
- `InsertChildAt` is often not callable in shipping builds. Re-add the children in order, and check
  every function the reorder needs **before** `ClearChildren`, restoring the old list on failure;
  a failed reorder after the clear empties the game's menu.
- A scrolling strip of fixed-size items scrolls by whole items (offset = first visible × pitch), so
  no icon is ever cut at the edge.
- The game selects a page's first row when its tab opens; rows you add a few ticks later miss that.
  Select the first row (or the previously selected one) yourself once the rows exist.

## Confirm, input and cameras

- A menu page often handles confirm itself by comparing the active row with its own named rows, so
  an added row never reaches the confirmed state. Post-hook the page's input event (its parameter
  carries the input enum) or the row's confirmed-state function, act on the next tick, and install
  the hook only while that page is visible: a Blueprint hook makes every script call pay a lookup.
- A Blueprint enum's names in a dump are `NewEnumeratorN`; read the enum asset's `DisplayNameMap`
  to learn which value is Confirm, Down, Back.
- A mode with its own camera state (photo mode, cutscenes) overrides `SetViewTargetWithBlend`; a
  camera state's own `SetCameraView` may stick on the object and still not drive the view. Step out
  of the mode for the mod's camera work, and come back into it, rather than fighting its stack.

## Cost

Measure per-phase frame cost before calling it done. Rebuild rows when the mod's data revision
changes, not every frame. Creating game widgets costs milliseconds each: spread a page build over
frames (one tab or page per frame, a few rows per frame) and measure each step; a 50 ms open is a
visible hitch. Cache imported textures and import them ahead while the player is still in a menu.

## Clean up and prove it

On close, remove every added widget and restore every wrapped container, then reopen the game's own
screen and count its panels in the viewport (`GetAllWidgetsOfClass` with `IsInViewport`): exactly
one, with the original child counts. Close a mode the way the player does (its input action event),
never through a developer or debug exit function, which can leave a ghost panel on screen.
