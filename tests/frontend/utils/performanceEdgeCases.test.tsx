import React, { useState, useMemo, useCallback, memo } from 'react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '../utils/testHelpers';
import { measureRenderTime, createMemoryLeakDetector } from '../utils/testHelpers';

describe('Performance Edge Cases', () => {
  let memoryDetector: ReturnType<typeof createMemoryLeakDetector>;

  beforeEach(() => {
    vi.clearAllMocks();
    memoryDetector = createMemoryLeakDetector();
  });

  afterEach(() => {
    memoryDetector.check();
  });

  describe('Large List Rendering', () => {
    it('handles rendering 1000 items efficiently', async () => {
      const LargeList = () => {
        const items = Array.from({ length: 1000 }, (_, i) => ({
          id: i,
          text: `Item ${i}`,
          value: Math.random()
        }));

        return (
          <div data-testid="large-list">
            {items.map(item => (
              <div key={item.id} data-testid={`item-${item.id}`}>
                {item.text} - {item.value.toFixed(3)}
              </div>
            ))}
          </div>
        );
      };

      const renderTime = await measureRenderTime(() => {
        render(<LargeList />);
      });

      // Should render in reasonable time
      expect(renderTime).toBeLessThan(200);
      expect(screen.getByTestId('large-list')).toBeInTheDocument();
      expect(screen.getByTestId('item-0')).toBeInTheDocument();
      expect(screen.getByTestId('item-999')).toBeInTheDocument();
    });

    it('handles frequent list updates efficiently', async () => {
      const UpdatingList = () => {
        const [items, setItems] = useState(
          Array.from({ length: 100 }, (_, i) => ({ id: i, count: 0 }))
        );

        const updateRandomItem = useCallback(() => {
          const randomIndex = Math.floor(Math.random() * items.length);
          setItems(prev => prev.map((item, index) => 
            index === randomIndex 
              ? { ...item, count: item.count + 1 }
              : item
          ));
        }, [items.length]);

        return (
          <div>
            <button onClick={updateRandomItem}>Update Random</button>
            {items.map(item => (
              <div key={item.id} data-testid={`item-${item.id}`}>
                Item {item.id}: {item.count}
              </div>
            ))}
          </div>
        );
      };

      const { user } = render(<UpdatingList />);

      // Perform multiple rapid updates
      const start = performance.now();
      for (let i = 0; i < 20; i++) {
        await user.click(screen.getByText('Update Random'));
      }
      const end = performance.now();

      expect(end - start).toBeLessThan(500); // Should handle rapid updates
    });

    it('handles list with complex items', async () => {
      const ComplexItem = memo(({ item }: { item: any }) => {
        // Expensive computation
        const expensiveValue = useMemo(() => {
          let result = 0;
          for (let i = 0; i < 1000; i++) {
            result += Math.sin(item.value * i);
          }
          return result;
        }, [item.value]);

        return (
          <div data-testid={`complex-item-${item.id}`}>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
            <span>Computed: {expensiveValue.toFixed(3)}</span>
          </div>
        );
      });

      const ComplexList = () => {
        const items = Array.from({ length: 50 }, (_, i) => ({
          id: i,
          title: `Complex Item ${i}`,
          description: `Description for item ${i}`.repeat(10),
          value: Math.random()
        }));

        return (
          <div data-testid="complex-list">
            {items.map(item => (
              <ComplexItem key={item.id} item={item} />
            ))}
          </div>
        );
      };

      const renderTime = await measureRenderTime(() => {
        render(<ComplexList />);
      });

      expect(renderTime).toBeLessThan(1000); // Complex but should still be reasonable
      expect(screen.getByTestId('complex-list')).toBeInTheDocument();
    });
  });

  describe('State Update Performance', () => {
    it('handles deep object updates efficiently', async () => {
      const DeepObjectComponent = () => {
        const [state, setState] = useState({
          level1: {
            level2: {
              level3: {
                level4: {
                  level5: {
                    value: 0,
                    array: Array.from({ length: 100 }, (_, i) => i)
                  }
                }
              }
            }
          }
        });

        const updateDeepValue = useCallback(() => {
          setState(prevState => ({
            ...prevState,
            level1: {
              ...prevState.level1,
              level2: {
                ...prevState.level1.level2,
                level3: {
                  ...prevState.level1.level2.level3,
                  level4: {
                    ...prevState.level1.level2.level3.level4,
                    level5: {
                      ...prevState.level1.level2.level3.level4.level5,
                      value: prevState.level1.level2.level3.level4.level5.value + 1
                    }
                  }
                }
              }
            }
          }));
        }, []);

        return (
          <div>
            <span data-testid="deep-value">
              {state.level1.level2.level3.level4.level5.value}
            </span>
            <button onClick={updateDeepValue}>Update Deep</button>
          </div>
        );
      };

      const { user } = render(<DeepObjectComponent />);

      const start = performance.now();
      for (let i = 0; i < 10; i++) {
        await user.click(screen.getByText('Update Deep'));
      }
      const end = performance.now();

      expect(end - start).toBeLessThan(100);
      expect(screen.getByTestId('deep-value')).toHaveTextContent('10');
    });

    it('handles frequent small updates vs infrequent large updates', async () => {
      const UpdateStrategies = () => {
        const [smallUpdates, setSmallUpdates] = useState(0);
        const [largeUpdates, setLargeUpdates] = useState(
          Array.from({ length: 1000 }, () => 0)
        );

        const doSmallUpdates = useCallback(() => {
          // Many small updates
          for (let i = 0; i < 100; i++) {
            setSmallUpdates(prev => prev + 1);
          }
        }, []);

        const doLargeUpdate = useCallback(() => {
          // One large update
          setLargeUpdates(prev => prev.map(val => val + 100));
        }, []);

        return (
          <div>
            <span data-testid="small-updates">{smallUpdates}</span>
            <span data-testid="large-updates">{largeUpdates[0]}</span>
            <button onClick={doSmallUpdates}>Small Updates</button>
            <button onClick={doLargeUpdate}>Large Update</button>
          </div>
        );
      };

      const { user } = render(<UpdateStrategies />);

      // Test small updates
      const smallStart = performance.now();
      await user.click(screen.getByText('Small Updates'));
      const smallEnd = performance.now();

      // Test large update  
      const largeStart = performance.now();
      await user.click(screen.getByText('Large Update'));
      const largeEnd = performance.now();

      const smallTime = smallEnd - smallStart;
      const largeTime = largeEnd - largeStart;

      expect(smallTime).toBeLessThan(200);
      expect(largeTime).toBeLessThan(100);
      expect(screen.getByTestId('small-updates')).toHaveTextContent('100');
      expect(screen.getByTestId('large-updates')).toHaveTextContent('100');
    });
  });

  describe('Memory Usage Patterns', () => {
    it('handles component creation and destruction without leaks', () => {
      const LeakTestComponent = ({ count }: { count: number }) => {
        const data = useMemo(() => {
          // Create large data structure
          return Array.from({ length: 1000 }, (_, i) => ({
            id: i,
            data: new Array(100).fill(`data-${count}-${i}`)
          }));
        }, [count]);

        return (
          <div data-testid={`leak-test-${count}`}>
            Component {count} - {data.length} items
          </div>
        );
      };

      const LeakTestContainer = () => {
        const [count, setCount] = useState(0);
        const [components, setComponents] = useState<number[]>([]);

        const addComponent = () => {
          const newCount = count + 1;
          setCount(newCount);
          setComponents(prev => [...prev, newCount]);
        };

        const removeComponent = () => {
          setComponents(prev => prev.slice(0, -1));
        };

        return (
          <div>
            <button onClick={addComponent}>Add Component</button>
            <button onClick={removeComponent}>Remove Component</button>
            <span data-testid="component-count">{components.length}</span>
            {components.map(id => (
              <LeakTestComponent key={id} count={id} />
            ))}
          </div>
        );
      };

      const { user } = render(<LeakTestContainer />);

      // Add many components
      for (let i = 0; i < 10; i++) {
        user.click(screen.getByText('Add Component'));
      }

      expect(screen.getByTestId('component-count')).toHaveTextContent('10');

      // Remove all components
      for (let i = 0; i < 10; i++) {
        user.click(screen.getByText('Remove Component'));
      }

      expect(screen.getByTestId('component-count')).toHaveTextContent('0');
    });

    it('handles large state objects efficiently', () => {
      const LargeStateComponent = () => {
        const [largeState, setLargeState] = useState(() => {
          // Initialize with large state
          return {
            users: Array.from({ length: 1000 }, (_, i) => ({
              id: i,
              name: `User ${i}`,
              email: `user${i}@example.com`,
              profile: {
                avatar: `avatar${i}.jpg`,
                bio: `Bio for user ${i}`.repeat(10),
                settings: {
                  theme: 'dark',
                  notifications: true,
                  privacy: {
                    showEmail: false,
                    showProfile: true
                  }
                }
              }
            }))
          };
        });

        const updateRandomUser = useCallback(() => {
          const randomIndex = Math.floor(Math.random() * largeState.users.length);
          
          setLargeState(prevState => ({
            ...prevState,
            users: prevState.users.map((user, index) =>
              index === randomIndex
                ? {
                    ...user,
                    profile: {
                      ...user.profile,
                      settings: {
                        ...user.profile.settings,
                        theme: user.profile.settings.theme === 'dark' ? 'light' : 'dark'
                      }
                    }
                  }
                : user
            )
          }));
        }, [largeState.users.length]);

        return (
          <div>
            <span data-testid="user-count">{largeState.users.length}</span>
            <button onClick={updateRandomUser}>Update Random User</button>
          </div>
        );
      };

      const start = performance.now();
      const { user } = render(<LargeStateComponent />);
      const renderEnd = performance.now();

      expect(renderEnd - start).toBeLessThan(500);
      expect(screen.getByTestId('user-count')).toHaveTextContent('1000');

      // Test update performance
      const updateStart = performance.now();
      user.click(screen.getByText('Update Random User'));
      const updateEnd = performance.now();

      expect(updateEnd - updateStart).toBeLessThan(50);
    });
  });

  describe('Render Optimization Edge Cases', () => {
    it('handles unnecessary re-renders with React.memo', () => {
      const renderSpy = vi.fn();

      const ExpensiveChild = memo(({ value, onRender }: { value: number; onRender: () => void }) => {
        onRender();
        
        // Simulate expensive rendering
        const result = useMemo(() => {
          let sum = 0;
          for (let i = 0; i < 10000; i++) {
            sum += Math.sin(value * i);
          }
          return sum;
        }, [value]);

        return <div data-testid="expensive-child">{result.toFixed(3)}</div>;
      });

      const OptimizationTest = () => {
        const [parentCount, setParentCount] = useState(0);
        const [childValue, setChildValue] = useState(1);

        const stableCallback = useCallback(() => {
          renderSpy();
        }, []); // Stable callback

        return (
          <div>
            <span data-testid="parent-count">{parentCount}</span>
            <button onClick={() => setParentCount(prev => prev + 1)}>
              Update Parent
            </button>
            <button onClick={() => setChildValue(prev => prev + 1)}>
              Update Child
            </button>
            <ExpensiveChild value={childValue} onRender={stableCallback} />
          </div>
        );
      };

      const { user } = render(<OptimizationTest />);

      expect(renderSpy).toHaveBeenCalledTimes(1); // Initial render

      // Update parent - child should not re-render due to memo
      user.click(screen.getByText('Update Parent'));
      expect(renderSpy).toHaveBeenCalledTimes(1); // Still 1

      // Update child - should re-render
      user.click(screen.getByText('Update Child'));
      expect(renderSpy).toHaveBeenCalledTimes(2); // Now 2
    });

    it('handles useMemo dependency changes correctly', () => {
      const computationSpy = vi.fn();

      const MemoComponent = ({ a, b, c }: { a: number; b: number; c: number }) => {
        const expensiveComputation = useMemo(() => {
          computationSpy();
          
          // Expensive computation
          let result = 0;
          for (let i = 0; i < 1000; i++) {
            result += a * Math.sin(b * i) + c;
          }
          return result;
        }, [a, b]); // Note: c is NOT in dependencies

        return (
          <div data-testid="memo-result">
            {expensiveComputation.toFixed(3)} (c={c})
          </div>
        );
      };

      const { rerender } = render(<MemoComponent a={1} b={2} c={3} />);
      expect(computationSpy).toHaveBeenCalledTimes(1);

      // Change c - should NOT recompute due to missing dependency
      rerender(<MemoComponent a={1} b={2} c={4} />);
      expect(computationSpy).toHaveBeenCalledTimes(1);

      // Change a - should recompute
      rerender(<MemoComponent a={2} b={2} c={4} />);
      expect(computationSpy).toHaveBeenCalledTimes(2);

      // Change b - should recompute
      rerender(<MemoComponent a={2} b={3} c={4} />);
      expect(computationSpy).toHaveBeenCalledTimes(3);
    });
  });

  describe('Animation Performance', () => {
    it('handles many concurrent animations', () => {
      vi.useFakeTimers();

      const AnimatedComponent = ({ id }: { id: number }) => {
        const [position, setPosition] = useState(0);

        React.useEffect(() => {
          const animate = () => {
            setPosition(prev => (prev + 1) % 100);
          };

          const interval = setInterval(animate, 16); // ~60fps
          return () => clearInterval(interval);
        }, []);

        return (
          <div
            data-testid={`animated-${id}`}
            style={{ transform: `translateX(${position}px)` }}
          >
            Item {id}
          </div>
        );
      };

      const ManyAnimations = () => {
        const items = Array.from({ length: 50 }, (_, i) => i);

        return (
          <div data-testid="animation-container">
            {items.map(id => (
              <AnimatedComponent key={id} id={id} />
            ))}
          </div>
        );
      };

      const start = performance.now();
      render(<ManyAnimations />);
      const end = performance.now();

      expect(end - start).toBeLessThan(200);

      // Run animations for a bit
      vi.advanceTimersByTime(100);

      expect(screen.getByTestId('animation-container')).toBeInTheDocument();
      expect(screen.getByTestId('animated-0')).toBeInTheDocument();

      vi.useRealTimers();
    });

    it('handles requestAnimationFrame performance', () => {
      vi.useFakeTimers();

      const rafCallbacks: Array<() => void> = [];
      let frameCount = 0;

      // Mock RAF to collect callbacks
      const mockRAF = vi.fn((callback) => {
        rafCallbacks.push(callback);
        return ++frameCount;
      });

      global.requestAnimationFrame = mockRAF;

      const RAFComponent = () => {
        const [frame, setFrame] = useState(0);

        React.useEffect(() => {
          const animate = () => {
            setFrame(prev => prev + 1);
            requestAnimationFrame(animate);
          };

          requestAnimationFrame(animate);
        }, []);

        return <div data-testid="raf-frame">{frame}</div>;
      };

      render(<RAFComponent />);

      expect(mockRAF).toHaveBeenCalled();

      // Execute several animation frames
      for (let i = 0; i < 10; i++) {
        rafCallbacks.forEach(callback => callback());
      }

      expect(screen.getByTestId('raf-frame')).toHaveTextContent('10');

      vi.useRealTimers();
    });
  });

  describe('Bundle Size Implications', () => {
    it('handles dynamic imports efficiently', async () => {
      const DynamicImportComponent = () => {
        const [Component, setComponent] = useState<React.ComponentType | null>(null);

        const loadComponent = async () => {
          // Simulate dynamic import
          const module = await new Promise<{ default: React.ComponentType }>(resolve => {
            setTimeout(() => {
              resolve({
                default: () => <div data-testid="dynamic-component">Dynamic!</div>
              });
            }, 10);
          });

          setComponent(() => module.default);
        };

        React.useEffect(() => {
          loadComponent();
        }, []);

        return Component ? <Component /> : <div>Loading...</div>;
      };

      render(<DynamicImportComponent />);

      expect(screen.getByText('Loading...')).toBeInTheDocument();

      await screen.findByTestId('dynamic-component');
      expect(screen.getByTestId('dynamic-component')).toHaveTextContent('Dynamic!');
    });

    it('handles tree shaking scenarios', () => {
      // Simulate a large utility library
      const largeUtilLibrary = {
        functionA: () => 'A',
        functionB: () => 'B',
        functionC: () => 'C',
        // ... imagine 100 more functions
        heavyFunction: () => {
          // Heavy computation that should be tree-shaken if unused
          let result = 0;
          for (let i = 0; i < 1000000; i++) {
            result += Math.random();
          }
          return result;
        }
      };

      const TreeShakingComponent = () => {
        // Only use one function - others should be tree-shaken
        const result = largeUtilLibrary.functionA();

        return <div data-testid="tree-shaking">{result}</div>;
      };

      const start = performance.now();
      render(<TreeShakingComponent />);
      const end = performance.now();

      expect(end - start).toBeLessThan(50);
      expect(screen.getByTestId('tree-shaking')).toHaveTextContent('A');
    });
  });
});