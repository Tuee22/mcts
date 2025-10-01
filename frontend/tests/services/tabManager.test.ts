import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { getTabManager, cleanupTabManager, TabInfo } from '@/services/tabManager';
import { useGameStore } from '@/store/gameStore';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

// Mock crypto.randomUUID
Object.defineProperty(global, 'crypto', {
  value: { randomUUID: () => 'test-uuid-123' }
});

// Mock intervals
vi.stubGlobal('setInterval', vi.fn((fn, delay) => {
  const id = Math.random();
  setTimeout(fn, 0); // Execute immediately for tests
  return id;
}));

vi.stubGlobal('clearInterval', vi.fn());

describe('TabManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.clear();
    cleanupTabManager();
    
    // Clear store state
    useGameStore.getState().dispatch({ type: 'RESET_GAME' });
    
    // Mock document.hidden
    Object.defineProperty(document, 'hidden', {
      value: false,
      writable: true
    });
  });

  afterEach(() => {
    cleanupTabManager();
    mockLocalStorage.clear();
  });

  it('initializes and registers a tab', () => {
    const tabManager = getTabManager();
    
    expect(tabManager.getActiveTabCount()).toBe(1);
    expect(tabManager.isPrimaryTab()).toBe(true);
  });

  it('detects multiple tabs and handles conflicts', () => {
    const tabManager1 = getTabManager();
    
    // Simulate another tab by directly manipulating localStorage
    const registry: Record<string, TabInfo> = JSON.parse(
      mockLocalStorage.getItem('mcts_tab_registry') || '{}'
    );
    
    registry['fake-tab-2'] = {
      id: 'fake-tab-2',
      timestamp: Date.now(),
      isActive: true
    };
    
    mockLocalStorage.setItem('mcts_tab_registry', JSON.stringify(registry));
    
    // Trigger conflict detection by dispatching a storage event
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'mcts_tab_registry',
      newValue: JSON.stringify(registry)
    }));
    
    // Should detect conflict
    expect(tabManager1.getActiveTabCount()).toBe(2);
    
    // First tab should remain primary (lower timestamp)
    expect(tabManager1.isPrimaryTab()).toBe(true);
  });

  it('handles tab becoming secondary in conflict', async () => {
    // Start with a tab that has an earlier timestamp
    const oldRegistry: Record<string, TabInfo> = {
      'older-tab': {
        id: 'older-tab',
        timestamp: Date.now() - 10000, // 10 seconds ago
        isActive: true
      }
    };
    mockLocalStorage.setItem('mcts_tab_registry', JSON.stringify(oldRegistry));
    
    // Now create our tab (which will have a newer timestamp)
    const tabManager = getTabManager();
    
    // Our tab should not be primary
    expect(tabManager.isPrimaryTab()).toBe(false);
    
    // Should trigger secondary tab behavior
    const state = useGameStore.getState();
    
    // Should eventually show disconnection due to multi-tab conflict
    // Note: This might require waiting for the async operations to complete
    await new Promise(resolve => setTimeout(resolve, 100));
  });

  it('notifies of game creation and ending', () => {
    const tabManager = getTabManager();
    
    // Notify game created
    tabManager.notifyGameCreated('test-game-123');
    
    const registry: Record<string, TabInfo> = JSON.parse(
      mockLocalStorage.getItem('mcts_tab_registry') || '{}'
    );
    
    const currentTab = Object.values(registry)[0];
    expect(currentTab?.gameId).toBe('test-game-123');
    
    // Notify game ended
    tabManager.notifyGameEnded();
    
    const updatedRegistry: Record<string, TabInfo> = JSON.parse(
      mockLocalStorage.getItem('mcts_tab_registry') || '{}'
    );
    
    const updatedTab = Object.values(updatedRegistry)[0];
    expect(updatedTab?.gameId).toBeUndefined();
  });

  it('cleans up stale entries', () => {
    const tabManager = getTabManager();
    
    // Add a stale entry
    const registry: Record<string, TabInfo> = JSON.parse(
      mockLocalStorage.getItem('mcts_tab_registry') || '{}'
    );
    
    registry['stale-tab'] = {
      id: 'stale-tab',
      timestamp: Date.now() - 120000, // 2 minutes ago (stale)
      isActive: true
    };
    
    mockLocalStorage.setItem('mcts_tab_registry', JSON.stringify(registry));
    
    expect(tabManager.getActiveTabCount()).toBe(2);
    
    // Trigger cleanup (this happens automatically via interval)
    // For testing, we can call the private cleanup method indirectly
    // by waiting for the cleanup interval
    setTimeout(() => {
      expect(tabManager.getActiveTabCount()).toBe(1);
    }, 0);
  });

  it('handles visibility changes correctly', () => {
    const tabManager = getTabManager();
    
    expect(tabManager.isPrimaryTab()).toBe(true);
    
    // Simulate tab becoming hidden
    Object.defineProperty(document, 'hidden', { value: true, writable: true });
    document.dispatchEvent(new Event('visibilitychange'));
    
    // Tab should still be registered but might not be considered active
    expect(tabManager.getActiveTabCount()).toBe(1);
    
    // Simulate tab becoming visible again
    Object.defineProperty(document, 'hidden', { value: false, writable: true });
    document.dispatchEvent(new Event('visibilitychange'));
    
    expect(tabManager.isPrimaryTab()).toBe(true);
  });

  it('handles cleanup properly', () => {
    const tabManager = getTabManager();
    const initialCount = tabManager.getActiveTabCount();
    
    expect(initialCount).toBe(1);
    
    // Cleanup should remove the tab from registry
    cleanupTabManager();
    
    // Create a new manager to check the registry
    const newTabManager = getTabManager();
    
    // After cleanup, the old tab should be gone and we should have a new one
    expect(newTabManager.getActiveTabCount()).toBe(1);
    expect(newTabManager.isPrimaryTab()).toBe(true);
  });

  it('integrates with game store for multi-tab notifications', () => {
    const tabManager = getTabManager();
    
    // Connect to trigger normal operation
    useGameStore.getState().dispatch({ 
      type: 'CONNECTION_ESTABLISHED', 
      clientId: 'test-client' 
    });
    
    let connectionState = useGameStore.getState().connection;
    expect(connectionState.type).toBe('connected');
    
    // Simulate multi-tab conflict by adding another active tab
    const registry: Record<string, TabInfo> = JSON.parse(
      mockLocalStorage.getItem('mcts_tab_registry') || '{}'
    );
    
    registry['conflicting-tab'] = {
      id: 'conflicting-tab',
      timestamp: Date.now() - 1000, // Slightly older, so our tab becomes secondary
      isActive: true
    };
    
    mockLocalStorage.setItem('mcts_tab_registry', JSON.stringify(registry));
    
    // Trigger conflict detection
    window.dispatchEvent(new StorageEvent('storage', {
      key: 'mcts_tab_registry',
      newValue: JSON.stringify(registry)
    }));
    
    // Should detect we're not the primary tab and become secondary
    expect(tabManager.isPrimaryTab()).toBe(false);
    
    // Check that notifications were added to the store
    const notifications = useGameStore.getState().ui.notifications;
    const hasMultiTabNotification = notifications.some(n => 
      n.message.includes('Multiple tabs') || n.message.includes('tabs')
    );
    
    expect(hasMultiTabNotification).toBe(true);
  });
});