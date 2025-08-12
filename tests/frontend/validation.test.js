/**
 * Basic validation test to ensure the test setup is working correctly
 */

describe('Test Environment Validation', () => {
  it('can run basic assertions', () => {
    expect(true).toBe(true);
    expect(1 + 1).toBe(2);
    expect('hello').toMatch(/hello/);
  });

  it('has access to DOM APIs', () => {
    expect(document).toBeDefined();
    expect(window).toBeDefined();
    expect(localStorage).toBeDefined();
  });

  it('can test async operations', async () => {
    const promise = Promise.resolve(42);
    const result = await promise;
    expect(result).toBe(42);
  });

  it('can use modern JavaScript features', () => {
    const arr = [1, 2, 3];
    const doubled = arr.map(x => x * 2);
    expect(doubled).toEqual([2, 4, 6]);

    const obj = { a: 1, b: 2 };
    const spread = { ...obj, c: 3 };
    expect(spread).toEqual({ a: 1, b: 2, c: 3 });
  });

  it('can handle errors properly', () => {
    expect(() => {
      throw new Error('test error');
    }).toThrow('test error');
  });

  it('supports timer mocking', () => {
    jest.useFakeTimers();
    
    const callback = jest.fn();
    setTimeout(callback, 1000);
    
    expect(callback).not.toHaveBeenCalled();
    
    jest.advanceTimersByTime(1000);
    expect(callback).toHaveBeenCalled();
    
    jest.useRealTimers();
  });
});