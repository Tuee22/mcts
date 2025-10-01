/**
 * Functional tab coordination service
 * 
 * Uses pure functions and single source of truth for multi-tab management.
 * Eliminates mutable state in favor of deterministic coordination.
 */

export interface TabInfo {
  id: string;
  timestamp: number;
  isVisible: boolean;
  gameId?: string;
}

export interface TabRegistry {
  tabs: Record<string, TabInfo>;
  lastUpdate: number;
}

export interface TabCoordinationResult {
  isPrimary: boolean;
  shouldShowConflictWarning: boolean;
  conflictMessage?: string;
}

/**
 * Pure function to determine if this tab is the primary tab
 */
export function determinePrimaryTab(
  currentTabId: string, 
  registry: TabRegistry
): TabCoordinationResult {
  const activeTabs = Object.values(registry.tabs).filter(
    tab => isTabActive(tab, Date.now())
  );

  if (activeTabs.length <= 1) {
    return {
      isPrimary: true,
      shouldShowConflictWarning: false
    };
  }

  // Deterministic primary selection: oldest timestamp wins
  const sortedTabs = activeTabs.sort((a, b) => a.timestamp - b.timestamp);
  const primaryTab = sortedTabs[0];
  const isPrimary = primaryTab.id === currentTabId;

  return {
    isPrimary,
    shouldShowConflictWarning: !isPrimary,
    conflictMessage: isPrimary 
      ? `This tab is active. ${activeTabs.length - 1} other tabs are in background mode.`
      : 'Another tab is controlling the game. Close other tabs to regain control.'
  };
}

/**
 * Pure function to check if a tab is still active
 */
function isTabActive(tab: TabInfo, currentTime: number): boolean {
  const ACTIVE_THRESHOLD = 15000; // 15 seconds
  return (currentTime - tab.timestamp) < ACTIVE_THRESHOLD;
}

/**
 * Pure function to update tab registry
 */
export function updateTabInRegistry(
  registry: TabRegistry,
  tabId: string,
  update: Partial<TabInfo>
): TabRegistry {
  const currentTime = Date.now();
  
  return {
    tabs: {
      ...registry.tabs,
      [tabId]: {
        ...registry.tabs[tabId],
        id: tabId,
        timestamp: currentTime,
        isVisible: true,
        ...update
      }
    },
    lastUpdate: currentTime
  };
}

/**
 * Pure function to clean stale tabs from registry
 */
export function cleanStaleTabsFromRegistry(registry: TabRegistry): TabRegistry {
  const currentTime = Date.now();
  const cleanTabs: Record<string, TabInfo> = {};
  
  for (const [tabId, tab] of Object.entries(registry.tabs)) {
    if (isTabActive(tab, currentTime)) {
      cleanTabs[tabId] = tab;
    }
  }
  
  return {
    tabs: cleanTabs,
    lastUpdate: currentTime
  };
}

/**
 * Pure function to get tab registry from localStorage
 */
export function getTabRegistry(): TabRegistry {
  try {
    const stored = localStorage.getItem('mcts_tab_registry_v2');
    if (!stored) {
      return { tabs: {}, lastUpdate: Date.now() };
    }
    
    const parsed = JSON.parse(stored) as TabRegistry;
    // Always clean stale tabs when reading
    return cleanStaleTabsFromRegistry(parsed);
  } catch {
    return { tabs: {}, lastUpdate: Date.now() };
  }
}

/**
 * Pure function to save tab registry to localStorage
 */
export function saveTabRegistry(registry: TabRegistry): void {
  try {
    localStorage.setItem('mcts_tab_registry_v2', JSON.stringify(registry));
  } catch {
    // Storage error - fail gracefully
  }
}

/**
 * Functional tab coordinator class
 * Maintains no internal state - all state is derived from localStorage
 */
export class FunctionalTabCoordinator {
  private readonly tabId: string;
  private readonly onStatusChange: (result: TabCoordinationResult) => void;
  private heartbeatInterval?: number;

  constructor(onStatusChange: (result: TabCoordinationResult) => void) {
    this.tabId = generateTabId();
    this.onStatusChange = onStatusChange;
    
    this.registerTab();
    this.startHeartbeat();
    this.setupEventListeners();
  }

  private registerTab(): void {
    const registry = getTabRegistry();
    const updatedRegistry = updateTabInRegistry(registry, this.tabId, {
      isVisible: !document.hidden
    });
    saveTabRegistry(updatedRegistry);
    this.checkStatus();
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (!document.hidden) {
        const registry = getTabRegistry();
        const updatedRegistry = updateTabInRegistry(registry, this.tabId, {
          isVisible: true
        });
        saveTabRegistry(updatedRegistry);
        this.checkStatus();
      }
    }, 5000); // Heartbeat every 5 seconds
  }

  private setupEventListeners(): void {
    const handleVisibilityChange = () => {
      const registry = getTabRegistry();
      const updatedRegistry = updateTabInRegistry(registry, this.tabId, {
        isVisible: !document.hidden
      });
      saveTabRegistry(updatedRegistry);
      this.checkStatus();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleVisibilityChange);
    
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });

    // Listen for storage changes from other tabs
    window.addEventListener('storage', (event) => {
      if (event.key === 'mcts_tab_registry_v2') {
        this.checkStatus();
      }
    });
  }

  private checkStatus(): void {
    const registry = getTabRegistry();
    const result = determinePrimaryTab(this.tabId, registry);
    this.onStatusChange(result);
  }

  public notifyGameCreated(gameId: string): void {
    const registry = getTabRegistry();
    const updatedRegistry = updateTabInRegistry(registry, this.tabId, {
      gameId
    });
    saveTabRegistry(updatedRegistry);
    this.checkStatus();
  }

  public notifyGameEnded(): void {
    const registry = getTabRegistry();
    const updatedRegistry = updateTabInRegistry(registry, this.tabId, {
      gameId: undefined
    });
    saveTabRegistry(updatedRegistry);
    this.checkStatus();
  }

  public cleanup(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    // Remove this tab from registry
    const registry = getTabRegistry();
    const cleanedRegistry = {
      ...registry,
      tabs: Object.fromEntries(
        Object.entries(registry.tabs).filter(([tabId]) => tabId !== this.tabId)
      ),
      lastUpdate: Date.now()
    };
    saveTabRegistry(cleanedRegistry);
  }
}

/**
 * Generate a unique tab ID
 */
function generateTabId(): string {
  return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Singleton instance
let coordinatorInstance: FunctionalTabCoordinator | null = null;

export const initializeTabCoordinator = (
  onStatusChange: (result: TabCoordinationResult) => void
): FunctionalTabCoordinator => {
  if (coordinatorInstance) {
    coordinatorInstance.cleanup();
  }
  coordinatorInstance = new FunctionalTabCoordinator(onStatusChange);
  return coordinatorInstance;
};

export const getTabCoordinator = (): FunctionalTabCoordinator | null => {
  return coordinatorInstance;
};

export const cleanupTabCoordinator = (): void => {
  if (coordinatorInstance) {
    coordinatorInstance.cleanup();
    coordinatorInstance = null;
  }
};