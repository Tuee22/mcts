#!/usr/bin/env node
/**
 * Simple test runner for string utilities and sanitizer
 */

const { SurrogateSanitizer } = require('./sanitize');
const { 
  hasUnpairedSurrogates, 
  stripUnpairedSurrogates, 
  analyzeSurrogates,
  isUtf8Safe 
} = require('./string-utils');

console.log('🧪 Running basic tests for string utilities...');

// Test data
const testCases = [
  { name: 'Clean string', text: 'Hello, World!', expectIssues: false },
  { name: 'High surrogate only', text: 'Test \uD800 end', expectIssues: true },
  { name: 'Low surrogate only', text: 'Test \uDC00 end', expectIssues: true },
  { name: 'Valid surrogate pair', text: 'Test 😀 end', expectIssues: false },
  { name: 'Multiple issues', text: '\uD800 test \uDC00 end', expectIssues: true }
];

let passed = 0;
let failed = 0;

console.log('');
console.log('Testing hasUnpairedSurrogates...');

for (const testCase of testCases) {
  const result = hasUnpairedSurrogates(testCase.text);
  const success = result === testCase.expectIssues;
  
  if (success) {
    console.log(`✅ ${testCase.name}: ${result ? 'Issues detected' : 'No issues'}`);
    passed++;
  } else {
    console.log(`❌ ${testCase.name}: Expected ${testCase.expectIssues}, got ${result}`);
    failed++;
  }
}

console.log('');
console.log('Testing stripUnpairedSurrogates...');

for (const testCase of testCases) {
  if (testCase.expectIssues) {
    const original = testCase.text;
    const cleaned = stripUnpairedSurrogates(original);
    const stillHasIssues = hasUnpairedSurrogates(cleaned);
    
    if (!stillHasIssues) {
      console.log(`✅ ${testCase.name}: Successfully cleaned`);
      passed++;
    } else {
      console.log(`❌ ${testCase.name}: Still has issues after cleaning`);
      failed++;
    }
  }
}

console.log('');
console.log('Testing analyzeSurrogates...');

const problemText = 'Start \uD800 middle \uDC00 end';
const analysis = analyzeSurrogates(problemText);

if (analysis.length >= 2) {
  console.log(`✅ Analysis: Found ${analysis.length} issues as expected`);
  passed++;
} else {
  console.log(`❌ Analysis: Expected multiple issues, found ${analysis.length}`);
  failed++;
}

console.log('');
console.log('Testing UTF-8 safety check...');

for (const testCase of testCases) {
  const isSafe = isUtf8Safe(testCase.text);
  const expectedSafe = !testCase.expectIssues;
  
  if (isSafe === expectedSafe) {
    console.log(`✅ ${testCase.name}: Safety check correct (${isSafe ? 'safe' : 'unsafe'})`);
    passed++;
  } else {
    console.log(`❌ ${testCase.name}: Expected ${expectedSafe ? 'safe' : 'unsafe'}, got ${isSafe ? 'safe' : 'unsafe'}`);
    failed++;
  }
}

console.log('');
console.log('📊 Test Results:');
console.log(`Passed: ${passed}`);
console.log(`Failed: ${failed}`);
console.log(`Total: ${passed + failed}`);
console.log(`Success rate: ${((passed / (passed + failed)) * 100).toFixed(1)}%`);

if (failed === 0) {
  console.log('');
  console.log('🎉 All tests passed!');
  process.exit(0);
} else {
  console.log('');
  console.log('❌ Some tests failed. Please check the implementation.');
  process.exit(1);
}