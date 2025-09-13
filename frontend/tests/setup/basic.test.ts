import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

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

  it('should support mocking with vi globals', () => {
    const mockFn = vi.fn(() => 'mocked');
    expect(mockFn()).toBe('mocked');
    expect(mockFn).toHaveBeenCalledTimes(1);
  });

  it('should have React available', () => {
    expect(React).toBeDefined();
    expect(React.version).toBeDefined();
  });

  it('should support React Testing Library', () => {
    const TestComponent = () => React.createElement('div', null, 'Hello Test');
    render(React.createElement(TestComponent));
    expect(screen.getByText('Hello Test')).toBeInTheDocument();
  });

  it('should have proper DOM environment', () => {
    expect(document).toBeDefined();
    expect(window).toBeDefined();
    expect(global.performance).toBeDefined();
  });
});