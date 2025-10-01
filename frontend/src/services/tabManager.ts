/**
 * Multi-tab detection and management service
 * 
 * Detects when multiple tabs are open and coordinates between them
 * to prevent connection conflicts and provide a good user experience.
 */

import { useGameStore } from '../store/gameStore';

export interface TabInfo {
  id: string;
  timestamp: number;
  isActive: boolean;
  gameId?: string;
}

class TabManager {
  private tabId: string;
  private storageKey = 'mcts_tab_registry';
  private heartbeatInterval?: number;
  private cleanupInterval?: number;
  private isActive = true;
  private conflictDetected = false;

  constructor() {
    this.tabId = this.generateTabId();
    this.setupEventListeners();
    this.startHeartbeat();
    this.startCleanup();
    this.registerTab();
  }

  private generateTabId(): string {
    return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private setupEventListeners(): void {
    // Listen for storage changes (other tabs)
    window.addEventListener('storage', this.handleStorageChange.bind(this));
    
    // Listen for visibility changes
    document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    
    // Listen for beforeunload to cleanup
    window.addEventListener('beforeunload', this.cleanup.bind(this));

    // Listen for focus changes
    window.addEventListener('focus', this.handleFocus.bind(this));
    window.addEventListener('blur', this.handleBlur.bind(this));
  }

  private handleStorageChange(event: StorageEvent): void {
    if (event.key !== this.storageKey) return;
    
    // Another tab has updated the registry
    this.checkForConflicts();
  }

  private handleVisibilityChange(): void {
    this.isActive = !document.hidden;
    this.updateTabInfo();
    
    if (this.isActive) {
      this.checkForConflicts();
    }
  }

  private handleFocus(): void {
    this.isActive = true;
    this.updateTabInfo();
    this.checkForConflicts();
  }

  private handleBlur(): void {
    // Don't immediately mark as inactive to avoid flicker
    setTimeout(() => {
      if (document.hidden) {
        this.isActive = false;
        this.updateTabInfo();
      }
    }, 100);
  }

  private registerTab(): void {
    const registry = this.getTabRegistry();
    registry[this.tabId] = {
      id: this.tabId,
      timestamp: Date.now(),
      isActive: this.isActive,
    };
    this.setTabRegistry(registry);
  }

  private updateTabInfo(gameId?: string): void {
    const registry = this.getTabRegistry();
    if (registry[this.tabId]) {
      registry[this.tabId] = {
        ...registry[this.tabId],
        timestamp: Date.now(),
        isActive: this.isActive,
        gameId,
      };
      this.setTabRegistry(registry);
    }
  }

  private getTabRegistry(): Record<string, TabInfo> {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  }

  private setTabRegistry(registry: Record<string, TabInfo>): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(registry));
    } catch {
      // Storage might be full or unavailable
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.isActive) {
        this.updateTabInfo();
        this.checkForConflicts();
      }
    }, 5000); // Heartbeat every 5 seconds
  }

  private startCleanup(): void {
    this.cleanupInterval = window.setInterval(() => {
      this.cleanupStaleEntries();
    }, 30000); // Cleanup every 30 seconds
  }

  private cleanupStaleEntries(): void {
    const registry = this.getTabRegistry();
    const now = Date.now();
    const staleThreshold = 60000; // 1 minute
    
    let hasChanges = false;
    for (const [tabId, info] of Object.entries(registry)) {
      if (now - info.timestamp > staleThreshold) {
        delete registry[tabId];
        hasChanges = true;
      }
    }
    
    if (hasChanges) {
      this.setTabRegistry(registry);
    }
  }

  private checkForConflicts(): void {
    const registry = this.getTabRegistry();
    const activeTabs = Object.values(registry).filter(tab => 
      tab.isActive && tab.timestamp > Date.now() - 10000 // Active within last 10 seconds
    );
    
    const hasMultipleTabs = activeTabs.length > 1;
    const currentState = useGameStore.getState();
    
    if (hasMultipleTabs && !this.conflictDetected) {
      this.conflictDetected = true;
      this.handleMultiTabDetected(activeTabs);
    } else if (!hasMultipleTabs && this.conflictDetected) {
      this.conflictDetected = false;
      this.handleMultiTabResolved();
    }
  }

  private handleMultiTabDetected(activeTabs: TabInfo[]): void {
    console.warn('Multiple active tabs detected:', activeTabs.map(t => t.id));
    
    // Determine which tab should be the primary
    const sortedTabs = activeTabs.sort((a, b) => a.timestamp - b.timestamp);
    const isPrimary = sortedTabs[0].id === this.tabId;
    
    if (isPrimary) {
      // This is the primary tab - show a warning but continue working
      useGameStore.getState().dispatch({
        type: 'NOTIFICATION_ADDED',
        notification: {
          id: crypto.randomUUID(),
          type: 'warning',
          message: 'Multiple tabs detected. This tab will remain active.',
          timestamp: new Date()
        }
      });
    } else {
      // This is a secondary tab - show conflict message and disable interactions
      this.becomeSecondaryTab();
    }
  }

  private becomeSecondaryTab(): void {
    // Disconnect from the game but preserve the UI
    useGameStore.getState().dispatch({
      type: 'CONNECTION_LOST',
      error: 'Multiple tabs open - this tab is inactive'
    });

    // Add a prominent notification
    useGameStore.getState().dispatch({
      type: 'NOTIFICATION_ADDED',
      notification: {
        id: 'multi-tab-conflict',
        type: 'error',
        message: 'Multiple tabs detected. Close other tabs or refresh this page to continue playing.',
        timestamp: new Date()
      }
    });
  }

  private handleMultiTabResolved(): void {
    console.log('Multi-tab conflict resolved');
    
    // Remove the conflict notification
    useGameStore.getState().dispatch({
      type: 'NOTIFICATION_REMOVED',
      id: 'multi-tab-conflict'
    });

    // Try to reconnect if we were disconnected due to multi-tab
    const currentState = useGameStore.getState();
    if (currentState.connection.type === 'disconnected' && 
        currentState.connection.error?.includes('Multiple tabs')) {
      useGameStore.getState().dispatch({ type: 'CONNECTION_RETRY' });
    }
  }

  public notifyGameCreated(gameId: string): void {
    this.updateTabInfo(gameId);
  }

  public notifyGameEnded(): void {
    this.updateTabInfo();
  }

  public getActiveTabCount(): number {
    const registry = this.getTabRegistry();
    return Object.values(registry).filter(tab => 
      tab.isActive && tab.timestamp > Date.now() - 10000
    ).length;
  }

  public isPrimaryTab(): boolean {
    const registry = this.getTabRegistry();
    const activeTabs = Object.values(registry).filter(tab => 
      tab.isActive && tab.timestamp > Date.now() - 10000
    );
    
    if (activeTabs.length <= 1) return true;
    
    const sortedTabs = activeTabs.sort((a, b) => a.timestamp - b.timestamp);
    return sortedTabs[0].id === this.tabId;
  }

  public cleanup(): void {
    // Remove this tab from registry
    const registry = this.getTabRegistry();
    delete registry[this.tabId];
    this.setTabRegistry(registry);
    
    // Clear intervals
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
    
    // Remove event listeners
    window.removeEventListener('storage', this.handleStorageChange.bind(this));
    document.removeEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    window.removeEventListener('beforeunload', this.cleanup.bind(this));
    window.removeEventListener('focus', this.handleFocus.bind(this));
    window.removeEventListener('blur', this.handleBlur.bind(this));
  }
}

// Create a singleton instance
let tabManagerInstance: TabManager | null = null;

export const getTabManager = (): TabManager => {
  if (!tabManagerInstance) {
    tabManagerInstance = new TabManager();
  }
  return tabManagerInstance;
};

export const cleanupTabManager = (): void => {
  if (tabManagerInstance) {
    tabManagerInstance.cleanup();
    tabManagerInstance = null;
  }
};