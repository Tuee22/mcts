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
  const { showSettings, gameId, isConnected } = state;

  // Show settings panel when user explicitly opens it
  if (showSettings) return true;

  // Show settings panel by default when no game is active AND connected
  // This allows initial game setup but prevents toggle during rapid transitions when disconnected
  return !gameId && isConnected;
};

/**
 * Determines whether the settings toggle button should be displayed
 * @param state Current visibility state
 * @returns true if toggle button should be shown, false for settings panel
 */
export const shouldShowToggleButton = (state: SettingsVisibilityState): boolean => {
  return !shouldShowSettingsPanel(state);
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