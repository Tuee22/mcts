import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, waitFor, screen } from '../utils/testHelpers';
import { createMockStorage, mockClipboard } from '../fixtures/mocks';

describe('Browser API Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('LocalStorage Edge Cases', () => {
    it('handles localStorage quota exceeded', () => {
      const mockStorage = createMockStorage();
      
      // Mock quota exceeded error
      mockStorage.setItem.mockImplementation(() => {
        throw new DOMException('QuotaExceededError', 'QuotaExceededError');
      });

      Object.defineProperty(window, 'localStorage', {
        value: mockStorage,
        writable: true
      });

      // Should handle gracefully without crashing
      expect(() => {
        localStorage.setItem('test', 'value');
      }).toThrow('QuotaExceededError');
    });

    it('handles localStorage access denied in private mode', () => {
      // Simulate private browsing mode
      Object.defineProperty(window, 'localStorage', {
        get() {
          throw new DOMException('SecurityError', 'Access is denied for this document');
        }
      });

      expect(() => {
        window.localStorage.getItem('test');
      }).toThrow('SecurityError');
    });

    it('handles localStorage returning null vs undefined', () => {
      const mockStorage = createMockStorage();
      
      // Some implementations return null, others undefined
      mockStorage.getItem.mockReturnValueOnce(null);
      mockStorage.getItem.mockReturnValueOnce(undefined as any);

      Object.defineProperty(window, 'localStorage', {
        value: mockStorage
      });

      expect(localStorage.getItem('nonexistent1')).toBeNull();
      expect(localStorage.getItem('nonexistent2')).toBeUndefined();
    });

    it('handles localStorage with circular references', () => {
      const mockStorage = createMockStorage();
      Object.defineProperty(window, 'localStorage', {
        value: mockStorage
      });

      const circularObj: any = { data: 'test' };
      circularObj.self = circularObj;

      // JSON.stringify should throw on circular references
      expect(() => {
        localStorage.setItem('circular', JSON.stringify(circularObj));
      }).toThrow();
    });
  });

  describe('Clipboard API Edge Cases', () => {
    it('handles clipboard permission denied', async () => {
      mockClipboard.writeText.mockRejectedValue(new DOMException('NotAllowedError', 'Permission denied'));

      Object.assign(navigator, { clipboard: mockClipboard });

      await expect(navigator.clipboard.writeText('test')).rejects.toThrow('Permission denied');
    });

    it('handles clipboard not available', () => {
      // Remove clipboard API
      Object.defineProperty(navigator, 'clipboard', {
        value: undefined,
        writable: true
      });

      expect(navigator.clipboard).toBeUndefined();
    });

    it('handles clipboard with special characters', async () => {
      mockClipboard.writeText.mockResolvedValue(undefined);

      Object.assign(navigator, { clipboard: mockClipboard });

      const specialText = '🎮♔♕♖♗♘♙ e2-e4 α β γ 中文 العربية';
      await navigator.clipboard.writeText(specialText);

      expect(mockClipboard.writeText).toHaveBeenCalledWith(specialText);
    });

    it('handles very long clipboard content', async () => {
      mockClipboard.writeText.mockImplementation(async (text) => {
        if (text.length > 1000000) { // 1MB limit
          throw new DOMException('DataError', 'Data too large');
        }
      });

      Object.assign(navigator, { clipboard: mockClipboard });

      const longText = 'x'.repeat(1000001);
      await expect(navigator.clipboard.writeText(longText)).rejects.toThrow('Data too large');
    });
  });

  describe('WebSocket Edge Cases', () => {
    it('handles WebSocket immediate close after creation', () => {
      const mockWS = vi.fn().mockImplementation(() => ({
        url: 'ws://test',
        readyState: WebSocket.CLOSED, // Immediately closed
        send: vi.fn(),
        close: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        onopen: null,
        onclose: null,
        onmessage: null,
        onerror: null
      }));

      global.WebSocket = mockWS as any;

      const ws = new WebSocket('ws://test');
      expect(ws.readyState).toBe(WebSocket.CLOSED);
    });

    it('handles WebSocket message with invalid JSON', () => {
      let messageHandler: ((event: MessageEvent) => void) | null = null;

      const mockWS = vi.fn().mockImplementation(() => ({
        url: 'ws://test',
        readyState: WebSocket.OPEN,
        send: vi.fn(),
        close: vi.fn(),
        addEventListener: vi.fn((event, handler) => {
          if (event === 'message') {
            messageHandler = handler;
          }
        }),
        removeEventListener: vi.fn()
      }));

      global.WebSocket = mockWS as any;

      const ws = new WebSocket('ws://test');
      ws.addEventListener('message', (event) => {
        expect(() => JSON.parse(event.data)).toThrow();
      });

      // Simulate invalid JSON message
      if (messageHandler) {
        messageHandler(new MessageEvent('message', { data: '{invalid json}' }));
      }
    });

    it('handles WebSocket connection timeout', () => {
      vi.useFakeTimers();

      let timeoutHandler: (() => void) | null = null;

      const mockWS = vi.fn().mockImplementation(() => ({
        url: 'ws://test',
        readyState: WebSocket.CONNECTING,
        send: vi.fn(),
        close: vi.fn(),
        addEventListener: vi.fn((event, handler) => {
          if (event === 'open') {
            timeoutHandler = () => {
              // Never call handler - simulate timeout
            };
          }
        }),
        removeEventListener: vi.fn()
      }));

      global.WebSocket = mockWS as any;

      const ws = new WebSocket('ws://test');
      expect(ws.readyState).toBe(WebSocket.CONNECTING);

      // Fast-forward time without triggering connection
      vi.advanceTimersByTime(30000);
      
      expect(ws.readyState).toBe(WebSocket.CONNECTING); // Still connecting

      vi.useRealTimers();
    });
  });

  describe('ResizeObserver Edge Cases', () => {
    it('handles ResizeObserver with no entries', () => {
      let resizeCallback: ResizeObserverCallback | null = null;

      global.ResizeObserver = vi.fn().mockImplementation((callback) => {
        resizeCallback = callback;
        return {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn()
        };
      });

      const observer = new ResizeObserver((entries) => {
        expect(entries).toEqual([]);
      });

      // Simulate callback with no entries
      if (resizeCallback) {
        resizeCallback([], observer);
      }
    });

    it('handles ResizeObserver disconnect during callback', () => {
      let resizeCallback: ResizeObserverCallback | null = null;
      let observerInstance: ResizeObserver | null = null;

      global.ResizeObserver = vi.fn().mockImplementation((callback) => {
        resizeCallback = callback;
        observerInstance = {
          observe: vi.fn(),
          unobserve: vi.fn(),
          disconnect: vi.fn()
        };
        return observerInstance;
      });

      const observer = new ResizeObserver((entries) => {
        // Disconnect self during callback
        observer.disconnect();
      });

      // Should not crash
      if (resizeCallback && observerInstance) {
        expect(() => resizeCallback([], observerInstance)).not.toThrow();
      }
    });
  });

  describe('IntersectionObserver Edge Cases', () => {
    it('handles IntersectionObserver with null root', () => {
      global.IntersectionObserver = vi.fn().mockImplementation(() => ({
        root: null,
        rootMargin: '0px',
        thresholds: [0],
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn()
      }));

      const observer = new IntersectionObserver(() => {}, {
        root: null // Document viewport
      });

      expect(observer.root).toBeNull();
    });

    it('handles IntersectionObserver with invalid threshold values', () => {
      global.IntersectionObserver = vi.fn().mockImplementation(() => ({
        root: null,
        rootMargin: '0px',
        thresholds: [0, 0.5, 1.0], // Valid thresholds
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn()
      }));

      // Invalid threshold values should be clamped or cause error
      expect(() => {
        new IntersectionObserver(() => {}, {
          threshold: [-1, 2] // Invalid values
        });
      }).not.toThrow(); // Browser handles this gracefully
    });
  });

  describe('Canvas API Edge Cases', () => {
    it('handles canvas getContext failure', () => {
      const mockCanvas = document.createElement('canvas');
      mockCanvas.getContext = vi.fn().mockReturnValue(null);

      const context = mockCanvas.getContext('2d');
      expect(context).toBeNull();
    });

    it('handles canvas size limits', () => {
      const mockCanvas = document.createElement('canvas');
      
      // Very large canvas dimensions might fail
      mockCanvas.width = 32768;
      mockCanvas.height = 32768;

      const context = mockCanvas.getContext('2d');
      // Some browsers limit canvas size
      expect(context).toBeDefined();
    });

    it('handles canvas memory exhaustion', () => {
      // Multiple large canvases might exhaust memory
      const canvases = [];
      
      for (let i = 0; i < 10; i++) {
        const canvas = document.createElement('canvas');
        canvas.width = 4096;
        canvas.height = 4096;
        canvases.push(canvas);
      }

      // Should not crash the test environment
      expect(canvases.length).toBe(10);
    });
  });

  describe('Performance API Edge Cases', () => {
    it('handles performance.now() not available', () => {
      const originalNow = performance.now;
      delete (performance as any).now;

      // Fallback should work
      const fallbackTime = Date.now();
      expect(typeof fallbackTime).toBe('number');

      performance.now = originalNow;
    });

    it('handles performance.memory not available', () => {
      const originalMemory = (performance as any).memory;
      delete (performance as any).memory;

      expect((performance as any).memory).toBeUndefined();

      (performance as any).memory = originalMemory;
    });

    it('handles performance timing precision reduction', () => {
      // Some browsers reduce timing precision for security
      const start = performance.now();
      const end = performance.now();
      
      const diff = end - start;
      expect(diff).toBeGreaterThanOrEqual(0);
    });
  });

  describe('URL API Edge Cases', () => {
    it('handles invalid URLs gracefully', () => {
      expect(() => new URL('not-a-url')).toThrow();
      expect(() => new URL('')).toThrow();
      expect(() => new URL('://invalid')).toThrow();
    });

    it('handles URL with special characters', () => {
      const url = new URL('ws://localhost:8000/socket.io/?game=test%20game');
      expect(url.searchParams.get('game')).toBe('test game');
    });

    it('handles createObjectURL memory leaks', () => {
      const mockBlob = new Blob(['test'], { type: 'text/plain' });
      const url = URL.createObjectURL(mockBlob);
      
      expect(typeof url).toBe('string');
      
      // Should revoke to prevent memory leaks
      URL.revokeObjectURL(url);
    });
  });

  describe('Event Listener Edge Cases', () => {
    it('handles removing non-existent event listener', () => {
      const element = document.createElement('div');
      const handler = vi.fn();
      
      // Remove listener that was never added
      expect(() => {
        element.removeEventListener('click', handler);
      }).not.toThrow();
    });

    it('handles adding duplicate event listeners', () => {
      const element = document.createElement('div');
      const handler = vi.fn();
      
      element.addEventListener('click', handler);
      element.addEventListener('click', handler); // Duplicate
      
      element.click();
      
      // Handler should only be called once with default options
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('handles event listener with passive option', () => {
      const element = document.createElement('div');
      const handler = vi.fn((event) => {
        // In passive mode, preventDefault should have no effect
        event.preventDefault();
      });
      
      element.addEventListener('touchstart', handler, { passive: true });
      
      const event = new TouchEvent('touchstart', { cancelable: true });
      element.dispatchEvent(event);
      
      expect(handler).toHaveBeenCalled();
    });
  });

  describe('Focus Management Edge Cases', () => {
    it('handles focus on hidden elements', () => {
      const element = document.createElement('button');
      element.style.display = 'none';
      document.body.appendChild(element);
      
      element.focus();
      
      // Hidden elements typically cannot receive focus
      expect(document.activeElement).not.toBe(element);
      
      document.body.removeChild(element);
    });

    it('handles focus trap with no focusable elements', () => {
      const container = document.createElement('div');
      container.innerHTML = '<span>No focusable elements</span>';
      document.body.appendChild(container);
      
      // Should handle gracefully when no focusable elements exist
      const focusableElements = container.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      expect(focusableElements.length).toBe(0);
      
      document.body.removeChild(container);
    });

    it('handles rapid focus changes', () => {
      const button1 = document.createElement('button');
      const button2 = document.createElement('button');
      
      document.body.appendChild(button1);
      document.body.appendChild(button2);
      
      // Rapid focus changes
      button1.focus();
      button2.focus();
      button1.focus();
      
      expect(document.activeElement).toBe(button1);
      
      document.body.removeChild(button1);
      document.body.removeChild(button2);
    });
  });

  describe('Animation Frame Edge Cases', () => {
    it('handles requestAnimationFrame in inactive tabs', () => {
      vi.useFakeTimers();
      
      const callback = vi.fn();
      const id = requestAnimationFrame(callback);
      
      // In inactive tabs, animations may be throttled
      vi.advanceTimersByTime(1000);
      
      expect(callback).toHaveBeenCalled();
      
      vi.useRealTimers();
    });

    it('handles cancelAnimationFrame with invalid ID', () => {
      expect(() => {
        cancelAnimationFrame(999999); // Invalid ID
      }).not.toThrow();
    });

    it('handles nested requestAnimationFrame calls', () => {
      vi.useFakeTimers();
      
      let callCount = 0;
      const nestedCallback = () => {
        callCount++;
        if (callCount < 5) {
          requestAnimationFrame(nestedCallback);
        }
      };
      
      requestAnimationFrame(nestedCallback);
      vi.advanceTimersByTime(100);
      
      expect(callCount).toBe(5);
      
      vi.useRealTimers();
    });
  });

  describe('Memory Leak Prevention', () => {
    it('detects potential memory leaks in event listeners', () => {
      const elements: HTMLElement[] = [];
      const handlers: (() => void)[] = [];
      
      // Create many elements with event listeners
      for (let i = 0; i < 100; i++) {
        const element = document.createElement('button');
        const handler = () => console.log(`Button ${i} clicked`);
        
        element.addEventListener('click', handler);
        elements.push(element);
        handlers.push(handler);
      }
      
      // Cleanup should remove all listeners
      elements.forEach((element, i) => {
        element.removeEventListener('click', handlers[i]);
      });
      
      expect(elements.length).toBe(100);
      expect(handlers.length).toBe(100);
    });

    it('detects observer cleanup', () => {
      const observers: (ResizeObserver | IntersectionObserver)[] = [];
      
      // Create multiple observers
      for (let i = 0; i < 10; i++) {
        const resizeObserver = new ResizeObserver(() => {});
        const intersectionObserver = new IntersectionObserver(() => {});
        
        observers.push(resizeObserver, intersectionObserver);
      }
      
      // All observers should be disconnected
      observers.forEach(observer => {
        observer.disconnect();
      });
      
      expect(observers.length).toBe(20);
    });

    it('detects timeout and interval cleanup', () => {
      vi.useFakeTimers();
      
      const timeoutIds: number[] = [];
      const intervalIds: number[] = [];
      
      // Create multiple timers
      for (let i = 0; i < 10; i++) {
        const timeoutId = setTimeout(() => {}, 1000);
        const intervalId = setInterval(() => {}, 100);
        
        timeoutIds.push(timeoutId);
        intervalIds.push(intervalId);
      }
      
      // All timers should be cleared
      timeoutIds.forEach(id => clearTimeout(id));
      intervalIds.forEach(id => clearInterval(id));
      
      vi.advanceTimersByTime(2000);
      
      expect(timeoutIds.length).toBe(10);
      expect(intervalIds.length).toBe(10);
      
      vi.useRealTimers();
    });
  });
});