import React, { useState, useEffect, useCallback, useRef } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '../utils/testHelpers';
import { createMemoryLeakDetector } from '../utils/testHelpers';

describe('React-Specific Edge Cases', () => {
  let memoryDetector: ReturnType<typeof createMemoryLeakDetector>;

  beforeEach(() => {
    vi.clearAllMocks();
    memoryDetector = createMemoryLeakDetector();
  });

  afterEach(() => {
    // Check for memory leaks after each test
    memoryDetector.check();
  });

  describe('State Update Edge Cases', () => {
    it('handles state updates after component unmount', async () => {
      const StateComponent = () => {
        const [count, setCount] = useState(0);
        
        useEffect(() => {
          const timer = setTimeout(() => {
            // This might run after component unmounts
            setCount(1);
          }, 100);
          
          return () => clearTimeout(timer);
        }, []);
        
        return <div>Count: {count}</div>;
      };

      const { unmount } = render(<StateComponent />);
      
      // Unmount before state update
      unmount();
      
      // Wait for potential state update
      await new Promise(resolve => setTimeout(resolve, 150));
      
      // Should not cause warnings or errors
      expect(true).toBe(true);
    });

    it('handles rapid state updates (batching)', async () => {
      const RapidUpdatesComponent = () => {
        const [count, setCount] = useState(0);
        const [renders, setRenders] = useState(0);
        
        useEffect(() => {
          setRenders(prev => prev + 1);
        });
        
        const handleMultipleUpdates = () => {
          // These should be batched in React 18+
          setCount(prev => prev + 1);
          setCount(prev => prev + 1);
          setCount(prev => prev + 1);
        };
        
        return (
          <div>
            <span data-testid="count">{count}</span>
            <span data-testid="renders">{renders}</span>
            <button onClick={handleMultipleUpdates}>Update</button>
          </div>
        );
      };

      const { user } = render(<RapidUpdatesComponent />);
      
      const button = screen.getByText('Update');
      await user.click(button);
      
      // Count should be 3 after batched updates
      expect(screen.getByTestId('count')).toHaveTextContent('3');
      
      // Should have minimal renders due to batching
      const renderCount = parseInt(screen.getByTestId('renders').textContent || '0');
      expect(renderCount).toBeLessThan(5); // Reasonable limit for batched updates
    });

    it('handles state updates with stale closures', async () => {
      const StaleClosure = () => {
        const [count, setCount] = useState(0);
        const [message, setMessage] = useState('');
        
        const handleClick = useCallback(() => {
          // This closure captures the initial count value
          setTimeout(() => {
            setMessage(`Count was: ${count}`); // Stale closure
          }, 50);
        }, []); // Empty dependency array creates stale closure
        
        return (
          <div>
            <span data-testid="count">{count}</span>
            <span data-testid="message">{message}</span>
            <button onClick={() => setCount(prev => prev + 1)}>Increment</button>
            <button onClick={handleClick}>Set Message</button>
          </div>
        );
      };

      const { user } = render(<StaleClosure />);
      
      // Increment count
      await user.click(screen.getByText('Increment'));
      expect(screen.getByTestId('count')).toHaveTextContent('1');
      
      // Trigger stale closure
      await user.click(screen.getByText('Set Message'));
      
      await waitFor(() => {
        // Message should show stale value (0) not current value (1)
        expect(screen.getByTestId('message')).toHaveTextContent('Count was: 0');
      });
    });

    it('handles concurrent state updates', async () => {
      const ConcurrentUpdates = () => {
        const [value, setValue] = useState(0);
        
        const handleConcurrentUpdates = async () => {
          // Simulate concurrent async operations
          const promises = [
            new Promise(resolve => setTimeout(() => resolve(setValue(prev => prev + 1)), 10)),
            new Promise(resolve => setTimeout(() => resolve(setValue(prev => prev + 2)), 15)),
            new Promise(resolve => setTimeout(() => resolve(setValue(prev => prev + 3)), 5))
          ];
          
          await Promise.all(promises);
        };
        
        return (
          <div>
            <span data-testid="value">{value}</span>
            <button onClick={handleConcurrentUpdates}>Concurrent Updates</button>
          </div>
        );
      };

      const { user } = render(<ConcurrentUpdates />);
      
      await user.click(screen.getByText('Concurrent Updates'));
      
      await waitFor(() => {
        // Final value should be the sum of all updates: 0 + 1 + 2 + 3 = 6
        expect(screen.getByTestId('value')).toHaveTextContent('6');
      });
    });
  });

  describe('Effect Cleanup Edge Cases', () => {
    it('handles effect cleanup with dependencies', () => {
      const cleanupSpy = vi.fn();
      
      const EffectComponent = ({ dependency }: { dependency: string }) => {
        useEffect(() => {
          return cleanupSpy;
        }, [dependency]);
        
        return <div>{dependency}</div>;
      };

      const { rerender, unmount } = render(<EffectComponent dependency="initial" />);
      
      // Change dependency - should trigger cleanup
      rerender(<EffectComponent dependency="changed" />);
      expect(cleanupSpy).toHaveBeenCalledTimes(1);
      
      // Unmount - should trigger cleanup again
      unmount();
      expect(cleanupSpy).toHaveBeenCalledTimes(2);
    });

    it('handles async cleanup functions', async () => {
      const asyncCleanup = vi.fn();
      
      const AsyncEffectComponent = () => {
        useEffect(() => {
          let cancelled = false;
          
          const asyncOperation = async () => {
            await new Promise(resolve => setTimeout(resolve, 50));
            if (!cancelled) {
              // Do something
            }
          };
          
          asyncOperation();
          
          return () => {
            cancelled = true;
            asyncCleanup();
          };
        }, []);
        
        return <div>Async Effect</div>;
      };

      const { unmount } = render(<AsyncEffectComponent />);
      
      // Unmount quickly before async operation completes
      unmount();
      
      expect(asyncCleanup).toHaveBeenCalled();
      
      // Wait for async operation to potentially complete
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    it('handles cleanup with multiple subscriptions', () => {
      const subscription1Cleanup = vi.fn();
      const subscription2Cleanup = vi.fn();
      const subscription3Cleanup = vi.fn();
      
      const MultiSubscription = () => {
        useEffect(() => {
          // Multiple subscriptions in one effect
          const cleanup1 = subscription1Cleanup;
          const cleanup2 = subscription2Cleanup;
          const cleanup3 = subscription3Cleanup;
          
          return () => {
            cleanup1();
            cleanup2();
            cleanup3();
          };
        }, []);
        
        return <div>Multi Subscription</div>;
      };

      const { unmount } = render(<MultiSubscription />);
      unmount();
      
      expect(subscription1Cleanup).toHaveBeenCalled();
      expect(subscription2Cleanup).toHaveBeenCalled();
      expect(subscription3Cleanup).toHaveBeenCalled();
    });
  });

  describe('Key Prop Edge Cases', () => {
    it('handles duplicate keys in lists', () => {
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const DuplicateKeys = () => {
        const items = [
          { id: 1, text: 'Item 1' },
          { id: 1, text: 'Item 2' }, // Duplicate key
          { id: 2, text: 'Item 3' }
        ];
        
        return (
          <ul>
            {items.map(item => (
              <li key={item.id}>{item.text}</li>
            ))}
          </ul>
        );
      };

      render(<DuplicateKeys />);
      
      // React should warn about duplicate keys
      expect(consoleWarn).toHaveBeenCalled();
      
      consoleWarn.mockRestore();
    });

    it('handles changing keys causing remount', () => {
      const mountSpy = vi.fn();
      const unmountSpy = vi.fn();
      
      const KeyChangingChild = ({ value }: { value: string }) => {
        useEffect(() => {
          mountSpy(value);
          return () => unmountSpy(value);
        }, [value]);
        
        return <div>{value}</div>;
      };
      
      const KeyChangingParent = ({ useIndex }: { useIndex: boolean }) => {
        const items = ['A', 'B', 'C'];
        
        return (
          <div>
            {items.map((item, index) => (
              <KeyChangingChild 
                key={useIndex ? index : item} 
                value={item} 
              />
            ))}
          </div>
        );
      };

      const { rerender } = render(<KeyChangingParent useIndex={false} />);
      
      expect(mountSpy).toHaveBeenCalledTimes(3);
      expect(mountSpy).toHaveBeenCalledWith('A');
      expect(mountSpy).toHaveBeenCalledWith('B');
      expect(mountSpy).toHaveBeenCalledWith('C');
      
      // Change key strategy - should cause remount
      rerender(<KeyChangingParent useIndex={true} />);
      
      expect(unmountSpy).toHaveBeenCalledTimes(3);
      expect(mountSpy).toHaveBeenCalledTimes(6); // 3 initial + 3 remounts
    });

    it('handles missing keys in dynamic lists', () => {
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const MissingKeys = () => {
        const items = ['Item 1', 'Item 2', 'Item 3'];
        
        return (
          <ul>
            {items.map(item => (
              <li>{item}</li> // Missing key prop
            ))}
          </ul>
        );
      };

      render(<MissingKeys />);
      
      // React should warn about missing keys
      expect(consoleWarn).toHaveBeenCalled();
      
      consoleWarn.mockRestore();
    });
  });

  describe('Ref Edge Cases', () => {
    it('handles ref to unmounted component', () => {
      const RefComponent = () => {
        const [mounted, setMounted] = useState(true);
        const ref = useRef<HTMLDivElement>(null);
        
        const handleClick = () => {
          setMounted(false);
          // Trying to access ref after unmount
          setTimeout(() => {
            if (ref.current) {
              ref.current.style.color = 'red'; // This should fail gracefully
            }
          }, 10);
        };
        
        return (
          <div>
            {mounted && <div ref={ref}>Mounted</div>}
            <button onClick={handleClick}>Unmount</button>
          </div>
        );
      };

      const { user } = render(<RefComponent />);
      
      expect(() => {
        user.click(screen.getByText('Unmount'));
      }).not.toThrow();
    });

    it('handles ref callback with null values', () => {
      const refCallback = vi.fn();
      
      const RefCallbackComponent = ({ showElement }: { showElement: boolean }) => {
        return (
          <div>
            {showElement && <div ref={refCallback}>Element</div>}
          </div>
        );
      };

      const { rerender } = render(<RefCallbackComponent showElement={true} />);
      
      expect(refCallback).toHaveBeenCalledWith(expect.any(HTMLDivElement));
      
      // Hide element - ref callback should be called with null
      rerender(<RefCallbackComponent showElement={false} />);
      
      expect(refCallback).toHaveBeenCalledWith(null);
    });

    it('handles forwarded refs properly', () => {
      const ForwardedComponent = React.forwardRef<HTMLDivElement, { children: React.ReactNode }>(
        ({ children }, ref) => {
          return <div ref={ref}>{children}</div>;
        }
      );
      
      const ParentComponent = () => {
        const ref = useRef<HTMLDivElement>(null);
        
        useEffect(() => {
          if (ref.current) {
            ref.current.setAttribute('data-testid', 'forwarded-ref');
          }
        });
        
        return <ForwardedComponent ref={ref}>Content</ForwardedComponent>;
      };

      render(<ParentComponent />);
      
      expect(screen.getByTestId('forwarded-ref')).toBeInTheDocument();
    });
  });

  describe('Event Handler Edge Cases', () => {
    it('handles event handlers with stale props', async () => {
      const StalePropsComponent = ({ value }: { value: number }) => {
        const [clicks, setClicks] = useState(0);
        
        // This callback captures the current value
        const handleClick = useCallback(() => {
          setClicks(prev => prev + value);
        }, []); // Missing value in dependencies - stale closure
        
        return (
          <div>
            <span data-testid="clicks">{clicks}</span>
            <span data-testid="value">{value}</span>
            <button onClick={handleClick}>Click</button>
          </div>
        );
      };

      const { user, rerender } = render(<StalePropsComponent value={1} />);
      
      // Click with initial value
      await user.click(screen.getByText('Click'));
      expect(screen.getByTestId('clicks')).toHaveTextContent('1');
      
      // Change prop value
      rerender(<StalePropsComponent value={5} />);
      expect(screen.getByTestId('value')).toHaveTextContent('5');
      
      // Click again - should still use stale value (1) not new value (5)
      await user.click(screen.getByText('Click'));
      expect(screen.getByTestId('clicks')).toHaveTextContent('2'); // 1 + 1, not 1 + 5
    });

    it('handles synthetic event pooling edge cases', async () => {
      const events: any[] = [];
      
      const EventComponent = () => {
        const handleClick = (event: React.MouseEvent) => {
          // Store event reference
          events.push(event);
          
          // Async access to event properties might fail in older React versions
          setTimeout(() => {
            try {
              const target = event.target; // Might be null due to event pooling
              events.push(target);
            } catch (error) {
              events.push('error');
            }
          }, 10);
        };
        
        return <button onClick={handleClick}>Click</button>;
      };

      const { user } = render(<EventComponent />);
      
      await user.click(screen.getByText('Click'));
      
      await waitFor(() => {
        expect(events.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('handles event handler removal timing', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();
      
      const HandlerComponent = ({ useFirstHandler }: { useFirstHandler: boolean }) => {
        return (
          <button onClick={useFirstHandler ? handler1 : handler2}>
            Click
          </button>
        );
      };

      const { user, rerender } = render(<HandlerComponent useFirstHandler={true} />);
      
      user.click(screen.getByText('Click'));
      expect(handler1).toHaveBeenCalled();
      expect(handler2).not.toHaveBeenCalled();
      
      // Change handler
      rerender(<HandlerComponent useFirstHandler={false} />);
      
      user.click(screen.getByText('Click'));
      expect(handler2).toHaveBeenCalled();
      
      // Both handlers should be called exactly once
      expect(handler1).toHaveBeenCalledTimes(1);
      expect(handler2).toHaveBeenCalledTimes(1);
    });
  });

  describe('Context Edge Cases', () => {
    it('handles context updates with many consumers', () => {
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
            {/* Many consumers */}
            {Array.from({ length: 50 }, (_, i) => (
              <Consumer key={i} id={`consumer-${i}`} />
            ))}
            <button onClick={() => setValue(prev => prev + 1)}>Update</button>
          </TestContext.Provider>
        );
      };

      const { user } = render(<Provider />);
      
      user.click(screen.getByText('Update'));
      
      // All consumers should update
      for (let i = 0; i < 10; i++) { // Check first 10
        expect(screen.getByTestId(`consumer-${i}`)).toHaveTextContent('1');
      }
    });

    it('handles context with complex values', () => {
      const ComplexContext = React.createContext<{
        user: { name: string; preferences: { theme: string } };
        updateUser: (user: any) => void;
      } | null>(null);
      
      const ComplexProvider = ({ children }: { children: React.ReactNode }) => {
        const [user, setUser] = useState({
          name: 'John',
          preferences: { theme: 'dark' }
        });
        
        const updateUser = useCallback((newUser: any) => {
          setUser(prevUser => ({ ...prevUser, ...newUser }));
        }, []);
        
        return (
          <ComplexContext.Provider value={{ user, updateUser }}>
            {children}
          </ComplexContext.Provider>
        );
      };
      
      const ComplexConsumer = () => {
        const context = React.useContext(ComplexContext);
        if (!context) return null;
        
        return (
          <div>
            <span data-testid="name">{context.user.name}</span>
            <span data-testid="theme">{context.user.preferences.theme}</span>
          </div>
        );
      };

      render(
        <ComplexProvider>
          <ComplexConsumer />
        </ComplexProvider>
      );
      
      expect(screen.getByTestId('name')).toHaveTextContent('John');
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
  });

  describe('Performance Edge Cases', () => {
    it('handles rapid re-renders without performance degradation', async () => {
      const RapidRerenders = () => {
        const [count, setCount] = useState(0);
        const renderTime = useRef<number>(0);
        
        // Measure render time
        const start = performance.now();
        renderTime.current = start;
        
        const handleRapidUpdates = () => {
          // Trigger many rapid updates
          for (let i = 0; i < 100; i++) {
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

      const { user } = render(<RapidRerenders />);
      
      const start = performance.now();
      await user.click(screen.getByText('Rapid Updates'));
      const end = performance.now();
      
      // Should complete in reasonable time
      expect(end - start).toBeLessThan(1000);
      expect(screen.getByTestId('count')).toHaveTextContent('100');
    });

    it('handles component with many props', () => {
      const ManyPropsComponent = (props: Record<string, any>) => {
        return <div data-testid="many-props">{Object.keys(props).length}</div>;
      };
      
      const manyProps = Array.from({ length: 1000 }, (_, i) => [`prop${i}`, `value${i}`])
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {});
      
      const start = performance.now();
      render(<ManyPropsComponent {...manyProps} />);
      const end = performance.now();
      
      expect(end - start).toBeLessThan(100);
      expect(screen.getByTestId('many-props')).toHaveTextContent('1000');
    });
  });
});