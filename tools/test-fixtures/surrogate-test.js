// Test fixture with intentional surrogate issues
// This file is used by the verification system to test surrogate detection

const cleanString = "Hello, World! 👋";

// Intentional surrogate issues for testing (these should be detected)
const unpairedHighSurrogate = "Text with unpaired high: \uD800 end";
const unpairedLowSurrogate = "Text with unpaired low: \uDC00 end";

// Valid surrogate pair (should NOT be detected as an issue)
const validSurrogatePair = "Valid emoji: 😀 end";

module.exports = {
  cleanString,
  unpairedHighSurrogate,
  unpairedLowSurrogate,
  validSurrogatePair
};