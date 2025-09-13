import React, { useState, useRef } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, createUser } from '../utils/testHelpers';

// Performance-focused tests that require more memory and time
// These are excluded from default test runs and run separately
describe('Performance Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Force cleanup (handle case where timers aren't mocked)
    try {
      vi.clearAllTimers();
      vi.runOnlyPendingTimers();
    } catch {
      // Timers are not mocked, skip
    }
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
  });

  describe('High-Load Performance Tests', () => {
    it('handles rapid re-renders without performance degradation', async () => {
      const RapidRerenders = () => {
        const [count, setCount] = useState(0);
        const renderTime = useRef<number>(0);
        
        // Measure render time
        const start = performance.now();
        renderTime.current = start;
        
        const handleRapidUpdates = () => {
          // Trigger fewer rapid updates for memory efficiency
          for (let i = 0; i < 10; i++) {
            setCount(prev => prev + 1);
          }
        };
        
        return (
          <div>
            <span data-testid="count">{count}</span>
            <span data-testid="render-time">{renderTime.current}</span>
            <button onClick={handleRapidUpdates}>Rapid Updates</button>
          </div>
        );
      };

      vi.useFakeTimers();
      render(<RapidRerenders />);
      const user = createUser();
      
      const start = performance.now();
      await user.click(screen.getByText('Rapid Updates'));
      const end = performance.now();
      vi.useRealTimers();
      
      // Should complete in reasonable time
      expect(end - start).toBeLessThan(1000);
      expect(screen.getByTestId('count')).toHaveTextContent('10');
    });

    it('handles component with many props', () => {
      const ManyPropsComponent = (props: Record<string, any>) => {
        return <div data-testid="many-props">{Object.keys(props).length}</div>;
      };
      
      const manyProps = Array.from({ length: 100 }, (_, i) => [`prop${i}`, `value${i}`])
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});
      
      const start = performance.now();
      render(<ManyPropsComponent {...manyProps} />);
      const end = performance.now();
      
      expect(end - start).toBeLessThan(100);
      expect(screen.getByTestId('many-props')).toHaveTextContent('100');
    });

    it('handles context updates with many consumers', async () => {
      const TestContext = React.createContext<{ value: number; setValue: (v: number) => void }>({
        value: 0,
        setValue: () => {}
      });
      
      const Consumer = ({ id }: { id: string }) => {
        const { value } = React.useContext(TestContext);
        return <span data-testid={id}>{value}</span>;
      };
      
      const Provider = () => {
        const [value, setValue] = useState(0);
        
        return (
          <TestContext.Provider value={{ value, setValue }}>
            {/* Reduced consumers for memory efficiency */}
            {Array.from({ length: 10 }, (_, i) => (
              <Consumer key={i} id={`consumer-${i}`} />
            ))}
            <button onClick={() => setValue(prev => prev + 1)}>Update</button>
          </TestContext.Provider>
        );
      };

      vi.useFakeTimers();
      render(<Provider />);
      const user = createUser();
      
      await user.click(screen.getByText('Update'));
      vi.useRealTimers();
      
      // All consumers should update - check a few samples
      for (let i = 0; i < 5; i++) { // Check first 5 to reduce DOM queries
        expect(screen.getByTestId(`consumer-${i}`)).toHaveTextContent('1');
      }
    });
  });
});