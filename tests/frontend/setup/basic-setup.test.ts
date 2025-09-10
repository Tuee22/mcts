import { describe, it, expect } from 'vitest';

describe('Basic Test Setup Verification', () => {
  it('should run basic vitest tests', () => {
    expect(true).toBe(true);
  });

  it('should have access to modern JavaScript features', () => {
    const arr = [1, 2, 3];
    const doubled = arr.map(x => x * 2);
    expect(doubled).toEqual([2, 4, 6]);
  });

  it('should support async/await', async () => {
    const promise = new Promise(resolve => setTimeout(() => resolve('done'), 1));
    const result = await promise;
    expect(result).toBe('done');
  });

  it('should have proper test isolation', () => {
    // Each test should run independently
    const testData = { count: 0 };
    testData.count++;
    expect(testData.count).toBe(1);
  });

  it('should support mocking', () => {
    const mockFn = vi.fn(() => 'mocked');
    expect(mockFn()).toBe('mocked');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });
});