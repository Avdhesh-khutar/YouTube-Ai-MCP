import test from "node:test";
import assert from "node:assert/strict";
import { isValidDateOnly } from "../src/date-validation.ts";

test("accepts valid calendar dates", () => {
  assert.equal(isValidDateOnly("2026-10-21"), true);
  assert.equal(isValidDateOnly("2024-02-29"), true);
});

test("rejects malformed and impossible calendar dates", () => {
  assert.equal(isValidDateOnly("2026-2-01"), false);
  assert.equal(isValidDateOnly("2026-02-30"), false);
  assert.equal(isValidDateOnly("2025-02-29"), false);
  assert.equal(isValidDateOnly("not-a-date"), false);
});
