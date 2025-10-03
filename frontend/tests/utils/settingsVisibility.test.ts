/**
 * Unit tests for settingsVisibility utility functions.
 *
 * These tests verify the E2E-compatible behavior:
 * - Toggle button is always shown initially (E2E expectation)
 * - Settings panel is only shown when user explicitly opens it (showSettings=true)
 * - Connection state affects toggle button enabled/disabled state
 */

import { describe, it, expect } from 'vitest';
import {
  shouldShowSettingsPanel,
  shouldShowToggleButton,
  getToggleButtonTitle,
  areSettingsDisabled,
  type SettingsVisibilityState
} from '../../src/utils/settingsVisibility';

describe('settingsVisibility utilities', () => {
  describe('shouldShowToggleButton', () => {
    it('should return true when showSettings is false (default state)', () => {
      const state: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowToggleButton(state)).toBe(true);
    });

    it('should return true when showSettings is false and game exists', () => {
      const state: SettingsVisibilityState = {
        showSettings: false,
        gameId: 'test-game-123',
        isConnected: true
      };

      expect(shouldShowToggleButton(state)).toBe(true);
    });

    it('should return true when disconnected and no game exists', () => {
      const state: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: false
      };

      expect(shouldShowToggleButton(state)).toBe(true);
    });

    it('should return false only when showSettings is explicitly true', () => {
      const state: SettingsVisibilityState = {
        showSettings: true,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowToggleButton(state)).toBe(false);
    });

    it('should return false when showSettings is true regardless of other state', () => {
      const state: SettingsVisibilityState = {
        showSettings: true,
        gameId: 'test-game-123',
        isConnected: false
      };

      expect(shouldShowToggleButton(state)).toBe(false);
    });
  });

  describe('shouldShowSettingsPanel', () => {
    it('should return false when showSettings is false (only explicit show)', () => {
      const state: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowSettingsPanel(state)).toBe(false);
    });

    it('should return false when showSettings is false, even when disconnected', () => {
      const state: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: false
      };

      expect(shouldShowSettingsPanel(state)).toBe(false);
    });

    it('should return true only when showSettings is explicitly true', () => {
      const state: SettingsVisibilityState = {
        showSettings: true,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowSettingsPanel(state)).toBe(true);
    });

    it('should return true when showSettings is true regardless of other state', () => {
      const state: SettingsVisibilityState = {
        showSettings: true,
        gameId: 'test-game-123',
        isConnected: false
      };

      expect(shouldShowSettingsPanel(state)).toBe(true);
    });
  });

  describe('mutual exclusivity', () => {
    it('should ensure toggle button and panel are mutually exclusive', () => {
      const states: SettingsVisibilityState[] = [
        { showSettings: false, gameId: null, isConnected: true },      // Panel (auto-show)
        { showSettings: false, gameId: 'test-game', isConnected: true }, // Toggle (game exists)
        { showSettings: false, gameId: null, isConnected: false },      // Toggle (disconnected)
        { showSettings: true, gameId: null, isConnected: true },        // Panel (explicit)
        { showSettings: true, gameId: 'test-game', isConnected: false } // Panel (explicit)
      ];

      states.forEach((state, index) => {
        const showToggle = shouldShowToggleButton(state);
        const showPanel = shouldShowSettingsPanel(state);

        // They must be mutually exclusive
        expect(showToggle).not.toBe(showPanel);
        // One of them must always be shown
        expect(showToggle || showPanel).toBe(true);
      });
    });
  });

  describe('getToggleButtonTitle', () => {
    it('should return appropriate title when connected', () => {
      expect(getToggleButtonTitle(true)).toBe('⚙️ Game Settings');
    });

    it('should return appropriate title when disconnected', () => {
      expect(getToggleButtonTitle(false)).toBe('Connect to server to access settings');
    });
  });

  describe('areSettingsDisabled', () => {
    it('should return false when connected', () => {
      expect(areSettingsDisabled(true)).toBe(false);
    });

    it('should return true when disconnected', () => {
      expect(areSettingsDisabled(false)).toBe(true);
    });
  });

  describe('E2E compatibility scenarios', () => {
    it('should show toggle button on fresh page load (E2E expectation)', () => {
      const freshPageState: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowToggleButton(freshPageState)).toBe(true);
      expect(shouldShowSettingsPanel(freshPageState)).toBe(false);
    });

    it('should show toggle button after browser navigation back to app', () => {
      const backNavigationState: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowToggleButton(backNavigationState)).toBe(true);
      expect(shouldShowSettingsPanel(backNavigationState)).toBe(false);
    });

    it('should show toggle button in multiple tabs scenario', () => {
      const multiTabState: SettingsVisibilityState = {
        showSettings: false,
        gameId: null,
        isConnected: true
      };

      expect(shouldShowToggleButton(multiTabState)).toBe(true);
      expect(shouldShowSettingsPanel(multiTabState)).toBe(false);
    });
  });
});