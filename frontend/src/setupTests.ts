// Vitest setup for frontend React components
// Provides DOM matchers for asserting on DOM nodes with Vitest
// Learn more: https://github.com/testing-library/jest-dom
import { expect } from 'vitest';
import * as matchers from '@testing-library/jest-dom/matchers';

// Extend Vitest's expect with Testing Library matchers
expect.extend(matchers);
