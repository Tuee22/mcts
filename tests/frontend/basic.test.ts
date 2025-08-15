import { describe, test, expect } from 'vitest';

describe('Basic Infrastructure Tests', () => {
  test('vitest is working', () => {
    expect(true).toBe(true);
  });

  test('math works', () => {
    expect(2 + 2).toBe(4);
  });

  test('string operations work', () => {
    expect('hello'.toUpperCase()).toBe('HELLO');
  });
});