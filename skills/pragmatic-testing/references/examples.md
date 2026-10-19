# Test-value examples

These Swift sketches illustrate the reasoning, not APIs or dependencies to add to a project. The same checks apply in other languages. Expected outcomes below come from the stated example requirements.

## 1. A mock echo versus a real rule

Requirement: the library exposes only published documents, preserving their order.

Weak:

```swift
repository.result = [publishedDocument]
let result = try await library.load()
#expect(result == [publishedDocument])
```

This cannot distinguish correct filtering from no filtering. The fixture already satisfies the rule.

Stronger:

```swift
let first = document(id: "first", published: true)
let draft = document(id: "draft", published: false)
let last = document(id: "last", published: true)
repository.result = [first, draft, last]

let result = try await library.load() // Real production library; only I/O is stubbed.

#expect(result.map(\.id) == ["first", "last"])
```

Plausible bug: removing the production publication filter includes `draft`. Reversing the result order also violates the asserted contract. The repository double must return all three documents, not filter them itself.

For a genuinely forwarding-only library, skip a new echo test if existing integration coverage proves the needed wiring. A separate test can still be valuable if it proves a distinct contract, such as selecting the correct account or preserving a required error.

## 2. Copied branching versus independent boundary examples

Requirement: orders of at least 10,000 cents receive free shipping; smaller orders cost 500 cents.

Weak:

```swift
let expected = subtotal >= 10_000 ? 0 : 500
#expect(shippingCost(subtotal: subtotal) == expected)
```

The test copies the implementation's decision and may copy its mistake. Instead, state facts from the rule, with explicit expected values:

```swift
@Test(arguments: [
    (subtotal: 9_999, expected: 500),
    (subtotal: 10_000, expected: 0),
    (subtotal: 10_001, expected: 0),
])
func shippingBoundary(example: (subtotal: Int, expected: Int)) {
    #expect(shippingCost(subtotal: example.subtotal) == example.expected)
}
```

Plausible bug: changing `>=` to `>` charges shipping at exactly 10,000 cents. A witnessed red before the function exists does not show this boundary is protected; the boundary case does. If its effectiveness is unclear, temporarily apply that comparison change during authorized verification and confirm the assertion fails, then restore and re-run green.

## 3. A double's algorithm versus real production behavior

Requirement: advancing playback skips chapter headings and selects the next body chunk.

Weak: a mocked playback manager implements its own loop that skips headings; the test calls a screen's `next` handler and checks the mock's selected chunk. Removing the loop from the real playback pipeline leaves this test green.

Stronger: instantiate the real pipeline with a controlled stream containing a current body chunk, a heading, and the next body chunk. Invoke the pipeline's stable `next` interface and assert that its selected ID is the next body's ID. Stub only external audio or I/O. A screen-level test may separately prove that the button delegates to this pipeline, but should not replay the pipeline's whole case matrix.

Plausible bug: treating the first heading as a playable chunk. If a fake skips it before production sees it, the test has the wrong seam.

## 4. A genuine integration contract

Requirement: a failed database transaction must leave no partially inserted order.

Use the real database in an isolated temporary store. Arrange a supported constraint failure after an earlier write within the transaction, execute the real order operation, and assert both the reported failure and the absence of the partial order through the real store.

Plausible bug: moving the earlier write outside the transaction. A fake database that implements rollback proves only the fake. A unit test of error mapping may also be useful, but does not replace this atomicity check even when both tests execute overlapping code.

## 5. A weak test that must be rewritten, not deleted

Requirement: fallback narration eventually reveals all words when no recorded audio exists.

Weak: sleep briefly and check that at least one word appeared. If this is the only test entering fallback narration, deleting it removes protection for the entire path.

Stronger: drive the real fallback behavior with controlled time where supported, await bounded completion, and assert the complete expected sequence. Keep the no-audio scenario explicit. A normal recorded-audio playback test is not equivalent protection.

Plausible bug: revealing the first word but never scheduling the rest. "Wait for the first word, then assert the first word" still misses it.
