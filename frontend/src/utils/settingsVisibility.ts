/**
 * Settings Visibility Logic Utilities
 *
 * Extracted from GameSettings component to enable better testing
 * and separation of concerns.
 */

export interface SettingsVisibilityState {
  showSettings: boolean;
  gameId: string | null;
  isConnected: boolean;
}

/**
 * Determines whether the settings panel should be displayed
 * @param state Current visibility state
 * @returns true if settings panel should be shown, false for toggle button
 */
export const shouldShowSettingsPanel = (state: SettingsVisibilityState): boolean => {
  const { showSettings } = state;

  // Show settings panel ONLY when user explicitly opens it
  // E2E tests expect toggle button to always be shown initially
  return showSettings;
};

/**
 * Determines whether the settings toggle button should be displayed
 * @param state Current visibility state
 * @returns true if toggle button should be shown, false for settings panel
 */
export const shouldShowToggleButton = (state: SettingsVisibilityState): boolean => {
  const { showSettings } = state;
  // Show toggle button when panel is NOT explicitly shown
  // E2E tests expect toggle button to always be available initially
  return !showSettings;
};

/**
 * Gets the appropriate button title text based on connection state
 * @param isConnected Current connection status
 * @returns Title text for the toggle button
 */
export const getToggleButtonTitle = (isConnected: boolean): string => {
  return isConnected ? 'Game Settings' : 'Connect to server to access settings';
};

/**
 * Determines if settings controls should be disabled
 * @param isConnected Current connection status
 * @returns true if controls should be disabled
 */
export const areSettingsDisabled = (isConnected: boolean): boolean => {
  return !isConnected;
};